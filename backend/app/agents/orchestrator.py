"""Multi-agent orchestrator.

Runs the agent pipeline for a case at each workflow stage:
  ingestion → extraction → routing (risk tier) → drafting → consistency.

Low-risk cases flow through without pausing; medium/high-risk cases stop at
the workflow engine's human checkpoints. This is the seed of the long-term
agentic governance vision (agents draft / validate / route / flag; humans
intervene only where needed).
"""
from app.agents.consistency import check_consistency
from app.agents.drafting import draft_nota
from app.agents.extraction import extract_submission_fields
from app.agents.routing import route_request
from app.core.audit import audit_log, new_trace_id
from app.models.schemas import DraftRequest, RoutingRequest
from app.workflow import engine


async def run_case_pipeline(case_id: str) -> dict:
    """Run the full agent pipeline for a case and return all artefacts."""
    trace_id = new_trace_id()
    case = engine.get_case(case_id)
    if case is None:
        raise KeyError(f"unknown case {case_id}")

    # 1. Extract structured facts from the ingested submission.
    fields, extraction_trace = await extract_submission_fields(case_id)

    # 2. Deterministic routing → sets the case's risk tier / automation level.
    routing = await route_request(
        RoutingRequest(
            case_id=case_id,
            request_type=fields.request_type,
            amount_idr=fields.amount_idr,
            business_unit=fields.requesting_unit,
        )
    )
    engine.set_risk_tier(case_id, routing.risk_tier)

    # 3. Draft the descriptive NOTA sections.
    draft = await draft_nota(DraftRequest(case_id=case_id))

    # 4. Audit the document set for consistency.
    report = await check_consistency(case_id)

    audit_log(
        "orchestrator.pipeline_completed",
        trace_id,
        {
            "case_id": case_id,
            "risk_tier": routing.risk_tier.value,
            "child_traces": [extraction_trace, routing.trace_id, draft.trace_id, report.trace_id],
            "findings": len(report.findings),
        },
    )
    return {
        "case": engine.get_case(case_id),
        "extracted_fields": fields.model_dump(),
        "routing": routing.model_dump(),
        "draft": draft.model_dump(),
        "consistency": report.model_dump(),
        "trace_id": trace_id,
    }
