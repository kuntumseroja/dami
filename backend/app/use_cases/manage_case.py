"""Case lifecycle use cases — create, advance (with checkpoint enforcement),
risk-tier changes. The checkpoint business rule lives in the Case entity;
this layer persists, audits, and binds the acting identity."""
import uuid

from app.domain.models import (
    STAGE_ORDER,
    BoardGateBlocked,
    Case,
    CaseEvent,
    RiskTier,
    Role,
    User,
    WorkflowStage,
    new_trace_id,
)
from app.domain.ports import AuditLog, CaseRepository
from app.use_cases.board_gate import unresolved_critical


class Forbidden(Exception):
    """Acting user lacks the role required for this transition."""


async def create_case(title: str, user: User, *,
                      repository: CaseRepository, audit: AuditLog) -> Case:
    case = Case(
        case_id=f"case_{uuid.uuid4().hex[:10]}",
        title=title,
        entity=user.entity,   # case is owned by the acting user's BPI entity
        history=[CaseEvent(stage="submission", note="case created", actor=user.id)],
    )
    await repository.save(case)
    audit.log("workflow.case_created", new_trace_id(),
              {"case_id": case.case_id, "title": title, "actor": user.id,
               "entity": case.entity.value})
    return case


async def advance_case(case_id: str, user: User, *,
                       repository: CaseRepository, audit: AuditLog,
                       override_by: str | None = None) -> Case:
    case = await repository.get(case_id)
    if case is None or not user.can_access_entity(case.entity):
        raise KeyError(case_id)  # cross-tenant looks like not-found

    # Sign-off identity comes from the authenticated user, never from input.
    signoff_by: str | None = None
    if case.requires_signoff:
        if not user.has_role(Role.APPROVER):
            raise Forbidden(
                f"Stage '{case.stage.value}' requires the approver role for "
                f"{case.risk_tier.value}-risk cases."
            )
        signoff_by = user.id

    # Board-stage Critical gate (3.7): block entry to board_preparation while
    # unresolved Critical consistency items exist; bypass = dual-approval override.
    idx = STAGE_ORDER.index(case.stage)
    next_stage = STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None
    if next_stage == WorkflowStage.BOARD_PREPARATION:
        blocking = await unresolved_critical(case_id, repository=repository)
        if blocking:
            valid_override = bool(override_by) and override_by != user.id
            if not valid_override:
                raise BoardGateBlocked(blocking)
            audit.log(
                "incident.board_gate_override",
                new_trace_id(),
                {"case_id": case_id, "severity": "compliance",
                 "approver_1": user.id, "approver_2": override_by,
                 "overridden_items": blocking},
            )

    previous, current = case.advance(actor=user.id, signoff_by=signoff_by)
    await repository.save(case)
    audit.log(
        "workflow.advanced",
        new_trace_id(),
        {"case_id": case_id, "from": previous, "to": current,
         "actor": signoff_by or user.id, "risk_tier": case.risk_tier.value},
    )
    return case


async def set_risk_tier(case_id: str, tier: RiskTier, actor: str, *,
                        repository: CaseRepository, audit: AuditLog) -> Case:
    case = await repository.get(case_id)
    if case is None:
        raise KeyError(case_id)
    case.set_risk_tier(tier, actor=actor)
    await repository.save(case)
    audit.log("workflow.risk_tier_set", new_trace_id(),
              {"case_id": case_id, "tier": tier.value, "actor": actor})
    return case
