"""Board-stage Critical gate (Sprint 3.7, FR-2 AC-2.5).

A case cannot advance into Board Preparation while any Critical consistency
finding is unresolved. A finding is cleared by an explicit resolution
(resolved / accepted-as-is / incorrect-flag); deferred or un-actioned Critical
items still block. Bypass is a dual-approval override, logged as a compliance
incident.
"""
from app.domain.ports import CaseRepository
from app.use_cases.resolve_findings import get_resolution_state

# Resolution statuses that clear a finding from the gate. 'deferred' does NOT.
CLEARED_STATUSES = {"resolved", "accepted_as_is", "incorrect_flag"}


async def unresolved_critical(case_id: str, *, repository: CaseRepository) -> list[dict]:
    """Critical findings (latest report) without a clearing resolution."""
    reports = await repository.list_artefacts(case_id, "consistency_report")
    if not reports:
        return []
    findings = reports[-1].get("payload", reports[-1]).get("findings", [])
    state = await get_resolution_state(case_id, repository=repository)
    blocking = []
    for f in findings:
        if f.get("severity") != "critical":
            continue
        res = state.get(f.get("id", ""))
        if res is None or res.get("status") not in CLEARED_STATUSES:
            blocking.append({"id": f.get("id", ""), "kind": f.get("kind"),
                             "description": f.get("description", "")})
    return blocking
