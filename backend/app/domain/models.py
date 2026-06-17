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
    # PRD 7-stage governance lifecycle (FR-6) + terminal CLOSED.
    SUBMISSION_INTAKE = "submission_intake"
    ELIGIBILITY_CHECK = "eligibility_check"
    NOTA_DRAFTING = "nota_drafting"
    INTERNAL_REVIEW = "internal_review"
    BOARD_PREPARATION = "board_preparation"
    DECISION = "decision"
    COMMUNICATION_DISPATCH = "communication_dispatch"
    CLOSED = "closed"


class RiskTier(str, Enum):
    LOW = "low"          # fully automated — human removed from the loop
    MEDIUM = "medium"    # automated with human sign-off checkpoint
    HIGH = "high"        # human-in-the-loop at every stage


STAGE_ORDER = [
    WorkflowStage.SUBMISSION_INTAKE,
    WorkflowStage.ELIGIBILITY_CHECK,
    WorkflowStage.NOTA_DRAFTING,
    WorkflowStage.INTERNAL_REVIEW,
    WorkflowStage.BOARD_PREPARATION,
    WorkflowStage.DECISION,
    WorkflowStage.COMMUNICATION_DISPATCH,
    WorkflowStage.CLOSED,
]

# Stages whose EXIT needs an explicit human sign-off for non-low-risk cases.
HUMAN_CHECKPOINTS = {
    WorkflowStage.INTERNAL_REVIEW,
    WorkflowStage.BOARD_PREPARATION,
    WorkflowStage.DECISION,
}

# Entry/exit conditions + owner per stage (FR-6). Surfaced via /api/workflow/stages
# and rendered in the UI; the descriptive contract for each lifecycle step.
STAGE_SPEC = [
    {"key": "submission_intake", "label": "Submission Intake", "owner": "drafter",
     "entry": "SOE submits the request package to DAM",
     "exit": "Mandatory documents present (cover sheet + request letter)"},
    {"key": "eligibility_check", "label": "Eligibility Check", "owner": "rule_engine",
     "entry": "Intake package received",
     "exit": "SOP routed; risk tier and approval level determined"},
    {"key": "nota_drafting", "label": "NOTA Drafting", "owner": "drafter",
     "entry": "Routing decided",
     "exit": "Descriptive sections drafted and 100% source-grounded"},
    {"key": "internal_review", "label": "Internal Review", "owner": "reviewer",
     "entry": "Draft ready",
     "exit": "Cross-document consistency clean; reviewer sign-off"},
    {"key": "board_preparation", "label": "Board Preparation", "owner": "reviewer",
     "entry": "Internal review passed",
     "exit": "No unresolved Critical items; committee pack assembled"},
    {"key": "decision", "label": "Decision", "owner": "approver",
     "entry": "Committee pack ready",
     "exit": "Approval recorded at required level (CEO / Dewan Pengawas / President)"},
    {"key": "communication_dispatch", "label": "Communication Dispatch", "owner": "drafter",
     "entry": "Decision recorded",
     "exit": "Decision communicated to the SOE; artefacts archived"},
    {"key": "closed", "label": "Closed", "owner": "—",
     "entry": "Communication dispatched", "exit": "—"},
]

# Migration: map legacy 6-stage values onto the PRD 7-stage lifecycle so
# pre-existing case rows load cleanly.
LEGACY_STAGE_MAP = {
    "submission": "submission_intake",
    "evaluation": "internal_review",
    "board": "board_preparation",
    "decision": "decision",
    "communication": "communication_dispatch",
    "closed": "closed",
}


def coerce_stage(value: str) -> str:
    """Translate a possibly-legacy stage string to the current vocabulary."""
    return LEGACY_STAGE_MAP.get(value, value)


class SignoffRequired(Exception):
    """Raised when a stage transition needs a human approver."""


class BoardGateBlocked(Exception):
    """Advance to board preparation blocked by unresolved Critical items (3.7)."""

    def __init__(self, items: list[dict]):
        self.items = items
        super().__init__(f"{len(items)} unresolved Critical item(s) block board preparation")


class MergeGateBlocked(Exception):
    """Advance to board prep blocked: parallel workstreams not all complete (4.7)."""

    def __init__(self, pending: list[str]):
        self.pending = pending
        super().__init__(f"parallel workstream(s) not complete: {', '.join(pending)}")


# Parallel workstreams that must merge before board preparation (4.7, FR-6).
REQUIRED_WORKSTREAMS = ("drafting", "routing_verification")

# Per-stage SLA in business days; a case past this in a stage alerts its
# supervisor (bottleneck alerting, 4.7). None = no SLA.
STAGE_SLA_DAYS = {
    "submission_intake": 2, "eligibility_check": 1, "nota_drafting": 3,
    "internal_review": 3, "board_preparation": 5, "decision": 7,
    "communication_dispatch": 2, "closed": None,
}


class CaseEvent(BaseModel):
    stage: str
    note: str
    actor: str
    at: datetime = Field(default_factory=utcnow)


