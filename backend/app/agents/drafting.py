"""NOTA drafting agent.

Generates the *descriptive* 80% of a NOTA from submission documents,
templates, and historical notes retrieved via RAG. Judgment sections are
emitted as empty placeholders — they belong to the human reviewer by design
(requirement B/D: AI does the restating, humans keep the judgment).
"""
from pydantic import BaseModel

from app.agents.base import get_client, model_id
from app.core.audit import audit_log, new_trace_id
from app.models.schemas import DraftRequest, NotaDraft, NotaSection
from app.rag.retriever import format_context, retrieve

# Default NOTA structure; replace per-template via the templates store.
DESCRIPTIVE_SECTIONS = [
    "Latar Belakang (Background)",
    "Ringkasan Permohonan (Request Summary)",
    "Dasar Hukum & Referensi (Legal Basis & References)",
    "Kronologi & Status (Chronology & Status)",
    "Data Pendukung (Supporting Data)",
]
JUDGMENT_SECTIONS = [
    "Analisis & Pertimbangan (Analysis & Considerations)",
    "Rekomendasi (Recommendation)",
]


class DraftedSection(BaseModel):
    heading: str
    content: str
    source_refs: list[str]


class DraftedSections(BaseModel):
    title: str
    sections: list[DraftedSection]


DRAFTING_SYSTEM = """You draft the descriptive sections of Danantara DAM \
governance NOTA documents.

Hard rules:
- Use ONLY facts present in the provided <source> blocks. Every paragraph must \
be supported by at least one source; list the supporting source refs per section.
- Do NOT analyse, judge, or recommend. Descriptive restatement only — analysis \
and recommendations are reserved for human reviewers.
- Match the formal register of Indonesian state-enterprise governance documents. \
Write in Bahasa Indonesia unless the sources are predominantly English.
- If sources are insufficient for a section, write "[DATA TIDAK TERSEDIA — \
mohon dilengkapi]" rather than inventing content."""


async def draft_nota(request: DraftRequest) -> NotaDraft:
    trace_id = new_trace_id()
    chunks = await retrieve(
        "submission background legal basis chronology supporting data",
        k=16,
        case_id=request.case_id,
        doc_types=["submission", "historical_nota", "template"],
    )
    context = format_context(chunks)
    headings = "\n".join(f"- {h}" for h in DESCRIPTIVE_SECTIONS)
    instructions = f"\nAdditional instructions: {request.instructions}" if request.instructions else ""

    client = get_client()
    response = await client.messages.parse(
        model=model_id(),
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=DRAFTING_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Sources for case {request.case_id}:\n{context}\n\n"
                f"Draft these descriptive sections:\n{headings}{instructions}"
            ),
        }],
        output_format=DraftedSections,
    )
    drafted = response.parsed_output

    sections = [
        NotaSection(heading=s.heading, kind="descriptive", content=s.content, sources=s.source_refs)
        for s in drafted.sections
    ] + [
        NotaSection(heading=h, kind="judgment", content="", sources=[])
        for h in JUDGMENT_SECTIONS
    ]

    audit_log(
        "agent.drafting",
        trace_id,
        {
            "case_id": request.case_id,
            "model": model_id(),
            "sources": [c.ref for c in chunks],
            "sections_drafted": [s.heading for s in drafted.sections],
        },
    )
    return NotaDraft(
        case_id=request.case_id,
        title=drafted.title,
        sections=sections,
        model=model_id(),
        trace_id=trace_id,
    )
