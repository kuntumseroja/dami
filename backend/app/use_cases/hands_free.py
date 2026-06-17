"""Hands-free low-risk end-to-end (Sprint 4.8, FR-8 / FR-10 seed).

An eligible LOW-risk request runs intake → communication_dispatch with zero
human touches: the pipeline extracts/routes/drafts/checks, the parallel
workstreams auto-complete, and the case auto-advances through every stage
(low-risk stages have no human checkpoint). The full trace is reconstructable
from the audit log. Anything that isn't cleanly low-risk — or any gate that
blocks (unresolved Critical) — auto-escalates to a human (4.6), so the system
never auto-approves something it shouldn't.
"""
from app.domain.models import (
    REQUIRED_WORKSTREAMS,
    STAGE_ORDER,
    BoardGateBlocked,
    RiskTier,
    User,
    WorkflowStage,
    new_trace_id,
)
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    Embedder,
    ModelRouter,
    Reranker,
    TemplateStore,
    VectorStore,
)
from app.use_cases.automation_safety import escalate_to_human
from app.use_cases.manage_case import advance_case
from app.use_cases.run_pipeline import run_case_pipeline
from app.use_cases.workflow_ops import set_workstream

SYSTEM = User(id="system-automation", name="Automation", roles=[])
_TARGET = WorkflowStage.COMMUNICATION_DISPATCH


async def auto_advance(case_id: str, *, target: WorkflowStage, repository: CaseRepository,
                       audit: AuditLog) -> str:
    """Advance a (low-risk) case stage-by-stage to the target, no human touch."""
    for _ in range(len(STAGE_ORDER) + 1):       # bounded — never loops forever
        case = await repository.get(case_id)
        if case is None or case.stage == target or case.stage == WorkflowStage.CLOSED:
            break
        if STAGE_ORDER.index(case.stage) >= STAGE_ORDER.index(target):
            break
        await advance_case(case_id, SYSTEM, repository=repository, audit=audit)
    return (await repository.get(case_id)).stage.value


async def run_hands_free(
    case_id: str, *, router: ModelRouter, embedder: Embedder, vectors: VectorStore,
    repository: CaseRepository, audit: AuditLog, reranker: Reranker | None = None,
    templates: TemplateStore | None = None,
) -> dict:
    trace_id = new_trace_id()
    # 1. Run the multi-agent pipeline (sets risk tier; guarded by 4.6).
    await run_case_pipeline(case_id, SYSTEM, router=router, embedder=embedder,
                            vectors=vectors, repository=repository, audit=audit,
                            reranker=reranker, templates=templates)
    case = await repository.get(case_id)

    # 2. Eligibility: only fully LOW-risk cases run hands-free.
    if case.risk_tier != RiskTier.LOW:
        await escalate_to_human(case_id, "not eligible for hands-free (not low risk)",
                                repository=repository, audit=audit,
                                detail=f"risk_tier={case.risk_tier.value}")
        return {"hands_free": False, "reason": "not low risk",
                "risk_tier": case.risk_tier.value, "final_stage": case.stage.value}

    # 3. Auto-complete the parallel workstreams (no human).
    for stream in REQUIRED_WORKSTREAMS:
        await set_workstream(case_id, stream, "complete", repository=repository, audit=audit)

    # 4. Auto-advance to communication dispatch; a blocking gate escalates.
    try:
        final = await auto_advance(case_id, target=_TARGET,
                                   repository=repository, audit=audit)
    except BoardGateBlocked as exc:
        await escalate_to_human(case_id, "hands-free halted at board gate",
                                repository=repository, audit=audit, detail=str(exc))
        return {"hands_free": False, "reason": "critical items unresolved",
                "final_stage": (await repository.get(case_id)).stage.value}

    audit.log("hands_free.completed", trace_id,
              {"case_id": case_id, "final_stage": final, "touches": 0})
    return {"hands_free": True, "final_stage": final,
            "trace": [r for r in audit.read(5000) if r.get("case_id") == case_id]}
