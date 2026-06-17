"""Workflow completion — owners, notifications, merge gate, SLA alerts (4.7, FR-6)."""
from datetime import timedelta

import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import (
    Case,
    CaseEvent,
    MergeGateBlocked,
    RiskTier,
    Role,
    User,
    WorkflowStage,
    utcnow,
)
from app.use_cases.manage_case import advance_case
from app.use_cases.workflow_ops import (
    assign_stage_owner,
    get_assignments,
    list_notifications,
    merge_gate_pending,
    set_workstream,
    sla_scan,
)


def _deps():
    return InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")


@pytest.mark.asyncio
async def test_assignment_notifies_owner_with_context():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="PTPN divestasi"))
    await assign_stage_owner("c1", "internal_review", "reviewer-A",
                             deadline_days=3, repository=repo, audit=audit)
    assert (await get_assignments("c1", repository=repo))["internal_review"]["owner"] == "reviewer-A"
    notes = await list_notifications("reviewer-A", repository=repo)
    assert len(notes) == 1
    assert notes[0]["kind"] == "assignment" and notes[0]["deadline"]
    assert "PTPN divestasi" in notes[0]["title"]


@pytest.mark.asyncio
async def test_merge_gate_blocks_until_both_streams_complete():
    repo, audit = _deps()
    await repo.save(Case(case_id="c1", title="t", stage=WorkflowStage.INTERNAL_REVIEW,
                         risk_tier=RiskTier.LOW))
    assert set(await merge_gate_pending("c1", repository=repo)) == {"drafting", "routing_verification"}
    with pytest.raises(MergeGateBlocked):
        await advance_case("c1", User(id="u", name="u", roles=[Role.REVIEWER]),
                           repository=repo, audit=audit)

    await set_workstream("c1", "drafting", "complete", repository=repo, audit=audit)
    assert await merge_gate_pending("c1", repository=repo) == ["routing_verification"]
    await set_workstream("c1", "routing_verification", "complete", repository=repo, audit=audit)
    assert await merge_gate_pending("c1", repository=repo) == []
    case = await advance_case("c1", User(id="u", name="u", roles=[Role.REVIEWER]),
                              repository=repo, audit=audit)
    assert case.stage == WorkflowStage.BOARD_PREPARATION


@pytest.mark.asyncio
async def test_sla_scan_alerts_supervisor_for_stalled_case():
    repo, audit = _deps()
    old = utcnow() - timedelta(days=10)
    case = Case(case_id="c1", title="Stuck", stage=WorkflowStage.NOTA_DRAFTING,
                history=[CaseEvent(stage="nota_drafting", note="advanced", actor="x", at=old)])
    await repo.save(case)
    overdue = await sla_scan(repository=repo, audit=audit, supervisor="boss")
    assert overdue and overdue[0]["case_id"] == "c1"
    assert overdue[0]["days_in_stage"] >= 10
    notes = await list_notifications("boss", repository=repo)
    assert notes and notes[0]["kind"] == "sla_breach"


@pytest.mark.asyncio
async def test_sla_scan_ignores_within_sla():
    repo, audit = _deps()
    case = Case(case_id="c1", title="Fresh", stage=WorkflowStage.NOTA_DRAFTING,
                history=[CaseEvent(stage="nota_drafting", note="advanced", actor="x")])
    await repo.save(case)
    assert await sla_scan(repository=repo, audit=audit) == []
