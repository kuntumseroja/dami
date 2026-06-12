"""Extraction agent — pulls structured fields from ingested submissions."""
from pydantic import BaseModel

from app.agents.base import get_client, model_id
from app.core.audit import audit_log, new_trace_id
from app.rag.retriever import format_context, retrieve


class SubmissionFields(BaseModel):
    requesting_unit: str
    request_type: str
    amount_idr: float | None
    counterparty: str | None
    summary: str
    key_dates: list[str]


EXTRACTION_SYSTEM = """You extract structured facts from Danantara governance \
submission documents. Use ONLY the provided sources. If a field is not present \
in the sources, return null — never guess. Indonesian and English inputs are \
both expected."""


async def extract_submission_fields(case_id: str) -> tuple[SubmissionFields, str]:
    trace_id = new_trace_id()
    chunks = await retrieve(
        "request type amount counterparty requesting unit dates",
        k=12,
        case_id=case_id,
        doc_types=["submission"],
    )
    context = format_context(chunks)

    client = get_client()
    response = await client.messages.parse(
        model=model_id(),
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=EXTRACTION_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Sources:\n{context}\n\nExtract the submission fields.",
        }],
        output_format=SubmissionFields,
    )
    fields = response.parsed_output

    audit_log(
        "agent.extraction",
        trace_id,
        {
            "case_id": case_id,
            "model": model_id(),
            "sources": [c.ref for c in chunks],
            "output": fields.model_dump(),
        },
    )
    return fields, trace_id
