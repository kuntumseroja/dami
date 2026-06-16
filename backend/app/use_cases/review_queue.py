"""Senior-review queue: auto-trigger + acknowledgment gate (Sprint 3.6, AC-2.7).

When a file is submitted to the senior review queue the consistency check runs
automatically; the file does not reach the senior officer's inbox until the
check has completed AND the submitting analyst has acknowledged the report.
Mean-time-to-acknowledgment is measured from the audit trail.
"""
from datetime import datetime

from app.domain.models import new_trace_id, utcnow
from app.domain.ports import AuditLog, CaseRepository, Embedder, ModelRouter, Reranker, VectorStore
from app.use_cases.check_consistency import check_consistency

_KIND = "review_submission"


async def submit_to_review(
    case_id: str, *, actor: str, router: ModelRouter, embedder: Embedder,
    vectors: VectorStore, repository: CaseRepository, audit: AuditLog,
    reranker: Reranker | None = None,
) -> dict:
    """Auto-run the consistency check and queue the file pending acknowledgment."""
    report = await check_consistency(
        case_id, router=router, embedder=embedder, vectors=vectors,
        repository=repository, audit=audit, reranker=reranker)
    critical = sum(1 for f in report.findings if f.severity == "critical")
    record = {
        "submitted_at": utcnow().isoformat(), "submitted_by": actor,
        "acknowledged": False, "ack_by": None, "ack_at": None,
        "consistency_trace": report.trace_id,
        "findings_count": len(report.findings), "critical_count": critical,
    }
    await repository.save_artefact(case_id, _KIND, record)
    audit.log("review.submitted", new_trace_id(),
              {"case_id": case_id, "actor": actor,
               "findings_count": len(report.findings), "critical_count": critical})
    return record


async def get_review_state(case_id: str, *, repository: CaseRepository) -> dict | None:
    artefacts = await repository.list_artefacts(case_id, _KIND)
    return artefacts[-1].get("payload", artefacts[-1]) if artefacts else None


async def acknowledge_review(
    case_id: str, *, actor: str, repository: CaseRepository, audit: AuditLog,
) -> dict:
    state = await get_review_state(case_id, repository=repository)
    if state is None:
        raise KeyError(f"no review submission for case {case_id}")
    acked = {**state, "acknowledged": True, "ack_by": actor,
             "ack_at": utcnow().isoformat()}
    await repository.save_artefact(case_id, _KIND, acked)
    audit.log("review.acknowledged", new_trace_id(),
              {"case_id": case_id, "actor": actor})
    return acked


def reaches_senior_inbox(state: dict | None) -> bool:
    """A file reaches the senior inbox only once submitted AND acknowledged."""
    return bool(state) and state.get("acknowledged") is True


def summarize_acknowledgment(records: list[dict]) -> dict:
    """Mean time-to-acknowledgment (minutes) from the audit trail."""
    submitted: dict[str, str] = {}
    deltas: list[float] = []
    pending = 0
    for r in records:                       # audit is newest-first; take earliest submit
        if r.get("event") == "review.submitted":
            submitted[r["case_id"]] = r.get("ts", "")
    acked_cases = set()
    for r in records:
        if r.get("event") == "review.acknowledged" and r["case_id"] in submitted:
            acked_cases.add(r["case_id"])
            try:
                sub = datetime.fromisoformat(submitted[r["case_id"]])
                ack = datetime.fromisoformat(r.get("ts", ""))
                deltas.append((ack - sub).total_seconds() / 60.0)
            except (ValueError, TypeError):
                continue
    pending = len(set(submitted) - acked_cases)
    mean = round(sum(deltas) / len(deltas), 2) if deltas else None
    return {"acknowledged": len(acked_cases), "pending": pending,
            "mean_minutes_to_ack": mean}
