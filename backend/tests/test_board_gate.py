"""Board-stage Critical gate (Sprint 3.7, FR-2 AC-2.5)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import (
    BoardGateBlocked,
    Case,
    FindingResolution,
    RiskTier,
    Role,
    User,
    WorkflowStage,
)
from app.use_cases.board_gate import unresolved_critical
from app.use_cases.manage_case import advance_case
from app.use_cases.resolve_findings import record_resolution

REVIEWER = User(id="rev", name="rev", roles=[Role.REVIEWER])
APPROVER2 = "app2"


async def _case_at_internal_review(repo, *, critical=True):
    # low risk → internal_review exit needs no approver, isolating the gate
    case = Case(case_id="c1", title="t", stage=WorkflowStage.INTERNAL_REVIEW,
                risk_tier=RiskTier.LOW)
    await repo.save(case)
    findings = [{"id": "fnd_x", "severity": "critical" if critical else "warning",
                 "kind": "numeric_mismatch", "description": "Rp415 vs Rp420"}]
    await repo.save_artefact("c1", "consistency_report", {"findings": findings})
    # complete the parallel workstreams so the 4.7 merge gate passes — this
    # isolates the Critical gate under test
    for stream in ("drafting", "routing_verification"):
        await repo.save_artefact("c1", "workstream",
                                 {"case_id": "c1", "stream": stream, "status": "complete"})
    return case


@pytest.mark.asyncio
async def test_unresolved_critical_blocks_advance():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _case_at_internal_review(repo)
    assert len(await unresolved_critical("c1", repository=repo)) == 1
    with pytest.raises(BoardGateBlocked) as exc:
        await advance_case("c1", REVIEWER, repository=repo, audit=audit)
    assert exc.value.items[0]["id"] == "fnd_x"


@pytest.mark.asyncio
async def test_resolving_critical_unblocks_advance():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _case_at_internal_review(repo)
    await record_resolution(FindingResolution(case_id="c1", finding_id="fnd_x",
                            status="resolved", actor="rev"), repository=repo, audit=audit)
    assert await unresolved_critical("c1", repository=repo) == []
    case = await advance_case("c1", REVIEWER, repository=repo, audit=audit)
    assert case.stage == WorkflowStage.BOARD_PREPARATION


@pytest.mark.asyncio
async def test_deferred_does_not_clear_gate():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _case_at_internal_review(repo)
    await record_resolution(FindingResolution(case_id="c1", finding_id="fnd_x",
                            status="deferred", actor="rev"), repository=repo, audit=audit)
    assert len(await unresolved_critical("c1", repository=repo)) == 1   # still blocking


@pytest.mark.asyncio
async def test_dual_approval_override_passes_and_audits():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _case_at_internal_review(repo)
    case = await advance_case("c1", REVIEWER, repository=repo, audit=audit,
                              override_by=APPROVER2)
    assert case.stage == WorkflowStage.BOARD_PREPARATION
    incidents = [r for r in audit.read(50) if r.get("event") == "incident.board_gate_override"]
    assert incidents and incidents[-1]["approver_2"] == APPROVER2


@pytest.mark.asyncio
async def test_override_must_be_a_second_person():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _case_at_internal_review(repo)
    with pytest.raises(BoardGateBlocked):           # same actor can't self-override
        await advance_case("c1", REVIEWER, repository=repo, audit=audit, override_by="rev")


@pytest.mark.asyncio
async def test_warning_only_does_not_block():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _case_at_internal_review(repo, critical=False)
    case = await advance_case("c1", REVIEWER, repository=repo, audit=audit)
    assert case.stage == WorkflowStage.BOARD_PREPARATION
