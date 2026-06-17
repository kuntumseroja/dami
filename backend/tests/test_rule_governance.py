"""Rule governance — dual-approval + version logging (Sprint 4.4, FR-4/FR-8)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import RoutingRequest
from app.domain.rules import evaluate
from app.use_cases.rule_governance import (
    SelfApprovalForbidden,
    decide_rule_change,
    list_rule_changes,
    propose_rule_change,
)


def _deps():
    return InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")


def test_decision_records_rulebook_version():
    out = evaluate(RoutingRequest(case_id="t", request_type="asset_disposal",
                                  amount_idr=1_000_000_000))
    assert out["rulebook_version"] == 1


@pytest.mark.asyncio
async def test_proposer_cannot_self_approve():
    repo, audit = _deps()
    ch = await propose_rule_change("Lower lease ceiling", "to Rp400m",
                                   proposed_by="owner1", repository=repo, audit=audit)
    with pytest.raises(SelfApprovalForbidden):
        await decide_rule_change(ch["id"], approver="owner1", decision="approved",
                                 repository=repo, audit=audit)


@pytest.mark.asyncio
async def test_second_approver_can_approve():
    repo, audit = _deps()
    ch = await propose_rule_change("New SOP for JV", "approve SOP-DAM-010",
                                   proposed_by="owner1", repository=repo, audit=audit)
    await decide_rule_change(ch["id"], approver="owner2", decision="approved",
                             repository=repo, audit=audit)
    changes = {c["id"]: c for c in await list_rule_changes(repo)}
    assert changes[ch["id"]]["status"] == "approved"
    assert changes[ch["id"]]["approved_by"] == "owner2"


@pytest.mark.asyncio
async def test_unknown_change_raises():
    repo, audit = _deps()
    with pytest.raises(KeyError):
        await decide_rule_change("rc_nope", approver="x", decision="approved",
                                 repository=repo, audit=audit)


@pytest.mark.asyncio
async def test_pending_until_approved():
    repo, audit = _deps()
    ch = await propose_rule_change("X", "y", proposed_by="o1", repository=repo, audit=audit)
    [only] = await list_rule_changes(repo)
    assert only["id"] == ch["id"] and only["status"] == "pending"
