"""Cross-document consistency agent.

Compares the artefacts of a case (review note vs board note vs decision doc
vs communication) against the master submission and flags inconsistencies,
outdated references, and missing updates — replacing the manual
reconciliation that consumes ~30% of senior reviewers' time.
"""
from pydantic import BaseModel

from app.agents.base import get_client, model_id
from app.core.audit import audit_log, new_trace_id
from app.models.schemas import ConsistencyFinding, ConsistencyReport
from app.rag.retriever import format_context, retrieve


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


async def check_consistency(case_id: str) -> ConsistencyReport:
    trace_id = new_trace_id()
    chunks = await retrieve(
        "amounts dates parties terms decisions references versions",
        k=24,
        case_id=case_id,
    )
    context = format_context(chunks)
    documents = sorted({c.document_id for c in chunks})

    client = get_client()
    response = await client.messages.parse(
        model=model_id(),
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=CONSISTENCY_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Document set for case {case_id} "
                f"({len(documents)} documents):\n{context}\n\n"
                "Audit the full set for inconsistencies, outdated references, "
                "and missing updates."
            ),
        }],
        output_format=FindingList,
    )
    findings = response.parsed_output.findings

    audit_log(
        "agent.consistency",
        trace_id,
        {
            "case_id": case_id,
            "model": model_id(),
            "documents_compared": documents,
            "findings_count": len(findings),
            "findings": [f.model_dump() for f in findings],
        },
    )
    return ConsistencyReport(
        case_id=case_id,
        findings=findings,
        documents_compared=documents,
        trace_id=trace_id,
    )
