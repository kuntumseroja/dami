"""NOTA Review Panel — multi-agent specialist review (Sprint 3.10).

Heterogeneous MD specialist reviewers (Investment, Risk, Legal, Finance) each
score the draft against their governance-rubric dimensions with a skeptical
stance and a cited finding per issue. A deterministic citation gate drops any
uncited finding (RVW-003 / FR-1). The financial reconciliation agent contributes
recomputed arithmetic findings (RVW-007). A bias-controlled Chair then
adjudicates: dedup, severity, a recommendation, an explicit confidence score and
an unresolved-issues / needs-human-review block (RVW-008 / addendum A6).

The panel REVIEWS; it never approves — approval is a human decision gated by the
SOP delegation rules. Depth is risk-tier-gated (RVW-005).
"""
import os
from functools import lru_cache
from pathlib import Path
from time import perf_counter

import yaml
from pydantic import BaseModel

from app.domain.models import (
    ChairReport,
    DimensionScore,
    PanelFinding,
    PanelReview,
    ReviewerReport,
    new_trace_id,
)
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    Embedder,
    ModelRouter,
    Reranker,
    VectorStore,
)
from app.domain.sla import sla_target_ms, within_sla
from app.use_cases.reconcile_numbers import reconcile_numbers
from app.use_cases.retrieval import format_context, retrieve

_RULE_PREFIXES = ("SOP-", "APR-", "RSK-", "DIM-")


@lru_cache
def panel_config() -> dict:
    cfg = Path(os.environ.get("REVIEW_PANEL_CONFIG", "../config/review-panel.yaml"))
    if not cfg.exists():
        cfg = Path(__file__).resolve().parents[3] / "config/review-panel.yaml"
    return yaml.safe_load(cfg.read_text(encoding="utf-8"))


def _dimension_index() -> dict:
    return {d["id"]: d for d in panel_config().get("dimensions", [])}


def _reviewer_roles() -> list[dict]:
    # MD specialist lenses that run on the reasoning tier (exclude the
    # deterministic reconciliation + verifier helpers).
    return [r for r in panel_config().get("roles", [])
            if r.get("model_role") == "reasoning"]


def is_grounded_citation(citation: str, valid_refs: set[str]) -> bool:
    c = (citation or "").strip()
    return c in valid_refs or c.startswith(_RULE_PREFIXES)


# --- LLM output schemas -------------------------------------------------------

class _ReviewerFinding(BaseModel):
    dimension: str
    severity: str
    title: str
    detail: str
    citation: str = ""


class _ReviewerOut(BaseModel):
    findings: list[_ReviewerFinding]
    confidence: float


class _DimScore(BaseModel):
    dimension: str
    severity: str
    status: str = ""


class _ChairOut(BaseModel):
    recommendation: str
    confidence: float
    summary: str
    dimension_scores: list[_DimScore]
    unresolved_issues: list[str]
    needs_human_review: bool


def _draft_text(draft: dict) -> str:
    return "\n\n".join(f"## {s['heading']}\n{s.get('content', '')}"
                       for s in draft.get("sections", []))


def _reviewer_system(role: dict, dims: dict) -> str:
    dim_lines = "\n".join(
        f"- {d}: {dims.get(d, {}).get('name', d)}" for d in role.get("dimensions", []))
    return (
        f"You are the {role['title']} on Danantara DAM's NOTA review panel, acting "
        f"as the {role.get('danantara_role', role['title'])}. Review the draft NOTA "
        f"with a SKEPTICAL stance — surface dissent, do not rubber-stamp. You review: "
        f"{role.get('reviews', '')}.\n\nScore ONLY these rubric dimensions:\n{dim_lines}\n\n"
        "For each issue produce a finding with: dimension (the id above), severity "
        "(critical/major/minor), a short title, detail, and a `citation` that is EITHER "
        "the exact `ref` of a <source> you relied on (e.g. doc_a1b2#0) OR a rule id "
        "(SOP-/APR-/RSK-). A finding without a resolvable citation will be dropped. "
        "Do not invent facts. Also give an overall confidence 0..1. If the draft is "
        "sound on your dimensions, return an empty findings list with high confidence."
    )


CHAIR_SYSTEM = (
    "You are the Review Chair adjudicating Danantara DAM's NOTA review panel "
    "(Level-3 executive endorsement). You receive the panel's cited findings. "
    "Bias controls: judge findings on substance not order or length; never add "
    "uncited claims. Deduplicate overlapping findings, assign a severity per "
    "rubric dimension, and produce: recommendation (endorse / "
    "endorse_with_conditions / return_for_revision), an overall confidence 0..1, "
    "a short summary, dimension_scores, an explicit unresolved_issues list, and "
    "needs_human_review (true unless every critical dimension is clean). You "
    "REVIEW only — the human four-eyes checker decides; never claim to approve."
)


