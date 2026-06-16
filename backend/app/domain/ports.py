"""Ports — the only doorway between the domain/use-case core and the world.

Every external dependency (model API, database, object storage, audit sink)
enters through one of these interfaces. Adapters implement them; use cases
depend on them; nothing inside the core imports a framework.
"""
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.domain.models import Case, Chunk, GovernanceDocument

T = TypeVar("T", bound=BaseModel)


class LLMGateway(ABC):
    """Single audited entry point to the language model (secure AI sandbox)."""

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    async def parse(self, *, system: str, prompt: str, output_type: type[T],
                    max_tokens: int = 8192) -> T:
        """Structured-output completion validated against `output_type`."""

    @abstractmethod
    async def complete(self, *, system: str, prompt: str, max_tokens: int = 2048) -> str:
        """Plain-text completion."""


class ModelRouter(ABC):
    """Selects the right model per task role (drafting, extraction, reasoning,
    multimodal_edge) from the model registry, and returns a role-bound
    `LLMGateway`. Use cases ask for a role; the router applies the cost-tiered
    mix and routing policies (config/models.yaml). The returned gateway's
    `.model` reflects the resolved model, so audit logging is unchanged."""

    @abstractmethod
    def gateway(self, role: str) -> "LLMGateway":
        """Return an LLMGateway bound to the model resolved for `role`."""


class Embedder(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]: ...


class VectorStore(ABC):
    @abstractmethod
    async def init(self) -> None: ...

    @abstractmethod
    async def replace_document(self, chunks: list[Chunk],
                               embeddings: list[list[float]]) -> int: ...

    @abstractmethod
    async def search(self, embedding: list[float], k: int = 8,
                     case_id: str | None = None,
                     doc_types: list[str] | None = None,
                     entity: str | None = None) -> list[Chunk]:
        """Dense similarity search, optionally scoped to a case, doc types, or
        BPI entity (tenant isolation for cross-case precedent retrieval)."""

    @abstractmethod
    async def keyword_search(self, query: str, k: int = 8,
                             case_id: str | None = None,
                             doc_types: list[str] | None = None,
                             entity: str | None = None) -> list[Chunk]:
        """Lexical/full-text search — the sparse half of hybrid retrieval."""


class Reranker(ABC):
    """Reorders candidate chunks by relevance to the query (the rerank stage
    after hybrid fusion). Cross-encoder or LLM in production; lexical default."""

    @abstractmethod
    async def rerank(self, query: str, chunks: list[Chunk], k: int = 8) -> list[Chunk]: ...


class AuditLog(ABC):
    """Append-only audit trail — the explainability and liability record."""

    @abstractmethod
    def log(self, event: str, trace_id: str, payload: dict) -> None: ...

    @abstractmethod
    def read(self, limit: int = 200) -> list[dict]: ...


class CaseRepository(ABC):
    @abstractmethod
    async def init(self) -> None: ...

    @abstractmethod
    async def get(self, case_id: str) -> Case | None: ...

    @abstractmethod
    async def save(self, case: Case) -> None: ...

    @abstractmethod
    async def list_all(self, entity: str | None = None) -> list[Case]:
        """List cases, optionally scoped to one BPI entity (tenant isolation)."""

    @abstractmethod
    async def save_document(self, document: GovernanceDocument) -> None: ...

    @abstractmethod
    async def list_documents(self, case_id: str) -> list[GovernanceDocument]: ...

    @abstractmethod
    async def save_artefact(self, case_id: str, kind: str, payload: dict) -> None: ...

    @abstractmethod
    async def list_artefacts(self, case_id: str, kind: str | None = None) -> list[dict]: ...


class ObjectStorage(ABC):
    """Original-file store (MinIO in production)."""

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...


class SourceItem(BaseModel):
    """A document discovered in an external repository (OneDrive/SharePoint)."""
    external_id: str
    name: str
    path: str
    modified: str | None = None
    size_bytes: int | None = None


class DocumentSource(ABC):
    """External document repository the platform ingests from.

    DAM stores governance documents in Microsoft 365 (OneDrive today, with a
    SharePoint document library as the governed target — both are Microsoft
    Graph drives). This port lets the platform pull submissions and SOPs from
    those libraries instead of relying only on manual upload, and is the path
    for the PRD's OneDrive-migration touchpoint (§10.2) and the
    'system as the only authorized intake channel' control (Risk R6).
    """

    @abstractmethod
    async def list_items(self, folder: str | None = None) -> list[SourceItem]: ...

    @abstractmethod
    async def fetch(self, external_id: str) -> tuple[bytes, SourceItem]:
        """Download one item's bytes plus its metadata."""
