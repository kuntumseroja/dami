"""Domain entities and value objects.

Framework-free: pydantic is used as a data-modeling library only. No
FastAPI, SQLAlchemy, Anthropic, or storage imports are allowed here.

The document hierarchy implements the "single source of truth" requirement:
a Submission is the master record; NOTA review notes, board notes, decision
documents, and communications are derived artefacts whose facts must stay
consistent with it.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_trace_id() -> str:
    return f"trc_{uuid.uuid4().hex[:16]}"


# --- Tenancy (Phase 2 FR-9 seam) ----------------------------------------------
# Every governed record carries a BPI entity from day one. Phase 1 runs the
# single entity DAM; Phase 2 turns the platform multi-tenant across the BPI
# ecosystem (DAM/DIM/DSI) with no schema migration — repositories already
# scope by this column and the auth context already binds it.

class BPIEntity(str, Enum):
    DAM = "DAM"   # Danantara Asset Management (Phase 1)
    DIM = "DIM"   # Danantara Investment Management (Phase 2)
    DSI = "DSI"   # Danantara Strategic Investments (Phase 2)


DEFAULT_ENTITY = BPIEntity.DAM


# --- Data classification (Phase 1 FR-5 / §11.1 seam) --------------------------
# Set at intake; gates which model tier may process a document (router policy
# RTE-002). Ordered low→high so threshold comparisons are simple.

class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"   # highest sensitivity — self-host tier only


CLASSIFICATION_ORDER = [
    DataClassification.PUBLIC,
    DataClassification.INTERNAL,
    DataClassification.CONFIDENTIAL,
    DataClassification.RESTRICTED,
]


# --- Identity ------------------------------------------------------------------

class Role(str, Enum):
    DRAFTER = "drafter"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    AUDITOR = "auditor"
    ADMIN = "admin"
    BPI_OVERSIGHT = "bpi_oversight"   # Phase 2: cross-entity read (BPI central office)


class User(BaseModel):
    id: str
    name: str
    roles: list[Role]
    entity: BPIEntity = DEFAULT_ENTITY   # tenant the user acts within

    def has_role(self, *roles: Role) -> bool:
        return Role.ADMIN in self.roles or any(r in self.roles for r in roles)

    def can_access_entity(self, entity: BPIEntity) -> bool:
        """Tenant isolation: own entity only, unless admin or BPI oversight."""
        if Role.ADMIN in self.roles or Role.BPI_OVERSIGHT in self.roles:
            return True
        return self.entity == entity


# --- Workflow ------------------------------------------------------------------

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


STAGE_ORDER = [
    WorkflowStage.SUBMISSION,
    WorkflowStage.EVALUATION,
    WorkflowStage.BOARD,
    WorkflowStage.DECISION,
    WorkflowStage.COMMUNICATION,
    WorkflowStage.CLOSED,
]

# Stages that need an explicit human sign-off for non-low-risk cases.
HUMAN_CHECKPOINTS = {WorkflowStage.EVALUATION, WorkflowStage.BOARD, WorkflowStage.DECISION}


class SignoffRequired(Exception):
    """Raised when a stage transition needs a human approver."""


class CaseEvent(BaseModel):
    stage: str
    note: str
    actor: str
    at: datetime = Field(default_factory=utcnow)


class Case(BaseModel):
    case_id: str
    title: str
    entity: BPIEntity = DEFAULT_ENTITY   # tenant scope (Phase 2 FR-9 seam)
    stage: WorkflowStage = WorkflowStage.SUBMISSION
    risk_tier: RiskTier = RiskTier.MEDIUM
    history: list[CaseEvent] = []
    created_at: datetime = Field(default_factory=utcnow)

    @property
    def requires_signoff(self) -> bool:
        return self.stage in HUMAN_CHECKPOINTS and self.risk_tier != RiskTier.LOW

    def advance(self, actor: str, signoff_by: str | None = None) -> tuple[str, str]:
        """Advance one stage; the risk-based checkpoint rule lives here."""
        if self.stage == WorkflowStage.CLOSED:
            return (self.stage.value, self.stage.value)
        if self.requires_signoff and not signoff_by:
            raise SignoffRequired(
                f"Stage '{self.stage.value}' requires human sign-off for "
                f"{self.risk_tier.value}-risk cases."
            )
        previous = self.stage
        self.stage = STAGE_ORDER[STAGE_ORDER.index(previous) + 1]
        self.history.append(
            CaseEvent(
                stage=self.stage.value,
                note=f"advanced from {previous.value}",
                actor=signoff_by or actor,
            )
        )
        return (previous.value, self.stage.value)

    def set_risk_tier(self, tier: RiskTier, actor: str = "rule_engine") -> None:
        self.risk_tier = tier
        self.history.append(
            CaseEvent(stage=self.stage.value, note=f"risk tier set to {tier.value}", actor=actor)
        )


# --- Documents -----------------------------------------------------------------

class DocumentType(str, Enum):
    SUBMISSION = "submission"
    REVIEW_NOTE = "review_note"
    BOARD_NOTE = "board_note"
    DECISION_DOC = "decision_doc"
    COMMUNICATION = "communication"
    SOP = "sop"
    TEMPLATE = "template"
    HISTORICAL_NOTA = "historical_nota"


class GovernanceDocument(BaseModel):
    id: str
    case_id: str | None = None
    entity: BPIEntity = DEFAULT_ENTITY                    # tenant scope (FR-9)
    classification: DataClassification = DataClassification.INTERNAL  # FR-5/§11.1
    doc_type: DocumentType
    title: str
    version: int = 1
    is_master: bool = False
    parent_doc_id: str | None = None  # propagation hierarchy
    storage_key: str | None = None    # object-storage key of the original file
    created_at: datetime = Field(default_factory=utcnow)


class Chunk(BaseModel):
    """Indexed fragment of a document; the unit of retrieval and grounding."""
    document_id: str
    case_id: str | None
    entity: BPIEntity = DEFAULT_ENTITY   # tenant-scoped retrieval (FR-9)
    doc_type: str
    chunk_index: int
    content: str
    score: float = 0.0

    @property
    def ref(self) -> str:
        return f"{self.document_id}#{self.chunk_index}"


class IngestionResult(BaseModel):
    document_id: str
    chunks_indexed: int
    storage_key: str | None = None


# --- Drafting (NOTA) -------------------------------------------------------------

class NotaSection(BaseModel):
    heading: str
    kind: Literal["descriptive", "judgment"]
    content: str = ""           # AI fills descriptive; judgment left to humans
    sources: list[str] = []     # chunk refs grounding this section
    grounded: bool = True       # set by the grounding gate — false = suppressed/placeholder


class NotaDraft(BaseModel):
    case_id: str
    title: str
    sections: list[NotaSection]
    model: str
    generated_at: datetime = Field(default_factory=utcnow)
    trace_id: str


class DraftRequest(BaseModel):
    case_id: str
    template_id: str | None = None
    instructions: str | None = None


class SubmissionFields(BaseModel):
    requesting_unit: str
    request_type: str                # free-text description as written in the submission
    # Canonical category for the deterministic routing rule engine. The
    # extractor classifies the request into one of these so SOP selection
    # never has to parse free text.
    request_category: Literal[
        "asset_disposal", "asset_acquisition", "investment",
        "asset_lease", "asset_utilization",
        "debt_issuance", "merger_acquisition", "capital_expenditure",
        "asset_writeoff", "other",
    ] = "other"
    amount_idr: float | None
    counterparty: str | None
    summary: str
    key_dates: list[str]


# --- Consistency ------------------------------------------------------------------

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
    generated_at: datetime = Field(default_factory=utcnow)


# --- Routing ----------------------------------------------------------------------

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
