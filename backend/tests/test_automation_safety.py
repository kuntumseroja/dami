"""Automation safety — fault → escalation + incident (Sprint 4.6, FR-8)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import Case, RiskTier
from app.use_cases.automation_safety import (
    escalate_to_human,
    list_incidents,
    run_guarded,
)


def _deps():
    return InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")


@pytest.mark.asyncio
async def test_escalation_records_incident_and_flips_off_automation():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="t", risk_tier=RiskTier.LOW))
    inc = await escalate_to_human("c1", "manual test", repository=repo, audit=audit,
                                  detail="boom")
    assert inc["escalated"] is True
    case = await repo.get("c1")
    assert case.risk_tier == RiskTier.MEDIUM            # off the automated path
    incidents = await list_incidents("c1", repository=repo)
    assert len(incidents) == 1 and incidents[0]["reason"] == "manual test"


@pytest.mark.asyncio
async def test_run_guarded_escalates_on_fault_and_reraises():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="t", risk_tier=RiskTier.LOW))

    async def boom():
        raise ValueError("injected fault")

    with pytest.raises(ValueError):
        await run_guarded("c1", "extraction", boom, repository=repo, audit=audit)
    incidents = await list_incidents("c1", repository=repo)
    assert incidents and "extraction" in incidents[0]["reason"]
    assert "injected fault" in incidents[0]["detail"]


@pytest.mark.asyncio
async def test_run_guarded_passes_through_on_success():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="t", risk_tier=RiskTier.LOW))

    async def ok():
        return 42

    assert await run_guarded("c1", "step", ok, repository=repo, audit=audit) == 42
    assert await list_incidents("c1", repository=repo) == []
    assert (await repo.get("c1")).risk_tier == RiskTier.LOW   # stays automated
