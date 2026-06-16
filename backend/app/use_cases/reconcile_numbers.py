"""Financial & statistical reconciliation agent (Sprint 3.11, addendum A1).

Two-step, with a hard separation of concerns:

  1. EXTRACT (LLM) — pull every numeric claim that asserts an arithmetic
     relationship (percentage, difference, sum, ratio, …) out of the documents,
     as structured operands + the result the document *states*. The model does
     NOT do arithmetic.
  2. RECOMPUTE (deterministic) — a pure Python calculator recomputes each result
     from the operands and flags any stated figure that disagrees beyond
     tolerance, citing the source numbers and the recomputed value.

This catches the planted "13.2% vs 130%" gain-on-disposal error and wrong
numerator/denominator mistakes — the kind LLM mental math silently reproduces.
"""
from time import perf_counter

from app.domain.models import (
    ClaimList,
    NumericClaim,
    ReconciliationFinding,
    ReconciliationReport,
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
from app.use_cases.retrieval import format_context, retrieve

# Relative tolerance for a recomputed vs stated figure (1%).
TOLERANCE = 0.01


def recompute(relationship: str, operands: list[float]) -> float | None:
    """Deterministically evaluate the asserted relationship. None = uncomputable."""
    o = operands
    try:
        if relationship == "sum":
            return float(sum(o)) if o else None
        if relationship == "percentage_change":
            return (o[0] - o[1]) / o[1] * 100 if len(o) >= 2 and o[1] != 0 else None
        if relationship == "percentage_of":
            return o[0] / o[1] * 100 if len(o) >= 2 and o[1] != 0 else None
        if relationship == "difference":
            return o[0] - o[1] if len(o) >= 2 else None
        if relationship == "ratio":
            return o[0] / o[1] if len(o) >= 2 and o[1] != 0 else None
        if relationship == "product":
            result = 1.0
            for v in o:
                result *= v
            return result if o else None
    except (IndexError, ZeroDivisionError, TypeError):
        return None
    return None


def _evaluate(claim: NumericClaim) -> ReconciliationFinding:
    expected = recompute(claim.relationship, claim.operands)
    if expected is None:
        return ReconciliationFinding(
            description=claim.description, relationship=claim.relationship,
            operands=claim.operands, claimed_result=claim.claimed_result,
            recomputed_result=None, status="uncomputable", severity="info",
            source_refs=claim.source_refs,
            explanation="Insufficient or invalid operands to recompute this figure.",
        )
    rel_err = abs(expected - claim.claimed_result) / max(abs(expected), 1.0)
    if rel_err <= TOLERANCE:
        return ReconciliationFinding(
            description=claim.description, relationship=claim.relationship,
            operands=claim.operands, claimed_result=claim.claimed_result,
            recomputed_result=round(expected, 4), status="ok", severity="info",
            source_refs=claim.source_refs,
            explanation="Stated figure matches the recomputed value.",
        )
    severity = "critical" if rel_err > 0.10 else "major"
    return ReconciliationFinding(
        description=claim.description, relationship=claim.relationship,
        operands=claim.operands, claimed_result=claim.claimed_result,
        recomputed_result=round(expected, 4), status="mismatch", severity=severity,
        source_refs=claim.source_refs,
        explanation=(
            f"Stated {claim.claimed_result}{claim.unit or ''} but {claim.relationship} "
            f"of {claim.operands} recomputes to {round(expected, 4)}{claim.unit or ''} "
            f"(relative error {rel_err:.1%})."
        ),
    )


def reconcile_claims(claims: list[NumericClaim]) -> list[ReconciliationFinding]:
    """Pure: recompute every claim and grade it. No model, no I/O."""
    return [_evaluate(c) for c in claims]


EXTRACTION_SYSTEM = """You extract numeric claims from Danantara DAM governance \
documents for an automated reconciliation check. Find every figure that asserts \
an arithmetic relationship — a percentage change/gain, a percentage-of-base, a \
difference, a sum/total, a ratio, or a product.

For each, return:
- relationship: one of percentage_change, percentage_of, difference, sum, ratio, product
- operands: the SOURCE numbers in formula order (for percentage_change use [new, base]; \
for percentage_of use [part, whole]). Use raw numbers (e.g. 420000000000), not text.
- claimed_result: the result EXACTLY as stated in the document (e.g. 130 for "130%").
- unit: "%", "IDR", "x", or null.
- source_refs: the exact <source ref="..."> values you used.

CRITICAL: do NOT compute or correct anything. Report operands and the stated \
result verbatim — a deterministic calculator verifies them. Only include claims \
whose operands are present in the sources. If none, return an empty list."""


async def reconcile_numbers(
    case_id: str, *, router: ModelRouter, embedder: Embedder,
    vectors: VectorStore, repository: CaseRepository, audit: AuditLog,
    reranker: Reranker | None = None,
) -> ReconciliationReport:
    trace_id = new_trace_id()
    started = perf_counter()
    llm = router.gateway("extraction")        # extraction is light; math is ours
    chunks = await retrieve(
        "nilai book value appraisal gain percentage IRR total amount ratio growth",
        embedder=embedder, vectors=vectors, reranker=reranker, k=20, case_id=case_id,
    )
    extracted = await llm.parse(
        system=EXTRACTION_SYSTEM,
        prompt=(f"Sources for case {case_id}:\n{format_context(chunks)}\n\n"
                "Extract the numeric claims as instructed."),
        output_type=ClaimList,
        max_tokens=4096,
    )

    findings = reconcile_claims(extracted.claims)
    mismatches = sum(1 for f in findings if f.status == "mismatch")
    latency_ms = int((perf_counter() - started) * 1000)
    report = ReconciliationReport(
        case_id=case_id, findings=findings, claims_checked=len(findings),
        mismatches=mismatches, trace_id=trace_id, latency_ms=latency_ms,
    )

    await repository.save_artefact(case_id, "reconciliation_report",
                                   report.model_dump(mode="json"))
    audit.log(
        "agent.reconciliation",
        trace_id,
        {
            "case_id": case_id,
            "model": llm.model,
            "claims_checked": len(findings),
            "mismatches": mismatches,
            "findings": [f.model_dump() for f in findings],
            "latency_ms": latency_ms,
            "sla_ms": sla_target_ms("agent.reconciliation"),
            "within_sla": within_sla("agent.reconciliation", latency_ms),
        },
    )
    return report
