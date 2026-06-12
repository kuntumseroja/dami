"""Domain schemas for the DAM governance platform.

The document hierarchy implements the "single source of truth" requirement:
a Submission is the master record; NOTA review notes, board notes, decision
documents, and communications are derived artefacts whose facts must stay
consistent with it.
"""
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# --- Workflow ----------------------------------------------------------------

class WorkflowStage(str, Enum):
    SUBMISSION = "submission"
    EVALUATION = "evaluation"
    BOARD = "board"
    DECISION = "decision"
    COMMUNICATION = "communication"
    CLOSED = "closed"


class RiskTier(str, Enum):
    LOW = "low"          # fully automated — human removed from the loop
    MEDIUM = "medium"    # automated with human sign-off checkpoint
    HIGH = "high"        # human-in-the-loop at every stage


class DocumentType(str, Enum):
    SUBMISSION = "submission"
    REVIEW_NOTE = "review_note"
    BOARD_NOTE = "board_note"
    DECISION_DOC = "decision_doc"
    COMMUNICATION = "communication"
    SOP = "sop"
    TEMPLATE = "template"
    HISTORICAL_NOTA = "historical_nota"


# --- Documents ---------------------------------------------------------------

class GovernanceDocument(BaseModel):
    id: str
    case_id: str | None = None
    doc_type: DocumentType
    title: str
    version: int = 1
    is_master: bool = False
    parent_doc_id: str | None = None  # propagation hierarchy
    storage_key: str | None = None    # MinIO object key
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IngestionResult(BaseModel):
    document_id: str
    chunks_indexed: int
    extracted_fields: dict[str, str] = {}


# --- Drafting (NOTA) ---------------------------------------------------------

class NotaSection(BaseModel):
    heading: str
    kind: Literal["descriptive", "judgment"]
    content: str = ""           # AI fills descriptive; judgment left to humans
    sources: list[str] = []     # chunk/document ids grounding this section


class NotaDraft(BaseModel):
    case_id: str
    title: str
    sections: list[NotaSection]
    model: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str               # explainability trace reference


class DraftRequest(BaseModel):
    case_id: str
    template_id: str | None = None
    instructions: str | None = None


# --- Consistency -------------------------------------------------------------

class ConsistencyFinding(BaseModel):
    severity: Literal["critical", "major", "minor"]
    kind: Literal["inconsistency", "outdated_reference", "missing_update"]
    description: str
    document_a: str
    excerpt_a: str
    document_b: str
    excerpt_b: str
    suggested_resolution: str


class ConsistencyReport(BaseModel):
    case_id: str
    findings: list[ConsistencyFinding]
    documents_compared: list[str]
    trace_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Routing -----------------------------------------------------------------

class RoutingRequest(BaseModel):
    case_id: str
    request_type: str
    amount_idr: float | None = None
    business_unit: str | None = None
    attributes: dict[str, str] = {}


class RoutingDecision(BaseModel):
    case_id: str
    applicable_sop: str
    approval_required: bool
    approval_level: str | None = None
    risk_tier: RiskTier
    rules_fired: list[str]      # deterministic rule ids — the legal defensibility record
    explanation: str            # plain-language rationale (LLM-generated, rule-grounded)
    trace_id: str


# --- Explainability ----------------------------------------------------------

class DecisionTrace(BaseModel):
    trace_id: str
    actor: Literal["agent", "rule_engine", "human"]
    action: str
    inputs: dict
    retrieved_sources: list[str] = []
    rules_fired: list[str] = []
    model: str | None = None
    rationale: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
