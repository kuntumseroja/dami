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
                     doc_types: list[str] | None = None) -> list[Chunk]: ...


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
    async def list_all(self) -> list[Case]: ...

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