class Notification(BaseModel):
    """A task/alert for a human (4.7) — assignment, deadline, or SLA breach."""
    id: str
    to: str                          # user id or role queue (e.g. "supervisor")
    kind: str                        # assignment | sla_breach
    case_id: str
    title: str
    body: str = ""
    deadline: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    read: bool = False


class Case(BaseModel):
    case_id: str
    title: str
    entity: BPIEntity = DEFAULT_ENTITY   # tenant scope (Phase 2 FR-9 seam)
    stage: WorkflowStage = WorkflowStage.SUBMISSION_INTAKE
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
    COVER_SHEET = "cover_sheet"        # standardized NOTA cover sheet (master)
    SUPPORTING = "supporting"          # analyst-attached supplementary material (non-master)
    REVIEW_NOTE = "review_note"
    BOARD_NOTE = "board_note"
    DECISION_DOC = "decision_doc"
    COMMUNICATION = "communication"
    SOP = "sop"
    TEMPLATE = "template"
    HISTORICAL_NOTA = "historical_nota"


class ParsedDocument(BaseModel):
    """Output of the document-understanding pipeline (Sprint 2.10)."""
    text: str
    method: str               # native | docling | tesseract | empty
    char_count: int
    ocr_used: bool = False


# --- Document version control (Sprint 3.8, FR-3) ---------------------------------

class DocumentVersion(BaseModel):
    document_id: str
    version: int
    content: str
    author: str
    change_summary: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class DocumentLocked(Exception):
    """Document is checked out by another user."""


class DocumentImmutable(Exception):
    """Document is frozen — its case was submitted to the review queue (FR-3)."""


class NotLockHolder(Exception):
    """Check-in attempted without holding the checkout lock."""


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
    authored_by: Literal["ai", "human"] | None = None   # provenance (3.3 contamination gate)


# Persistent AI-mistake disclaimer (addendum A4) — attached to every AI artifact
# in-app and on export, and audited.
AI_DISCLAIMER = (
    "Konten deskriptif ini dibantu AI dan wajib bersumber pada dokumen yang "
    "dikutip; analisis, pertimbangan, dan rekomendasi adalah penilaian manusia. "
    "AI dapat keliru — verifikasi terhadap sumber sebelum sign-off. / "
    "This descriptive content is AI-assisted and grounded in the cited sources; "
    "analysis and recommendations are human judgment. AI can make mistakes — "
    "verify against sources before sign-off."
)


# --- NOTA templates (Sprint 3.1, addendum A3/A5) ---------------------------------

class TemplateSection(BaseModel):
    heading: str
    kind: Literal["descriptive", "judgment"]
    mandatory: bool = True


class NotaTemplate(BaseModel):
    """A NOTA structure as data: section list + which are mandatory. Adding a
    template (YAML) introduces a new structure with zero code change."""
    id: str
    name: str
    applies_to: list[str] = ["*"]      # SOP ids this template serves, or "*"
    sections: list[TemplateSection]

    @property
    def descriptive(self) -> list[TemplateSection]:
        return [s for s in self.sections if s.kind == "descriptive"]

    @property
    def judgment(self) -> list[TemplateSection]:
        return [s for s in self.sections if s.kind == "judgment"]


class NotaDraft(BaseModel):
    case_id: str
    title: str
    sections: list[NotaSection]
    model: str
    generated_at: datetime = Field(default_factory=utcnow)
    trace_id: str
    latency_ms: int | None = None      # wall-clock draft time (SLA, FR-6/2.8)
    coverage: float | None = None      # share of descriptive sections grounded (2.6)
    source_sufficient: bool | None = None          # coverage >= target & none suppressed
    insufficient_sections: list[str] = []          # sections sources couldn't support
    template_id: str | None = None                 # template used (3.1)
    mandatory_missing: list[str] = []              # mandatory sections not satisfied (A3)
    complete: bool = True                          # no mandatory section unfilled/invented
    disclaimer: str = AI_DISCLAIMER                # persistent AI-mistake disclaimer (A4)
    contamination_incidents: list[str] = []        # judgment sections AI tried to fill (3.3)


# --- Paragraph-level review actions (Sprint 3.2, FR-1 AC-1.5) ---------------------

class ParagraphAction(BaseModel):
    """A discrete, tracked reviewer action on one drafted paragraph/section."""
    case_id: str
    paragraph_id: str                              # stable id — the section heading
    action: Literal["accept", "edit", "reject"]
    final_content: str = ""                        # edited text (edit); else echoes original
    actor: str = ""
    at: datetime = Field(default_factory=utcnow)


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
        "asset_writeoff", "rights_issue", "ipo", "spin_off",
        "dissolution", "other",
    ] = "other"
    amount_idr: float | None
    counterparty: str | None
    summary: str
    key_dates: list[str]


# --- Consistency ------------------------------------------------------------------

