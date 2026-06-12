from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.consistency import check_consistency
from app.agents.drafting import draft_nota
from app.agents.orchestrator import run_case_pipeline
from app.agents.routing import route_request
from app.core.audit import read_audit_log
from app.ingestion.pipeline import ingest_document
from app.models.schemas import (
    ConsistencyReport,
    DocumentType,
    DraftRequest,
    IngestionResult,
    NotaDraft,
    RiskTier,
    RoutingDecision,
    RoutingRequest,
)
from app.workflow import engine

router = APIRouter(prefix="/api")


# --- Cases / workflow ---------------------------------------------------------

@router.post("/cases")
def create_case(title: str = Form(...)):
    return engine.create_case(title)


@router.get("/cases")
def list_cases():
    return engine.list_cases()


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    case = engine.get_case(case_id)
    if case is None:
        raise HTTPException(404, "case not found")
    return case


@router.post("/cases/{case_id}/advance")
def advance_case(case_id: str, signoff_by: str | None = Form(None)):
    if engine.get_case(case_id) is None:
        raise HTTPException(404, "case not found")
    try:
        return engine.advance(case_id, signoff_by=signoff_by)
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/cases/{case_id}/risk-tier")
def set_risk_tier(case_id: str, tier: RiskTier = Form(...)):
    if engine.get_case(case_id) is None:
        raise HTTPException(404, "case not found")
    return engine.set_risk_tier(case_id, tier)


# --- Ingestion ----------------------------------------------------------------

@router.post("/documents/ingest", response_model=IngestionResult)
async def ingest(
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(...),
    case_id: str | None = Form(None),
):
    data = await file.read()
    return await ingest_document(file.filename or "upload", data, doc_type, case_id)


# --- Agents -------------------------------------------------------------------

@router.post("/agents/draft", response_model=NotaDraft)
async def agent_draft(request: DraftRequest):
    return await draft_nota(request)


@router.post("/agents/consistency/{case_id}", response_model=ConsistencyReport)
async def agent_consistency(case_id: str):
    return await check_consistency(case_id)


@router.post("/agents/route", response_model=RoutingDecision)
async def agent_route(request: RoutingRequest):
    return await route_request(request)


@router.post("/agents/pipeline/{case_id}")
async def agent_pipeline(case_id: str):
    try:
        return await run_case_pipeline(case_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


# --- Audit / explainability ----------------------------------------------------

@router.get("/audit")
def audit(limit: int = 200):
    return read_audit_log(limit)
