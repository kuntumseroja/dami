"""Cross-document consistency use case.

Compares the artefacts of a case (review note vs board note vs decision doc
vs communication) against the master submission and flags inconsistencies,
outdated references, and missing updates — replacing the manual
reconciliation that consumes ~30% of senior reviewers' time.
"""
from time import perf_counter

from pydantic import BaseModel

from app.domain.models import ConsistencyFinding, ConsistencyReport, new_trace_id
from app.domain.sla import sla_target_ms, within_sla
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    Embedder,
    ModelRouter,
    Reranker,
    VectorStore,
)
from app.use_cases.retrieval import format_context, retrieve


class FindingList(BaseModel):
    findings: list[ConsistencyFinding]


CONSISTENCY_SYSTEM = """You audit Danantara DAM governance document sets for \
consistency. The submission is the single source of truth; derived artefacts \
(review notes, board notes, decision documents, communications) must agree \
with it and with each other.

Flag every:
- inconsistency: conflicting facts (amounts, dates, names, terms) between documents
- outdated_reference: citation of a superseded version, regulation, or decision
- missing_update: a change present in one artefact but not propagated to another

For each finding quote the exact excerpts from both documents, classify \
severity (critical = changes the decision; major = misleads a reader; \
minor = cosmetic), and propose the resolution that aligns with the master \
submission. Report everything you find, including findings you are uncertain \
about — a human reviewer filters downstream. If documents are fully \
consistent, return an empty list."""


async def check_consistency(
    case_id: str, *, router: ModelRouter, embedder: Embedder,
    vectors: VectorStore, repository: CaseRepository, audit: AuditLog,
    reranker: Reranker | None = None,
) -> ConsistencyReport:
    trace_id = new_trace_id()
    started = perf_counter()
    llm = router.gateway("reasoning")
    chunks = await retrieve(
        "amounts dates parties terms decisions references versions",
        embedder=embedder, vectors=vectors, reranker=reranker,
        k=24, case_id=case_id,
    )
    documents = sorted({c.document_id for c in chunks})

    result = await llm.parse(
        system=CONSISTENCY_SYSTEM,
        prompt=(
            f"Document set for case {case_id} "
            f"({len(documents)} documents):\n{format_context(chunks)}\n\n"
            "Audit the full set for inconsistencies, outdated references, "
            "and missing updates."
        ),
        output_type=FindingList,
        max_tokens=16000,
    )
    report = ConsistencyReport(
        case_id=case_id,
        findings=result.findings,
        documents_compared=documents,
        trace_id=trace_id,
    )

    latency_ms = int((perf_counter() - started) * 1000)
    await repository.save_artefact(case_id, "consistency_report",
                                   report.model_dump(mode="json"))
    audit.log(
        "agent.consistency",
        trace_id,
        {
            "case_id": case_id,
            "model": llm.model,
            "documents_compared": documents,
            "findings_count": len(result.findings),
            "findings": [f.model_dump() for f in result.findings],
            "latency_ms": latency_ms,
            "sla_ms": sla_target_ms("agent.consistency"),
            "within_sla": within_sla("agent.consistency", latency_ms),
        },
    )
    return report
