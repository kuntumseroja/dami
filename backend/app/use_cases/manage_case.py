"""Case lifecycle use cases — create, advance (with checkpoint enforcement),
risk-tier changes. The checkpoint business rule lives in the Case entity;
this layer persists, audits, and binds the acting identity."""
import uuid

from app.domain.models import new_trace_id
from app.domain.models import Case, CaseEvent, RiskTier, Role, User
from app.domain.ports import AuditLog, CaseRepository


class Forbidden(Exception):
    """Acting user lacks the role required for this transition."""


async def create_case(title: str, user: User, *,
                      repository: CaseRepository, audit: AuditLog) -> Case:
    case = Case(
        case_id=f"case_{uuid.uuid4().hex[:10]}",
        title=title,
        history=[CaseEvent(stage="submission", note="case created", actor=user.id)],
    )
    await repository.save(case)
    audit.log("workflow.case_created", new_trace_id(),
              {"case_id": case.case_id, "title": title, "actor": user.id})
    return case


async def advance_case(case_id: str, user: User, *,
                       repository: CaseRepository, audit: AuditLog) -> Case:
    case = await repository.get(case_id)
    if case is None:
        raise KeyError(case_id)

    # Sign-off identity comes from the authenticated user, never from input.
    signoff_by: str | None = None
    if case.requires_signoff:
        if not user.has_role(Role.APPROVER):
            raise Forbidden(
                f"Stage '{case.stage.value}' requires the approver role for "
                f"{case.risk_tier.value}-risk cases."
            )
        signoff_by = user.id

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
