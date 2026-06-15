"""Thin HTTP controllers — translate requests to use-case calls, nothing more."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.domain.models import (
    ConsistencyReport,
    DataClassification,
    DocumentType,
    DraftRequest,
    IngestionResult,
    NotaDraft,
    RiskTier,
    Role,
    RoutingDecision,
    RoutingRequest,
    SignoffRequired,
    User,
)
from app.infrastructure.container import Container, get_container
from app.infrastructure.security import get_current_user, require_roles
from app.use_cases import manage_case
from app.use_cases.check_consistency import check_consistency
from app.use_cases.draft_nota import draft_nota
from app.use_cases.ingest_document import ingest_document
from app.use_cases.route_request import route_request
from app.use_cases.run_pipeline import run_case_pipeline
from app.use_cases.sync_source import sync_from_source

router = APIRouter(prefix="/api")


def deps() -> Container:
    return get_container()


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
        repository=c.repository, audit=c.audit,
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
        repository=c.repository, audit=c.audit,
    )


# --- Agents -------------------------------------------------------------------------

@router.post("/agents/draft", response_model=NotaDraft)
async def agent_draft(
    request: DraftRequest,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    return await draft_nota(request, router=c.router, embedder=c.embedder,
                            vectors=c.vectors, repository=c.repository, audit=c.audit)


@router.post("/agents/consistency/{case_id}", response_model=ConsistencyReport)
async def agent_consistency(
    case_id: str,
    user: User = Depends(require_roles(Role.DRAFTER, Role.REVIEWER)),
    c: Container = Depends(deps),
):
    return await check_consistency(case_id, router=c.router, embedder=c.embedder,
                                   vectors=c.vectors, repository=c.repository,
                                   audit=c.audit)


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
            repository=c.repository, audit=c.audit)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


# --- Audit / explainability -----------------------------------------------------------

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
