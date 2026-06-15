"""Composition root — the only place adapters are constructed and bound to
ports. Everything inward of here depends on interfaces alone."""
import os
from dataclasses import dataclass
from functools import lru_cache

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.embedder_hash import HashEmbedder
from app.adapters.llm_claude import ClaudeGateway
from app.adapters.repo_memory import InMemoryCaseRepository
from app.adapters.repo_postgres import PostgresCaseRepository
from app.adapters.storage_local import LocalStorage
from app.adapters.vector_pgvector import InMemoryVectorStore, PgVectorStore
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    DocumentSource,
    Embedder,
    LLMGateway,
    ObjectStorage,
    VectorStore,
)
from app.infrastructure.config import Settings, get_settings


@dataclass
class Container:
    settings: Settings
    llm: LLMGateway
    embedder: Embedder
    vectors: VectorStore
    repository: CaseRepository
    storage: ObjectStorage
    audit: AuditLog
    doc_source: DocumentSource | None = None

    async def init(self) -> None:
        await self.repository.init()
        await self.vectors.init()


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    # Domain rule engine reads this env var (framework-free config path).
    os.environ.setdefault("SOP_CONFIG_DIR", settings.sop_config_dir)

    embedder = HashEmbedder()

    if settings.repo_backend == "postgres":
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(settings.database_url)
        repository: CaseRepository = PostgresCaseRepository(engine)
        vectors: VectorStore = PgVectorStore(engine, dim=embedder.dim)
    else:
        repository = InMemoryCaseRepository()
        vectors = InMemoryVectorStore()

    if settings.storage_backend == "minio":
        from app.adapters.storage_minio import MinioStorage

        storage: ObjectStorage = MinioStorage(
            settings.minio_endpoint,
            settings.minio_access_key,
            settings.minio_secret_key,
            settings.minio_bucket,
        )
    else:
        storage = LocalStorage(settings.local_storage_path)

    doc_source: DocumentSource | None = None
    if settings.doc_source == "graph":
        from app.adapters.source_graph import GraphDocumentSource

        doc_source = GraphDocumentSource(
            tenant_id=settings.m365_tenant_id,
            client_id=settings.m365_client_id,
            client_secret=settings.m365_client_secret,
            drive_id=settings.m365_drive_id,
        )
    elif settings.doc_source == "local":
        from app.adapters.source_local import LocalFolderSource

        doc_source = LocalFolderSource(settings.local_source_path)

    return Container(
        settings=settings,
        llm=ClaudeGateway(settings.anthropic_api_key, settings.dam_model),
        embedder=embedder,
        vectors=vectors,
        repository=repository,
        storage=storage,
        audit=JsonlAuditLog(settings.dam_audit_log_path),
        doc_source=doc_source,
    )


@lru_cache
def get_container() -> Container:
    return build_container()