async def run_review_panel(
    case_id: str, *, router: ModelRouter, embedder: Embedder, vectors: VectorStore,
    repository: CaseRepository, audit: AuditLog, reranker: Reranker | None = None,
) -> PanelReview:
    trace_id = new_trace_id()
    started = perf_counter()

    drafts = await repository.list_artefacts(case_id, "nota_draft")
    if not drafts:
        raise KeyError(f"no draft to review for case {case_id}")
    draft = drafts[-1].get("payload", drafts[-1])
    case = await repository.get(case_id)
    risk_tier = case.risk_tier.value if case else "medium"

    chunks = await retrieve(
        "background legal basis financial risk valuation disclosure precedent",
        embedder=embedder, vectors=vectors, reranker=reranker, k=20, case_id=case_id)
    valid_refs = {c.ref for c in chunks}
    context = format_context(chunks)
    draft_text = _draft_text(draft)
    dims = _dimension_index()

    # --- Round 1: independent specialist review --------------------------------
    reviewers: list[ReviewerReport] = []
    all_findings: list[PanelFinding] = []
    dropped = 0
    for role in _reviewer_roles():
        llm = router.gateway(role.get("model_role", "reasoning"))
        out = await llm.parse(
            system=_reviewer_system(role, dims),
            prompt=(f"Sources:\n{context}\n\nDraft NOTA under review:\n{draft_text}\n\n"
                    "Return your findings and confidence."),
            output_type=_ReviewerOut, max_tokens=8000,
        )
        rfindings = []
        for f in out.findings:
            grounded = is_grounded_citation(f.citation, valid_refs)
            if not grounded:
                dropped += 1
                continue                       # RVW-003: uncited findings dropped
            sev = f.severity if f.severity in ("critical", "major", "minor") else "major"
            pf = PanelFinding(reviewer_id=role["id"], reviewer_title=role["title"],
                              dimension=f.dimension, severity=sev, title=f.title,
                              detail=f.detail, citation=f.citation, grounded=True)
            rfindings.append(pf)
            all_findings.append(pf)
        reviewers.append(ReviewerReport(reviewer_id=role["id"], title=role["title"],
                                        findings=rfindings,
                                        confidence=round(float(out.confidence or 0), 3)))

    # --- DIM-CALC: deterministic reconciliation findings (RVW-007) -------------
    recon = await reconcile_numbers(case_id, router=router, embedder=embedder,
                                    vectors=vectors, repository=repository,
                                    audit=audit, reranker=reranker)
    for m in [f for f in recon.findings if f.status == "mismatch"]:
        pf = PanelFinding(
            reviewer_id="financial_reconciliation",
            reviewer_title="Financial & Statistical Reconciliation Agent",
            dimension="DIM-CALC", severity="critical", title=m.description,
            detail=m.explanation, citation=(m.source_refs[0] if m.source_refs else "DIM-CALC"),
            grounded=True)
        all_findings.append(pf)

    # --- Adjudication: bias-controlled Chair (RVW-008 / A6) --------------------
    chair_llm = router.gateway("reasoning")
    findings_blob = "\n".join(
        f"- [{f.reviewer_title} · {f.dimension} · {f.severity}] {f.title}: {f.detail} "
        f"(cite: {f.citation})" for f in all_findings) or "(no findings raised)"
    chair_out = await chair_llm.parse(
        system=CHAIR_SYSTEM,
        prompt=(f"Risk tier: {risk_tier}. Panel findings (already citation-gated):\n"
                f"{findings_blob}\n\nAdjudicate per the rubric and report."),
        output_type=_ChairOut, max_tokens=6000,
    )
    chair = ChairReport(
        recommendation=(chair_out.recommendation
                        if chair_out.recommendation in
                        ("endorse", "endorse_with_conditions", "return_for_revision")
                        else "return_for_revision"),
        confidence=round(float(chair_out.confidence or 0), 3),
        summary=chair_out.summary,
        dimension_scores=[
            DimensionScore(dimension=d.dimension,
                           severity=d.severity if d.severity in
                           ("critical", "major", "minor", "ok") else "ok",
                           status=d.status)
            for d in chair_out.dimension_scores],
        unresolved_issues=chair_out.unresolved_issues,
        needs_human_review=bool(chair_out.needs_human_review),
    )

    latency_ms = int((perf_counter() - started) * 1000)
    review = PanelReview(
        case_id=case_id, risk_tier=risk_tier, reviewers=reviewers,
        findings=all_findings, dropped_uncited=dropped, chair=chair,
        trace_id=trace_id, latency_ms=latency_ms)

    await repository.save_artefact(case_id, "panel_review", review.model_dump(mode="json"))
    audit.log("agent.review_panel", trace_id, {
        "case_id": case_id, "risk_tier": risk_tier,
        "reviewers": [r.reviewer_id for r in reviewers],
        "findings": len(all_findings), "dropped_uncited": dropped,
        "recommendation": chair.recommendation, "confidence": chair.confidence,
        "needs_human_review": chair.needs_human_review,
        "latency_ms": latency_ms, "sla_ms": sla_target_ms("agent.review_panel"),
        "within_sla": within_sla("agent.review_panel", latency_ms),
    })
    return review
