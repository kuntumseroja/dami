"""Extraction use case — pulls structured fields from ingested submissions."""
from app.domain.models import SubmissionFields, new_trace_id
from app.domain.ports import AuditLog, Embedder, ModelRouter, Reranker, VectorStore
from app.use_cases.retrieval import format_context, retrieve

EXTRACTION_SYSTEM = """You extract structured facts from Danantara governance \
submission documents. Use ONLY the provided sources. If a field is not present \
in the sources, return null — never guess. Indonesian and English inputs are \
both expected.

Also classify the request into `request_category` — one of asset_disposal, \
asset_acquisition, investment, asset_lease, asset_utilization, or other — so \
the routing rule engine can select the correct SOP. (e.g. "divestasi"/sale = \
asset_disposal; "penyertaan modal"/equity = investment; "sewa"/lease = \
asset_lease.)"""


async def extract_submission_fields(
    case_id: str, *, router: ModelRouter, embedder: Embedder,
    vectors: VectorStore, audit: AuditLog, reranker: Reranker | None = None,
) -> tuple[SubmissionFields, str]:
    trace_id = new_trace_id()
    llm = router.gateway("extraction")
    chunks = await retrieve(
        "request type amount counterparty requesting unit dates",
        embedder=embedder, vectors=vectors, reranker=reranker,
        k=12, case_id=case_id, doc_types=["submission"],
    )
    fields = await llm.parse(
        system=EXTRACTION_SYSTEM,
        prompt=f"Sources:\n{format_context(chunks)}\n\nExtract the submission fields.",
        output_type=SubmissionFields,
        max_tokens=4096,
    )
    audit.log(
        "agent.extraction",
        trace_id,
        {
            "case_id": case_id,
            "model": llm.model,
            "sources": [c.ref for c in chunks],
            "output": fields.model_dump(),
        },
    )
    return fields, trace_id
