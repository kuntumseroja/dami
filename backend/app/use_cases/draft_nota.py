"""NOTA drafting use case.

Generates the *descriptive* 80% of a NOTA from submission documents,
templates, and historical notes retrieved via RAG. Judgment sections are
emitted as empty placeholders — they belong to the human reviewer by design.
"""
from time import perf_counter

from pydantic import BaseModel

from app.domain.models import DraftRequest, NotaDraft, NotaSection, new_trace_id
from app.domain.sla import sla_target_ms, within_sla
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    Embedder,
    ModelRouter,
    Reranker,
    VectorStore,
)
from app.use_cases.grounding import enforce_grounding
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
be supported by at least one source.
- In `source_refs`, put ONLY the exact value of the `ref` attribute of the \
<source ref="..."> blocks you used — e.g. "doc_a1b2c3d4#0". Copy the ref \
string verbatim. NEVER put document titles, paraphrases, entity names, or any \
other text in source_refs; an unrecognised ref causes the section to be \
suppressed by the traceability gate.
- Do NOT analyse, judge, or recommend. Descriptive restatement only — analysis \
and recommendations are reserved for human reviewers.
- Match the formal register of Indonesian state-enterprise governance documents. \
Write in Bahasa Indonesia unless the sources are predominantly English.
- If sources are insufficient for a section, write "[DATA TIDAK TERSEDIA — \
mohon dilengkapi]" rather than inventing content."""


async def draft_nota(
    request: DraftRequest, *, router: ModelRouter, embedder: Embedder,
    vectors: VectorStore, repository: CaseRepository, audit: AuditLog,
    reranker: Reranker | None = None,
) -> NotaDraft:
    trace_id = new_trace_id()
    started = perf_counter()
    llm = router.gateway("drafting")
    chunks = await retrieve(
        "submission background legal basis chronology supporting data",
        embedder=embedder, vectors=vectors, reranker=reranker,
        k=16, case_id=request.case_id,
        doc_types=["submission", "historical_nota", "template"],
    )
    headings = "\n".join(f"- {h}" for h in DESCRIPTIVE_SECTIONS)
    extra = f"\nAdditional instructions: {request.instructions}" if request.instructions else ""

    drafted = await llm.parse(
        system=DRAFTING_SYSTEM,
        prompt=(
            f"Sources for case {request.case_id}:\n{format_context(chunks)}\n\n"
            f"Return exactly one section object for EACH heading below, in this "
            f"order, omitting none. Use the heading text verbatim. For each, "
            f"cite the source refs you used (verbatim ref values):\n{headings}{extra}"
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

    # Hard source-traceability gate (FR-1, AC-1.3): no descriptive content is
    # rendered unless it cites a source ref that actually resolves to a chunk
    # retrieved for this case. Hallucinated citations are stripped; ungrounded
    # content is suppressed to a low-confidence placeholder.
    valid_refs = {c.ref for c in chunks}
    sections, grounding_report = enforce_grounding(sections, valid_refs)

    latency_ms = int((perf_counter() - started) * 1000)
    draft = NotaDraft(
        case_id=request.case_id,
        title=drafted.title,
        sections=sections,
        model=llm.model,
        trace_id=trace_id,
        latency_ms=latency_ms,
        coverage=grounding_report["coverage"],
        source_sufficient=grounding_report["sufficient"],
        insufficient_sections=grounding_report["insufficient_sections"],
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
            "grounding_gate": grounding_report,   # checked / passed / suppressed / stripped_refs
            "latency_ms": latency_ms,
            "sla_ms": sla_target_ms("agent.drafting"),
            "within_sla": within_sla("agent.drafting", latency_ms),
        },
    )
    return draft
