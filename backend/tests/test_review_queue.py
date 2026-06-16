"""Auto-trigger + acknowledgment gate (Sprint 3.6, AC-2.7)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.use_cases.review_queue import (
    acknowledge_review,
    get_review_state,
    reaches_senior_inbox,
    summarize_acknowledgment,
)


def test_inbox_requires_submit_and_ack():
    assert reaches_senior_inbox(None) is False
    assert reaches_senior_inbox({"acknowledged": False}) is False
    assert reaches_senior_inbox({"acknowledged": True}) is True


@pytest.mark.asyncio
async def test_acknowledge_flips_state_and_reaches_inbox():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    # simulate submit (without the LLM consistency run)
    await repo.save_artefact("c1", "review_submission",
                             {"submitted_at": "2026-06-16T10:00:00", "acknowledged": False,
                              "critical_count": 0, "findings_count": 2})
    assert reaches_senior_inbox(await get_review_state("c1", repository=repo)) is False
    await acknowledge_review("c1", actor="analyst-1", repository=repo, audit=audit)
    state = await get_review_state("c1", repository=repo)
    assert state["acknowledged"] is True and state["ack_by"] == "analyst-1"
    assert reaches_senior_inbox(state) is True


@pytest.mark.asyncio
async def test_acknowledge_without_submission_raises():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    with pytest.raises(KeyError):
        await acknowledge_review("nope", actor="a", repository=repo, audit=audit)


def test_mtt_acknowledgment_summary():
    records = [
        {"event": "review.submitted", "case_id": "c1", "ts": "2026-06-16T10:00:00"},
        {"event": "review.acknowledged", "case_id": "c1", "ts": "2026-06-16T10:30:00"},
        {"event": "review.submitted", "case_id": "c2", "ts": "2026-06-16T09:00:00"},  # no ack
    ]
    s = summarize_acknowledgment(records)
    assert s["acknowledged"] == 1
    assert s["pending"] == 1
    assert s["mean_minutes_to_ack"] == 30.0
