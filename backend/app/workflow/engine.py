"""Workflow engine — submission → evaluation → board → decision → communication.

System-driven progression with checkpoints (requirement 6). Checkpoints are
risk-tier aware: low-risk cases advance automatically, medium/high-risk
stages require a recorded human sign-off before advancing.

In-memory store for the scaffold; replace with a SQLAlchemy-backed table for
production.
"""
import uuid
from datetime import datetime, timezone

from app.core.audit import audit_log, new_trace_id
from app.models.schemas import RiskTier, WorkflowStage

STAGE_ORDER = [
    WorkflowStage.SUBMISSION,
    WorkflowStage.EVALUATION,
    WorkflowStage.BOARD,
    WorkflowStage.DECISION,
    WorkflowStage.COMMUNICATION,
    WorkflowStage.CLOSED,
]

# Stages that need an explicit human sign-off for non-low-risk cases.
HUMAN_CHECKPOINTS = {WorkflowStage.EVALUATION, WorkflowStage.BOARD, WorkflowStage.DECISION}

_cases: dict[str, dict] = {}


def create_case(title: str, risk_tier: RiskTier = RiskTier.MEDIUM) -> dict:
    case_id = f"case_{uuid.uuid4().hex[:10]}"
    case = {
        "case_id": case_id,
        "title": title,
        "stage": WorkflowStage.SUBMISSION,
        "risk_tier": risk_tier,
        "history": [_event(WorkflowStage.SUBMISSION, "case created", actor="system")],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _cases[case_id] = case
    audit_log("workflow.case_created", new_trace_id(), {"case_id": case_id, "title": title})
    return case


def get_case(case_id: str) -> dict | None:
    return _cases.get(case_id)


def list_cases() -> list[dict]:
    return list(_cases.values())


def advance(case_id: str, actor: str = "system", signoff_by: str | None = None) -> dict:
    case = _cases[case_id]
    current = case["stage"]
    if current == WorkflowStage.CLOSED:
        return case

    needs_signoff = (
        current in HUMAN_CHECKPOINTS and case["risk_tier"] != RiskTier.LOW
    )
    if needs_signoff and not signoff_by:
        raise PermissionError(
            f"Stage '{current.value}' requires human sign-off for "
            f"{case['risk_tier'].value}-risk cases."
        )

    nxt = STAGE_ORDER[STAGE_ORDER.index(current) + 1]
    case["stage"] = nxt
    case["history"].append(
        _event(nxt, f"advanced from {current.value}", actor=signoff_by or actor)
    )
    audit_log(
        "workflow.advanced",
        new_trace_id(),
        {"case_id": case_id, "from": current.value, "to": nxt.value,
         "actor": signoff_by or actor, "risk_tier": case["risk_tier"].value},
    )
    return case


def set_risk_tier(case_id: str, tier: RiskTier) -> dict:
    case = _cases[case_id]
    case["risk_tier"] = tier
    case["history"].append(_event(case["stage"], f"risk tier set to {tier.value}", actor="rule_engine"))
    return case


def _event(stage: WorkflowStage, note: str, actor: str) -> dict:
    return {
        "stage": stage.value,
        "note": note,
        "actor": actor,
        "at": datetime.now(timezone.utc).isoformat(),
    }
