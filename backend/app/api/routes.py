"""Thin HTTP controllers — translate requests to use-case calls, nothing more."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.domain.models import (
    HUMAN_CHECKPOINTS,
    STAGE_SPEC,
    BoardGateBlocked,
    ConsistencyReport,
    DocumentImmutable,
    DocumentLocked,
    NotLockHolder,
    DataClassification,
    DocumentType,
    DraftRequest,
    IngestionResult,
    FindingResolution,
    NotaDraft,
    PanelReview,
    ParagraphAction,
    ReconciliationReport,
    RiskTier,
    Role,
    RoutingDecision,
    RoutingRequest,
    SignoffRequired,
    User,
)
from app.domain.rules import decision_tree, evaluate, sop_catalogue, sop_coverage
from app.domain.taxonomy import CONSISTENCY_TYPES, default_severities
from app.infrastructure.container import Container, get_container
from app.infrastructure.security import get_current_user, require_roles
from app.use_cases import manage_case, manage_document, versioning
from app.use_cases.board_gate import unresolved_critical
from app.use_cases.check_consistency import check_consistency
from app.use_cases.cover_checklist import build_cover_checklist
from app.use_cases.metrics import summarize_latency
from app.use_cases.reconcile_numbers import reconcile_numbers
from app.use_cases.resolve_findings import (
    ResolutionInvalid,
    get_resolution_state,
    record_resolution,
    summarize_false_positives,
)
from app.use_cases.review_panel import run_review_panel
from app.use_cases.rule_governance import (
    SelfApprovalForbidden,
    decide_rule_change,
    list_rule_changes,
    propose_rule_change,
)
from app.use_cases.review_queue import (
    acknowledge_review,
    get_review_state,
    reaches_senior_inbox,
    submit_to_review,
    summarize_acknowledgment,
)
from app.use_cases.draft_nota import draft_nota
from app.use_cases.draft_review import (
    export_nota_markdown,
    get_action_state,
    record_paragraph_action,
)
from app.use_cases.ingest_document import ingest_document
from app.use_cases.route_request import route_request
from app.use_cases.run_pipeline import run_case_pipeline
from app.use_cases.sync_source import sync_from_source

router = APIRouter(prefix="/api")


def deps() -> Container:
    return get_container()


# --- Workflow lifecycle --------------------------------------------------------

@router.get("/consistency/taxonomy")
async def consistency_taxonomy():
    """The 8-type consistency taxonomy with configured default severities (3.4)."""
    defaults = default_severities()
    return [{"type": t, "default_severity": defaults[t]} for t in CONSISTENCY_TYPES]


@router.get("/templates")
async def list_templates(c: Container = Depends(deps)):
    """NOTA template catalogue (data-driven; add a YAML to add a structure)."""
    return [t.model_dump(mode="json") for t in c.templates.list()]


@router.get("/sop")
async def list_sops():
    """SOP catalogue with lifecycle metadata (version/owner/status/active) — 4.1."""
    return sop_catalogue()


@router.get("/rules/version")
async def rules_version():
    from app.domain.rules import load_rulebook
    return {"rulebook_version": load_rulebook().get("rulebook_version", 1)}


@router.get("/rules/changes")
async def list_changes(c: Container = Depends(deps)):
    return await list_rule_changes(c.repository)


@router.post("/rules/changes")
async def propose_change(
    summary: str = Form(...),
    detail: str = Form(""),
    user: User = Depends(require_roles(Role.REVIEWER, Role.APPROVER, Role.ADMIN)),
    c: Container = Depends(deps),
):
    """Propose a rule/threshold change (requires a second approver — 4.4)."""
    return await propose_rule_change(summary, detail, proposed_by=user.id,
                                     repository=c.repository, audit=c.audit)


@router.post("/rules/changes/{change_id}/decide")
async def decide_change(
    change_id: str,
    decision: str = Form(...),
    user: User = Depends(require_roles(Role.APPROVER, Role.ADMIN)),
    c: Container = Depends(deps),
):
    """Approve/reject a rule change — a proposer can never self-approve (4.4)."""
    try:
        return await decide_rule_change(change_id, approver=user.id, decision=decision,
                                        repository=c.repository, audit=c.audit)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except SelfApprovalForbidden as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/routing/decision-tree")
async def routing_decision_tree():
    """The routing rulebook as a reviewable decision tree (4.2)."""
    return decision_tree()


@router.get("/routing/simulate")
async def routing_simulate(request_type: str, amount_idr: float = 0,
                          business_unit: str = ""):
    """Deterministic what-if: evaluate the rules and return the fired path
    (no LLM, instant) — drives the decision-tree highlight (4.2)."""
    outcome = evaluate(RoutingRequest(case_id="simulate", request_type=request_type,
                                      amount_idr=amount_idr, business_unit=business_unit))
    return {
        "sop": outcome["sop"], "sop_id": outcome["sop_id"],
        "sop_version": outcome.get("sop_version"),
        "approval_required": outcome["approval_required"],
        "approval_level": outcome.get("approval_level"),
        "approval_suppressed": outcome.get("approval_suppressed", False),
        "risk_tier": outcome["risk_tier"].value,
        "rules_fired": outcome["rules_fired"],
        "pre_conditions": outcome.get("pre_conditions", []),
        "expected_timeline_days": outcome.get("expected_timeline_days"),
        "ambiguous": outcome.get("ambiguous", False),
        "resolver": outcome.get("resolver"),
    }


@router.get("/sop/coverage")
async def sop_coverage_report():
    """Which request categories are served by an active (approved) SOP — 4.1."""
    from typing import get_args

    from app.domain.models import SubmissionFields
    cats = [c for c in get_args(SubmissionFields.model_fields["request_category"].annotation)
            if c != "other"]
    return sop_coverage(cats)


@router.get("/workflow/stages")
async def workflow_stages():
    """The PRD 7-stage governance lifecycle: ordered stages with entry/exit
    conditions, owner role, and whether the stage exit is a human checkpoint."""
    checkpoints = {s.value for s in HUMAN_CHECKPOINTS}
    return [
        {**spec, "order": i, "checkpoint": spec["key"] in checkpoints}
        for i, spec in enumerate(STAGE_SPEC)
    ]


# --- Cases / workflow -----------------------------------------------------------

@router.post("/cases")
async def create_case(
    title: str = Form(...),
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    case = await manage_case.create_case(title, user, repository=c.repository, audit=c.audit)
    return case.model_dump(mode="json")


@router.get("/cases")
async def list_cases(
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    # Tenant isolation: a user sees only their entity's cases unless they hold
    # cross-entity oversight (BPI central office / admin) — Phase 2 FR-9.
    scope = None if user.has_role(Role.BPI_OVERSIGHT) else user.entity.value
    return [case.model_dump(mode="json") for case in await c.repository.list_all(scope)]


@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    case = await c.repository.get(case_id)
    if case is None or not user.can_access_entity(case.entity):
        raise HTTPException(404, "case not found")  # don't leak cross-tenant existence
    return case.model_dump(mode="json")


@router.post("/cases/{case_id}/advance")
async def advance_case(
    case_id: str,
    override_by: str | None = Form(None),
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    try:
        case = await manage_case.advance_case(
            case_id, user, repository=c.repository, audit=c.audit,
            override_by=override_by)
    except KeyError:
        raise HTTPException(404, "case not found") from None
    except manage_case.Forbidden as exc:
        raise HTTPException(403, str(exc)) from exc
    except BoardGateBlocked as exc:
        raise HTTPException(409, detail={"error": str(exc), "blocking": exc.items}) from exc
    except SignoffRequired as exc:
        raise HTTPException(409, str(exc)) from exc
    return case.model_dump(mode="json")


@router.post("/cases/{case_id}/documents/{doc_id}/checkout")
async def doc_checkout(
    case_id: str, doc_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    try:
        await versioning.checkout(case_id, doc_id, user=user.id,
                                  repository=c.repository, audit=c.audit)
    except DocumentImmutable as exc:
        raise HTTPException(409, str(exc)) from exc
    except DocumentLocked as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"status": "checked_out", "document_id": doc_id, "by": user.id}


@router.post("/cases/{case_id}/documents/{doc_id}/checkin")
async def doc_checkin(
    case_id: str, doc_id: str,
    content: str = Form(...),
    change_summary: str = Form(""),
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    try:
        ver = await versioning.checkin(case_id, doc_id, user=user.id, content=content,
                                       change_summary=change_summary,
                                       repository=c.repository, audit=c.audit)
    except DocumentImmutable as exc:
        raise HTTPException(409, str(exc)) from exc
    except NotLockHolder as exc:
        raise HTTPException(409, str(exc)) from exc
    return ver.model_dump(mode="json")


@router.get("/cases/{case_id}/documents/{doc_id}/versions")
async def doc_versions(case_id: str, doc_id: str, c: Container = Depends(deps)):
    return {
        "versions": await versioning.list_versions(case_id, doc_id, repository=c.repository),
        "locked_by": await versioning.current_lock(case_id, doc_id, repository=c.repository),
        "immutable": await versioning.case_immutable(case_id, repository=c.repository),
        "propagation": await versioning.propagation_status(case_id, doc_id, repository=c.repository),
    }


@router.get("/cases/{case_id}/documents/{doc_id}/diff")
async def doc_diff(case_id: str, doc_id: str, a: int, b: int,
                   c: Container = Depends(deps)):
    try:
        return {"diff": await versioning.diff_versions(case_id, doc_id, a, b,
                                                       repository=c.repository)}
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/cases/{case_id}/board-gate")
async def board_gate_status(case_id: str, c: Container = Depends(deps)):
    """Unresolved Critical items blocking advance to board preparation (3.7)."""
    items = await unresolved_critical(case_id, repository=c.repository)
    return {"blocked": bool(items), "blocking": items}


@router.post("/cases/{case_id}/risk-tier")
async def set_risk_tier(
    case_id: str,
    tier: RiskTier = Form(...),
    user: User = Depends(require_roles(Role.REVIEWER, Role.APPROVER)),
    c: Container = Depends(deps),
):
    try:
        case = await manage_case.set_risk_tier(
            case_id, tier, actor=user.id, repository=c.repository, audit=c.audit)
    except KeyError:
        raise HTTPException(404, "case not found") from None
    return case.model_dump(mode="json")


@router.get("/cases/{case_id}/documents")
async def list_documents(case_id: str, c: Container = Depends(deps)):
    return [d.model_dump(mode="json") for d in await c.repository.list_documents(case_id)]


@router.get("/cases/{case_id}/checklist")
async def cover_checklist(case_id: str, sop: str | None = None,
                         c: Container = Depends(deps)):
    """Completeness checklist derived from attached docs; required-collateral set
    varies by SOP (resolved from the case's routing decision, or `?sop=` override)."""
    report = await build_cover_checklist(case_id, repository=c.repository, sop=sop)
    return report.model_dump(mode="json")


_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "txt": "text/plain; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/documents/{doc_id}/file")
async def document_file(
    doc_id: str,
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    """Stream a document's original file for in-browser preview/download."""
    doc = await c.repository.get_document(doc_id)
    if doc is None or not user.can_access_entity(doc.entity):
        raise HTTPException(404, "document not found")
    if not doc.storage_key:
        raise HTTPException(404, "no original file stored for this document")
    try:
        data = c.storage.get(doc.storage_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(404, "file not found in object storage") from exc
    ext = (doc.title.rsplit(".", 1)[-1] if "." in doc.title else "").lower()
    media = _MEDIA_TYPES.get(ext, "application/octet-stream")
    # inline so PDFs render in the browser viewer rather than downloading
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'inline; filename="{doc.title}"',
    })


