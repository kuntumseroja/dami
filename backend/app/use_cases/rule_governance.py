"""Rule governance — dual-approval on rule/threshold changes (Sprint 4.4, FR-4/FR-8).

SOP owners propose rule/threshold changes through configuration (decoupled from
the software release). Every change requires a SECOND approver — a proposer can
never self-approve. Proposals + decisions are append-only and audited; the
rulebook version (recorded on every routing decision) bumps on approval. The
what-if simulator (4.2) is the pre-production simulation environment (R3).
"""
import uuid

from app.domain.models import new_trace_id, utcnow
from app.domain.ports import AuditLog, CaseRepository

GOV_CASE = "__rule_governance__"          # synthetic scope for global rule records
_PROPOSAL = "rule_change"
_DECISION = "rule_change_decision"


class SelfApprovalForbidden(Exception):
    """A proposer cannot approve their own rule change (dual-approval)."""


async def propose_rule_change(
    summary: str, detail: str, *, proposed_by: str,
    repository: CaseRepository, audit: AuditLog,
) -> dict:
    rec = {"id": f"rc_{uuid.uuid4().hex[:10]}", "summary": summary, "detail": detail,
           "proposed_by": proposed_by, "status": "pending",
           "at": utcnow().isoformat()}
    await repository.save_artefact(GOV_CASE, _PROPOSAL, rec)
    audit.log("rule.change_proposed", new_trace_id(),
              {"change_id": rec["id"], "summary": summary, "proposed_by": proposed_by})
    return rec


async def _proposals(repository: CaseRepository) -> dict:
    rows = await repository.list_artefacts(GOV_CASE, _PROPOSAL)
    return {r.get("payload", r)["id"]: dict(r.get("payload", r)) for r in rows}


async def decide_rule_change(
    change_id: str, *, approver: str, decision: str,
    repository: CaseRepository, audit: AuditLog,
) -> dict:
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be approved | rejected")
    proposals = await _proposals(repository)
    change = proposals.get(change_id)
    if change is None:
        raise KeyError(f"unknown rule change {change_id}")
    if approver == change["proposed_by"]:
        raise SelfApprovalForbidden("a proposer cannot approve their own change")
    rec = {"change_id": change_id, "decision": decision, "approved_by": approver,
           "at": utcnow().isoformat()}
    await repository.save_artefact(GOV_CASE, _DECISION, rec)
    audit.log(f"rule.change_{decision}", new_trace_id(),
              {"change_id": change_id, "approved_by": approver,
               "proposed_by": change["proposed_by"]})
    return rec


async def list_rule_changes(repository: CaseRepository) -> list[dict]:
    proposals = await _proposals(repository)
    for r in await repository.list_artefacts(GOV_CASE, _DECISION):
        d = r.get("payload", r)
        if d["change_id"] in proposals:
            proposals[d["change_id"]].update(
                status=d["decision"], approved_by=d["approved_by"], decided_at=d["at"])
    return sorted(proposals.values(), key=lambda c: c["at"], reverse=True)