class ConsistencyFinding(BaseModel):
    id: str = ""               # stable content hash — resolution anchor (3.5)
    # PRD 8-type taxonomy + Critical/Warning/Informational severities (3.4).
    severity: Literal["critical", "warning", "informational"]
    kind: Literal[
        "numeric_mismatch", "date_mismatch", "entity_name_mismatch",
        "stale_version_reference", "missing_propagated_update",
        "contradictory_recommendation", "scope_deviation",
        "structural_omission", "formatting_inconsistency",
    ]
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


def finding_id(case_id: str, f: ConsistencyFinding) -> str:
    """Stable id from finding content — survives re-runs so resolutions stick."""
    import hashlib
    key = f"{case_id}|{f.kind}|{f.document_a}|{f.excerpt_a}|{f.document_b}|{f.excerpt_b}"
    return "fnd_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


class FindingResolution(BaseModel):
    """A reviewer's decision on a flagged consistency item (Sprint 3.5)."""
    case_id: str
    finding_id: str
    kind: str = ""                  # finding type — for false-positive aggregation
    status: Literal["resolved", "accepted_as_is", "deferred", "incorrect_flag"]
    justification: str = ""
    actor: str = ""
    at: datetime = Field(default_factory=utcnow)


# --- Financial & statistical reconciliation (FR-2a, addendum A1, Sprint 3.11) -----
# The LLM EXTRACTS numeric claims and the arithmetic relationship asserted in the
# documents; a deterministic calculator RECOMPUTES the result — the model never
# does the math.

RelationshipType = Literal[
    "percentage_change",   # (operands[0]-operands[1]) / operands[1] * 100
    "percentage_of",       # operands[0] / operands[1] * 100
    "difference",          # operands[0] - operands[1]
    "sum",                 # sum(operands)
    "ratio",               # operands[0] / operands[1]
    "product",             # operands[0] * operands[1]
]


class NumericClaim(BaseModel):
    """A figure in the documents that asserts an arithmetic relationship."""
    description: str
    relationship: RelationshipType
    operands: list[float]          # the SOURCE numbers, in formula order
    claimed_result: float          # the result as STATED in the document
    unit: str | None = None        # "%", "IDR", "x", …
    source_refs: list[str] = []


class ClaimList(BaseModel):
    claims: list[NumericClaim]


class ReconciliationFinding(BaseModel):
    description: str
    relationship: str
    operands: list[float]
    claimed_result: float
    recomputed_result: float | None
    status: Literal["ok", "mismatch", "uncomputable"]
    severity: Literal["critical", "major", "minor", "info"]
    source_refs: list[str] = []
    explanation: str


class ReconciliationReport(BaseModel):
    case_id: str
    findings: list[ReconciliationFinding]
    claims_checked: int
    mismatches: int
    trace_id: str
    latency_ms: int | None = None
    generated_at: datetime = Field(default_factory=utcnow)


# --- NOTA Review Panel (Sprint 3.10, FR-2 deepens / FR-10 seed) -------------------

class PanelFinding(BaseModel):
    reviewer_id: str
    reviewer_title: str = ""
    dimension: str                          # rubric dimension id (DIM-*)
    severity: Literal["critical", "major", "minor"]
    title: str
    detail: str
    citation: str = ""                      # resolvable source ref or fired rule id
    grounded: bool = True                    # passed the citation gate (RVW-003)


class ReviewerReport(BaseModel):
    reviewer_id: str
    title: str
    findings: list[PanelFinding] = []
    confidence: float = 0.0                  # reviewer self-confidence 0..1


class DimensionScore(BaseModel):
    dimension: str
    severity: Literal["critical", "major", "minor", "ok"]
    status: str = ""


class ChairReport(BaseModel):
    recommendation: Literal["endorse", "endorse_with_conditions", "return_for_revision"]
    confidence: float = 0.0
    summary: str = ""
    dimension_scores: list[DimensionScore] = []
    unresolved_issues: list[str] = []        # addendum A6 — needs-human block
    needs_human_review: bool = True


class PanelReview(BaseModel):
    case_id: str
    risk_tier: str
    reviewers: list[ReviewerReport] = []
    findings: list[PanelFinding] = []        # grounded, deduped
    dropped_uncited: int = 0                  # findings dropped by the citation gate
    chair: ChairReport
    trace_id: str
    latency_ms: int | None = None
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
    sop_version: int | None = None      # SOP lifecycle version recorded per decision (4.1/4.4)
    rulebook_version: int | None = None  # rulebook version applied — legal defensibility (4.4)
    approval_required: bool
    approval_level: str | None = None
    risk_tier: RiskTier
    rules_fired: list[str]      # deterministic rule ids — the legal defensibility record
    explanation: str            # plain-language rationale (LLM-generated, rule-grounded)
    trace_id: str
    # Routing output completion (4.3, FR-4) — the four-part contract + ambiguity:
    pre_conditions: list[str] = []
    expected_timeline_days: int | None = None
    approval_suppressed: bool = False    # unnecessary approval flagged + suppressed
    ambiguous: bool = False              # no specific SOP / missing amount → human resolver
    resolver: str | None = None
