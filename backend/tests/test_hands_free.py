"""Hands-free low-risk auto-advance (Sprint 4.8, FR-8)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import Case, RiskTier, WorkflowStage
from app.use_cases.hands_free import auto_advance
from app.use_cases.workflow_ops import set_workstream


def _deps():
    return InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")


@pytest.mark.asyncio
async def test_low_risk_auto_advances_to_dispatch_zero_touch():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="Low-risk lease", risk_tier=RiskTier.LOW))
    # merge gate: workstreams complete (the hands-free flow does this)
    for s in ("drafting", "routing_verification"):
        await set_workstream("c1", s, "complete", repository=repo, audit=audit)

    final = await auto_advance("c1", target=WorkflowStage.COMMUNICATION_DISPATCH,
                               repository=repo, audit=audit)
    assert final == "communication_dispatch"
    # zero human sign-offs: every advance actor is the automation system
    case = await repo.get("c1")
    advances = [e for e in case.history if e.note.startswith("advanced")]
    assert advances and all(e.actor == "system-automation" for e in advances)


@pytest.mark.asyncio
async def test_auto_advance_stops_at_target_not_closed():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="t", risk_tier=RiskTier.LOW))
    for s in ("drafting", "routing_verification"):
        await set_workstream("c1", s, "complete", repository=repo, audit=audit)
    final = await auto_advance("c1", target=WorkflowStage.COMMUNICATION_DISPATCH,
                               repository=repo, audit=audit)
    assert final == "communication_dispatch"     # not closed — stops at target


@pytest.mark.asyncio
async def test_auto_advance_idempotent_at_target():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="t", risk_tier=RiskTier.LOW,
                         stage=WorkflowStage.COMMUNICATION_DISPATCH))
    final = await auto_advance("c1", target=WorkflowStage.COMMUNICATION_DISPATCH,
                               repository=repo, audit=audit)
    assert final == "communication_dispatch"
