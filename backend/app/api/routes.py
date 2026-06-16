"""Thin HTTP controllers — translate requests to use-case calls, nothing more."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.domain.models import (
    HUMAN_CHECKPOINTS,
    STAGE_SPEC,
    ConsistencyReport,
    DataClassification,
    DocumentType,
    DraftRequest,
    IngestionResult,
    FindingResolution,
    NotaDraft,
    ParagraphAction,
    ReconciliationReport,
    RiskTier,
    Role,
    RoutingDecision,
    RoutingRequest,
    SignoffRequired,
    User,
)
from app.domain.taxonomy import CONSISTENCY_TYPES, default_severities
from app.infrastructure.container import Container, get_container
from app.infrastructure.security import get_current_user, require_roles
from app.use_cases import manage_case, manage_document
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
    user: User = Depends(get_current_user),
    c: Container = Depends(deps),
):
    try:
        case = await manage_case.advance_case(
            case_id, user, repository=c.repository, audit=c.audit)
    except KeyError:
        raise HTTPException(404, "case not found") from None
    except manage_case.Forbidden as exc:
        raise HTTPException(403, str(exc)) from exc
    except SignoffRequired as exc:
        raise HTTPException(409, str(exc)) from exc
    return case.model_dump(mode="json")


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


@router.post("/agents/consistency/{case_id}", response_model=ConsistencyReport)
async def agent_consistency(
    case_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    return await check_consistency(case_id, router=c.router, embedder=c.embedder,
                                   vectors=c.vectors, repository=c.repository,
                                   audit=c.audit, reranker=c.reranker)


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
