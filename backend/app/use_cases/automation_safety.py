"""Automation safety net (Sprint 4.6, FR-8).

Any error, exception, or override in an automated flow auto-escalates to a human
reviewer and logs a Sev incident. Escalation flips the case off the automated
path (risk tier → medium, so the next transition needs human sign-off) and
records an `automation_incident` artefact + audit entry. `run_guarded` wraps an
automated step so a fault never silently passes.
"""
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.domain.models import RiskTier, new_trace_id
from app.domain.ports import AuditLog, CaseRepository

T = TypeVar("T")


async def escalate_to_human(
    case_id: str, reason: str, *, repository: CaseRepository, audit: AuditLog,
    detail: str = "", severity: str = "sev2",
) -> dict:
    """Record an automation incident + move the case to human-in-the-loop."""
    trace_id = new_trace_id()
    incident = {"case_id": case_id, "reason": reason, "detail": detail,
                "severity": severity, "trace_id": trace_id, "escalated": True}
    await repository.save_artefact(case_id, "automation_incident", incident)

    case = await repository.get(case_id)
    if case is not None and case.risk_tier == RiskTier.LOW:
        case.set_risk_tier(RiskTier.MEDIUM, actor="automation_safety")
        await repository.save(case)

    audit.log("incident.automation_fault", trace_id,
              {"case_id": case_id, "reason": reason, "detail": detail,
               "severity": severity})
    return incident


async def run_guarded(
    case_id: str, label: str, fn: Callable[[], Awaitable[T]], *,
    repository: CaseRepository, audit: AuditLog,
) -> T:
    """Run an automated step; on ANY exception, escalate + re-raise."""
    try:
        return await fn()
    except Exception as exc:                       # noqa: BLE001 — safety net by design
        await escalate_to_human(case_id, f"automated step '{label}' failed",
                                repository=repository, audit=audit,
                                detail=f"{type(exc).__name__}: {exc}")
        raise


async def list_incidents(case_id: str, *, repository: CaseRepository) -> list[dict]:
    rows = await repository.list_artefacts(case_id, "automation_incident")
    return [r.get("payload", r) for r in rows]
