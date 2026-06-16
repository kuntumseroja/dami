"""Finding resolution workflow (Sprint 3.5, FR-2 AC-2.6)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import ConsistencyFinding, FindingResolution, finding_id
from app.use_cases.resolve_findings import (
    ResolutionInvalid,
    get_resolution_state,
    record_resolution,
    summarize_false_positives,
)


def _f(**kw):
    base = dict(severity="critical", kind="numeric_mismatch", description="d",
                document_a="A", excerpt_a="Rp420", document_b="B", excerpt_b="Rp415",
                suggested_resolution="align")
    base.update(kw)
    return ConsistencyFinding(**base)


def test_finding_id_is_stable_across_runs():
    f1, f2 = _f(), _f()
    assert finding_id("c1", f1) == finding_id("c1", f2)        # same content → same id
    assert finding_id("c1", f1) != finding_id("c2", f1)        # case-scoped


@pytest.mark.asyncio
async def test_latest_resolution_wins():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    fid = "fnd_abc"
    await record_resolution(FindingResolution(case_id="c1", finding_id=fid,
                            status="deferred", actor="u1"), repository=repo, audit=audit)
    await record_resolution(FindingResolution(case_id="c1", finding_id=fid,
                            status="resolved", actor="u2"), repository=repo, audit=audit)
    state = await get_resolution_state("c1", repository=repo)
    assert state[fid]["status"] == "resolved" and state[fid]["actor"] == "u2"


@pytest.mark.asyncio
async def test_accepted_as_is_requires_justification():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    with pytest.raises(ResolutionInvalid):
        await record_resolution(FindingResolution(case_id="c1", finding_id="f",
                                status="accepted_as_is", actor="u1"),
                                repository=repo, audit=audit)
    # with justification it succeeds
    ok = await record_resolution(FindingResolution(case_id="c1", finding_id="f",
                                 status="accepted_as_is", justification="risk accepted by CRO",
                                 actor="u1"), repository=repo, audit=audit)
    assert ok.status == "accepted_as_is"


def test_false_positive_summary():
    records = [
        {"event": "finding.resolution", "status": "resolved", "kind": "numeric_mismatch"},
        {"event": "finding.resolution", "status": "incorrect_flag", "kind": "date_mismatch"},
        {"event": "finding.resolution", "status": "incorrect_flag", "kind": "date_mismatch"},
        {"event": "agent.drafting"},                       # ignored
    ]
    s = summarize_false_positives(records)
    assert s["false_positives"] == 2
    assert s["resolutions"] == 3
    assert s["by_kind"]["date_mismatch"] == 2
    assert s["false_positive_rate"] == round(2 / 3, 4)