@router.delete("/cases/{case_id}/documents/{doc_id}")
async def delete_document(
    case_id: str,
    doc_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    """Remove a supplementary document. Master (SOE) submissions are locked."""
    try:
        await manage_document.remove_document(
            case_id, doc_id, actor=user.id, repository=c.repository,
            vectors=c.vectors, storage=c.storage, audit=c.audit)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except manage_document.DocumentLocked as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"status": "removed", "document_id": doc_id}


@router.get("/cases/{case_id}/artefacts")
async def list_artefacts(case_id: str, kind: str | None = None,
                         c: Container = Depends(deps)):
    return await c.repository.list_artefacts(case_id, kind)


# --- Ingestion --------------------------------------------------------------------

@router.post("/documents/ingest", response_model=IngestionResult)
async def ingest(
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(...),
    case_id: str | None = Form(None),
    classification: DataClassification = Form(DataClassification.INTERNAL),
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    data = await file.read()
    return await ingest_document(
        file.filename or "upload", data, doc_type, case_id,
        embedder=c.embedder, vectors=c.vectors, storage=c.storage,
        repository=c.repository, audit=c.audit, parser=c.parser,
        entity=user.entity, classification=classification,
    )


@router.get("/sources/items")
async def source_items(
    folder: str | None = None,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    """List documents available in the connected OneDrive/SharePoint library."""
    if c.doc_source is None:
        raise HTTPException(503, "no document source configured")
    return [it.model_dump() for it in await c.doc_source.list_items(folder)]


@router.post("/sources/sync")
async def source_sync(
    folder: str | None = Form(None),
    doc_type: DocumentType = Form(...),
    case_id: str | None = Form(None),
    classification: DataClassification = Form(DataClassification.INTERNAL),
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    """Pull documents from OneDrive/SharePoint into the governed pipeline."""
    if c.doc_source is None:
        raise HTTPException(503, "no document source configured")
    return await sync_from_source(
        source=c.doc_source, folder=folder, doc_type=doc_type, case_id=case_id,
        entity=user.entity, classification=classification,
        embedder=c.embedder, vectors=c.vectors, storage=c.storage,
        repository=c.repository, audit=c.audit, parser=c.parser,
    )


# --- Agents -------------------------------------------------------------------------

@router.post("/agents/draft", response_model=NotaDraft)
async def agent_draft(
    request: DraftRequest,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    return await draft_nota(request, router=c.router, embedder=c.embedder,
                            vectors=c.vectors, repository=c.repository, audit=c.audit,
                            reranker=c.reranker, templates=c.templates)


@router.post("/cases/{case_id}/draft/actions")
async def record_draft_action(
    case_id: str,
    paragraph_id: str = Form(...),
    action: str = Form(...),
    final_content: str = Form(""),
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    """Record a paragraph-level accept / edit / reject (tracked + audited)."""
    if action not in ("accept", "edit", "reject"):
        raise HTTPException(422, "action must be accept | edit | reject")
    rec = ParagraphAction(case_id=case_id, paragraph_id=paragraph_id, action=action,
                          final_content=final_content, actor=user.id)
    await record_paragraph_action(rec, repository=c.repository, audit=c.audit)
    return rec.model_dump(mode="json")


@router.get("/cases/{case_id}/draft/actions")
async def draft_action_state(case_id: str, c: Container = Depends(deps)):
    return await get_action_state(case_id, repository=c.repository)


@router.get("/cases/{case_id}/draft/export")
async def export_draft(case_id: str, c: Container = Depends(deps)):
    """Reviewed NOTA as Markdown, with the persistent AI disclaimer (A4)."""
    try:
        md = await export_nota_markdown(case_id, repository=c.repository)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(content=md, media_type="text/markdown; charset=utf-8", headers={
        "Content-Disposition": f'inline; filename="nota-{case_id}.md"',
    })


@router.post("/cases/{case_id}/submit-review")
async def submit_review(
    case_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    """Submit to the senior review queue: auto-runs consistency, awaits ack."""
    return await submit_to_review(
        case_id, actor=user.id, router=c.router, embedder=c.embedder,
        vectors=c.vectors, repository=c.repository, audit=c.audit, reranker=c.reranker)


@router.post("/cases/{case_id}/review/acknowledge")
async def acknowledge_review_route(
    case_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    try:
        return await acknowledge_review(case_id, actor=user.id,
                                        repository=c.repository, audit=c.audit)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/cases/{case_id}/review-state")
async def review_state(case_id: str, c: Container = Depends(deps)):
    return await get_review_state(case_id, repository=c.repository) or {}


@router.get("/review-queue")
async def senior_review_queue(
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    """Files that have reached the senior inbox (submitted + acknowledged)."""
    scope = None if user.has_role(Role.BPI_OVERSIGHT) else user.entity.value
    out = []
    for case in await c.repository.list_all(scope):
        state = await get_review_state(case.case_id, repository=c.repository)
        if reaches_senior_inbox(state):
            out.append({**case.model_dump(mode="json"),
                        "review": {"critical_count": state.get("critical_count"),
                                   "findings_count": state.get("findings_count"),
                                   "ack_by": state.get("ack_by")}})
    return out


@router.get("/metrics/acknowledgment")
async def acknowledgment_metrics(
    limit: int = 5000,
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    return summarize_acknowledgment(c.audit.read(limit))


@router.post("/agents/consistency/{case_id}", response_model=ConsistencyReport)
async def agent_consistency(
    case_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    return await check_consistency(case_id, router=c.router, embedder=c.embedder,
                                   vectors=c.vectors, repository=c.repository,
                                   audit=c.audit, reranker=c.reranker)


@router.post("/agents/review-panel/{case_id}", response_model=PanelReview)
async def agent_review_panel(
    case_id: str,
    user: User = Depends(require_roles(Role.REVIEWER, Role.APPROVER)),
    c: Container = Depends(deps),
):
    """Multi-agent specialist review panel → cited findings + chair adjudication."""
    try:
        return await run_review_panel(case_id, router=c.router, embedder=c.embedder,
                                      vectors=c.vectors, repository=c.repository,
                                      audit=c.audit, reranker=c.reranker)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/agents/reconcile/{case_id}", response_model=ReconciliationReport)
async def agent_reconcile(
    case_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    """Deterministic financial/statistical reconciliation of the case's figures."""
    return await reconcile_numbers(case_id, router=c.router, embedder=c.embedder,
                                   vectors=c.vectors, repository=c.repository,
                                   audit=c.audit, reranker=c.reranker)


@router.post("/cases/{case_id}/findings/{fid}/resolution")
async def resolve_finding(
    case_id: str,
    fid: str,
    status: str = Form(...),
    justification: str = Form(""),
    kind: str = Form(""),
    user: User = Depends(require_roles(Role.REVIEWER, Role.APPROVER)),
    c: Container = Depends(deps),
):
    """Record a finding resolution (resolved / accepted_as_is / deferred / incorrect_flag)."""
    if status not in ("resolved", "accepted_as_is", "deferred", "incorrect_flag"):
        raise HTTPException(422, "invalid status")
    res = FindingResolution(case_id=case_id, finding_id=fid, kind=kind,
                            status=status, justification=justification, actor=user.id)
    try:
        await record_resolution(res, repository=c.repository, audit=c.audit)
    except ResolutionInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    return res.model_dump(mode="json")


@router.get("/cases/{case_id}/findings/resolutions")
async def finding_resolutions(case_id: str, c: Container = Depends(deps)):
    return await get_resolution_state(case_id, repository=c.repository)


@router.get("/metrics/false-positives")
async def false_positive_metrics(
    limit: int = 5000,
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    """Weekly false-positive aggregation from the audit trail (AC-2.6)."""
    return summarize_false_positives(c.audit.read(limit))


@router.post("/agents/route", response_model=RoutingDecision)
async def agent_route(
    request: RoutingRequest,
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    return await route_request(request, router=c.router, repository=c.repository,
                               audit=c.audit)


@router.post("/agents/pipeline/{case_id}")
async def agent_pipeline(
    case_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    try:
        return await run_case_pipeline(
            case_id, user, router=c.router, embedder=c.embedder, vectors=c.vectors,
            repository=c.repository, audit=c.audit, reranker=c.reranker,
            templates=c.templates)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


# --- Audit / explainability -----------------------------------------------------------

@router.get("/metrics/latency")
async def latency_metrics(
    limit: int = 5000,
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    """Per-operation latency (p50/p95/max) + SLA breach rate from the audit trail."""
    return summarize_latency(c.audit.read(limit))


@router.get("/audit")
async def audit_log(
    limit: int = 200,
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    return c.audit.read(limit)


@router.get("/cases/{case_id}/trace")
async def case_trace(
    case_id: str,
    user: User = Depends(require_roles(Role.AUDITOR, Role.REVIEWER, Role.APPROVER)),
    c: Container = Depends(deps),
):
    """Full decision provenance for a case, reconstructed from the audit trail."""
    return [r for r in c.audit.read(5000) if r.get("case_id") == case_id]
