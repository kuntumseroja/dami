"""Multi-agent orchestration: extraction → routing → drafting → consistency.

Low-risk cases flow through without pausing; medium/high-risk cases stop at
the workflow engine's human checkpoints. This is the seed of the long-term
agentic governance vision.
"""
from time import perf_counter

from app.domain.models import DraftRequest, RoutingRequest, User, new_trace_id
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    Embedder,
    ModelRouter,
    Reranker,
    VectorStore,
)
from app.domain.sla import sla_target_ms, within_sla
from app.use_cases.check_consistency import check_consistency
from app.use_cases.draft_nota import draft_nota
from app.use_cases.extract_fields import extract_submission_fields
from app.use_cases.manage_case import set_risk_tier
from app.use_cases.route_request import route_request


async def run_case_pipeline(
    case_id: str, user: User, *, router: ModelRouter, embedder: Embedder,
    vectors: VectorStore, repository: CaseRepository, audit: AuditLog,
    reranker: Reranker | None = None,
) -> dict:
    trace_id = new_trace_id()
    started = perf_counter()
    case = await repository.get(case_id)
    if case is None:
        raise KeyError(f"unknown case {case_id}")

    # 1. Extract structured facts from the ingested submission.
    fields, extraction_trace = await extract_submission_fields(
        case_id, router=router, embedder=embedder, vectors=vectors, audit=audit,
        reranker=reranker)

    # 2. Deterministic routing → sets the case's risk tier / automation level.
    #    Use the canonical request_category enum so SOP selection is exact.
    routing = await route_request(
        RoutingRequest(
            case_id=case_id,
            request_type=fields.request_category,
            amount_idr=fields.amount_idr,
            business_unit=fields.requesting_unit,
        ),
        router=router, repository=repository, audit=audit,
    )
    await set_risk_tier(case_id, routing.risk_tier, actor="rule_engine",
                        repository=repository, audit=audit)

    # 3. Draft the descriptive NOTA sections.
    draft = await draft_nota(
        DraftRequest(case_id=case_id),
        router=router, embedder=embedder, vectors=vectors,
        repository=repository, audit=audit, reranker=reranker,
    )

    # 4. Audit the document set for consistency.
    report = await check_consistency(
        case_id, router=router, embedder=embedder, vectors=vectors,
        repository=repository, audit=audit, reranker=reranker,
    )

    latency_ms = int((perf_counter() - started) * 1000)
    audit.log(
        "orchestrator.pipeline_completed",
        trace_id,
        {
            "case_id": case_id,
            "actor": user.id,
            "risk_tier": routing.risk_tier.value,
            "child_traces": [extraction_trace, routing.trace_id,
                             draft.trace_id, report.trace_id],
            "findings": len(report.findings),
            "latency_ms": latency_ms,
            "sla_ms": sla_target_ms("orchestrator.pipeline_completed"),
            "within_sla": within_sla("orchestrator.pipeline_completed", latency_ms),
        },
    )
    return {
        "case": (await repository.get(case_id)).model_dump(mode="json"),
        "extracted_fields": fields.model_dump(),
        "routing": routing.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
        "consistency": report.model_dump(mode="json"),
        "trace_id": trace_id,
    }
