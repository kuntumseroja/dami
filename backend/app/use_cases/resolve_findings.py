"""Consistency-finding resolution workflow (Sprint 3.5, FR-2 AC-2.6).

Each flagged item can be Resolved / Accepted-as-is-with-justification /
Deferred, plus a one-click "Incorrect flag" feedback action — all logged with
identity + justification. Resolutions are append-only artefacts (latest wins),
and the audit trail feeds a false-positive aggregation for weekly review.
"""
from app.domain.models import FindingResolution, new_trace_id
from app.domain.ports import AuditLog, CaseRepository

_KIND = "finding_resolution"
JUSTIFICATION_REQUIRED = {"accepted_as_is", "incorrect_flag"}


class ResolutionInvalid(ValueError):
    """Raised when a resolution is missing a required justification."""


async def record_resolution(
    res: FindingResolution, *, repository: CaseRepository, audit: AuditLog,
) -> FindingResolution:
    if res.status in JUSTIFICATION_REQUIRED and not res.justification.strip():
        raise ResolutionInvalid(f"'{res.status}' requires a justification")
    trace_id = new_trace_id()
    await repository.save_artefact(res.case_id, _KIND, res.model_dump(mode="json"))
    audit.log(
        "finding.resolution",
        trace_id,
        {
            "case_id": res.case_id,
            "finding_id": res.finding_id,
            "kind": res.kind,
            "status": res.status,
            "justification": res.justification,
            "actor": res.actor,
        },
    )
    return res


async def get_resolution_state(case_id: str, *, repository: CaseRepository) -> dict:
    """Latest resolution per finding id (artefacts are append-only, in order)."""
    artefacts = await repository.list_artefacts(case_id, _KIND)
    latest: dict[str, dict] = {}
    for a in artefacts:
        payload = a.get("payload", a)
        latest[payload["finding_id"]] = payload
    return latest


def summarize_false_positives(records: list[dict]) -> dict:
    """Aggregate 'incorrect_flag' resolutions from the audit trail (weekly FP)."""
    by_kind: dict[str, int] = {}
    total = 0
    resolutions = 0
    for r in records:
        if r.get("event") != "finding.resolution":
            continue
        resolutions += 1
        if r.get("status") == "incorrect_flag":
            total += 1
            by_kind[r.get("kind") or "unknown"] = by_kind.get(r.get("kind") or "unknown", 0) + 1
    rate = round(total / resolutions, 4) if resolutions else 0.0
    return {"false_positives": total, "resolutions": resolutions,
            "false_positive_rate": rate, "by_kind": by_kind}
