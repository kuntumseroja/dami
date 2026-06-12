"""Extraction use case — pulls structured fields from ingested submissions."""
from app.domain.models import new_trace_id
from app.domain.models import SubmissionFields
from app.domain.ports import AuditLog, Embedder, LLMGateway, VectorStore
from app.use_cases.retrieval import format_context, retrieve

EXTRACTION_SYSTEM = """You extract structured facts from Danantara governance \
submission documents. Use ONLY the provided sources. If a field is not present \
in the sources, return null — never guess. Indonesian and English inputs are \
both expected."""


async def extract_submission_fields(
    case_id: str, *, llm: LLMGateway, embedder: Embedder,
    vectors: VectorStore, audit: AuditLog,
) -> tuple[SubmissionFields, str]:
    trace_id = new_trace_id()
    chunks = await retrieve(
        "request type amount counterparty requesting unit dates",
        embedder=embedder, vectors=vectors,
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
