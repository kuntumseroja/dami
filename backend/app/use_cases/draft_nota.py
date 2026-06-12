"""NOTA drafting use case.

Generates the *descriptive* 80% of a NOTA from submission documents,
templates, and historical notes retrieved via RAG. Judgment sections are
emitted as empty placeholders — they belong to the human reviewer by design.
"""
from pydantic import BaseModel

from app.domain.models import new_trace_id
from app.domain.models import DraftRequest, NotaDraft, NotaSection
from app.domain.ports import AuditLog, CaseRepository, Embedder, LLMGateway, VectorStore
from app.use_cases.retrieval import format_context, retrieve

# Default NOTA structure; Sprint 3 moves this into the template store.
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


async def draft_nota(
    request: DraftRequest, *, llm: LLMGateway, embedder: Embedder,
    vectors: VectorStore, repository: CaseRepository, audit: AuditLog,
) -> NotaDraft:
    trace_id = new_trace_id()
    chunks = await retrieve(
        "submission background legal basis chronology supporting data",
        embedder=embedder, vectors=vectors,
        k=16, case_id=request.case_id,
        doc_types=["submission", "historical_nota", "template"],
    )
    headings = "\n".join(f"- {h}" for h in DESCRIPTIVE_SECTIONS)
    extra = f"\nAdditional instructions: {request.instructions}" if request.instructions else ""

    drafted = await llm.parse(
        system=DRAFTING_SYSTEM,
        prompt=(
            f"Sources for case {request.case_id}:\n{format_context(chunks)}\n\n"
            f"Draft these descriptive sections:\n{headings}{extra}"
        ),
        output_type=DraftedSections,
        max_tokens=16000,
    )

    sections = [
        NotaSection(heading=s.heading, kind="descriptive", content=s.content,
                    sources=s.source_refs)
        for s in drafted.sections
    ] + [
        NotaSection(heading=h, kind="judgment", content="", sources=[])
        for h in JUDGMENT_SECTIONS
    ]
    draft = NotaDraft(
        case_id=request.case_id,
        title=drafted.title,
        sections=sections,
        model=llm.model,
        trace_id=trace_id,
    )

    await repository.save_artefact(request.case_id, "nota_draft",
                                   draft.model_dump(mode="json"))
    audit.log(
        "agent.drafting",
        trace_id,
        {
            "case_id": request.case_id,
            "model": llm.model,
            "sources": [c.ref for c in chunks],
            "sections_drafted": [s.heading for s in drafted.sections],
        },
    )
    return draft
