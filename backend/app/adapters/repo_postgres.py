"""Postgres CaseRepository — restart-safe persistence for cases, documents,
and AI artefacts (drafts, consistency reports, routing decisions)."""
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.models import Case, GovernanceDocument, utcnow
from app.domain.ports import CaseRepository

DDL = """
CREATE TABLE IF NOT EXISTS cases (
    case_id    TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    entity     TEXT NOT NULL DEFAULT 'DAM',
    stage      TEXT NOT NULL,
    risk_tier  TEXT NOT NULL,
    history    JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS cases_entity_idx ON cases (entity);
CREATE TABLE IF NOT EXISTS documents (
    id             TEXT PRIMARY KEY,
    case_id        TEXT,
    entity         TEXT NOT NULL DEFAULT 'DAM',
    classification TEXT NOT NULL DEFAULT 'internal',
    doc_type       TEXT NOT NULL,
    title          TEXT NOT NULL,
    version        INT NOT NULL DEFAULT 1,
    is_master      BOOLEAN NOT NULL DEFAULT FALSE,
    parent_doc_id  TEXT,
    storage_key    TEXT,
    created_at     TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS documents_case_idx ON documents (case_id);
CREATE INDEX IF NOT EXISTS documents_entity_idx ON documents (entity);
CREATE TABLE IF NOT EXISTS artefacts (
    id         BIGSERIAL PRIMARY KEY,
    case_id    TEXT NOT NULL,
    kind       TEXT NOT NULL,
    payload    JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS artefacts_case_idx ON artefacts (case_id, kind);
"""


class PostgresCaseRepository(CaseRepository):
    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    async def init(self) -> None:
        async with self._engine.begin() as conn:
            for stmt in DDL.strip().split(";"):
                if stmt.strip():
                    await conn.execute(text(stmt))

    async def get(self, case_id: str) -> Case | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(
                text("SELECT * FROM cases WHERE case_id = :id"), {"id": case_id}
            )).fetchone()
        return self._to_case(row) if row else None

    async def save(self, case: Case) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO cases "
                    "(case_id, title, entity, stage, risk_tier, history, created_at) "
                    "VALUES (:id, :title, :entity, :stage, :tier, :history, :created) "
                    "ON CONFLICT (case_id) DO UPDATE SET "
                    "title = :title, stage = :stage, risk_tier = :tier, history = :history"
                ),
                {
                    "id": case.case_id,
                    "title": case.title,
                    "entity": case.entity.value,
                    "stage": case.stage.value,
                    "tier": case.risk_tier.value,
                    "history": json.dumps([e.model_dump(mode="json") for e in case.history]),
                    "created": case.created_at,
                },
            )

    async def list_all(self, entity: str | None = None) -> list[Case]:
        sql = "SELECT * FROM cases"
        params: dict = {}
        if entity is not None:
            sql += " WHERE entity = :entity"
            params["entity"] = entity
        sql += " ORDER BY created_at DESC"
        async with self._engine.connect() as conn:
            rows = (await conn.execute(text(sql), params)).fetchall()
        return [self._to_case(r) for r in rows]

    async def save_document(self, document: GovernanceDocument) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO documents "
                    "(id, case_id, entity, classification, doc_type, title, version, "
                    " is_master, parent_doc_id, storage_key, created_at) "
                    "VALUES (:id, :case_id, :entity, :classification, :doc_type, :title, "
                    "        :version, :is_master, :parent, :key, :created) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "version = :version, storage_key = :key, classification = :classification"
                ),
                {
                    "id": document.id,
                    "case_id": document.case_id,
                    "entity": document.entity.value,
                    "classification": document.classification.value,
                    "doc_type": document.doc_type.value,
                    "title": document.title,
                    "version": document.version,
                    "is_master": document.is_master,
                    "parent": document.parent_doc_id,
                    "key": document.storage_key,
                    "created": document.created_at,
                },
            )

    async def list_documents(self, case_id: str) -> list[GovernanceDocument]:
        async with self._engine.connect() as conn:
            rows = (await conn.execute(
                text("SELECT * FROM documents WHERE case_id = :id ORDER BY created_at"),
                {"id": case_id},
            )).fetchall()
        return [GovernanceDocument.model_validate(dict(r._mapping)) for r in rows]

    async def get_document(self, doc_id: str) -> GovernanceDocument | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(
                text("SELECT * FROM documents WHERE id = :id"), {"id": doc_id},
            )).fetchone()
        return GovernanceDocument.model_validate(dict(row._mapping)) if row else None

    async def delete_document(self, doc_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM documents WHERE id = :id"), {"id": doc_id})

    async def save_artefact(self, case_id: str, kind: str, payload: dict) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO artefacts (case_id, kind, payload, created_at) "
                    "VALUES (:case_id, :kind, :payload, :created)"
                ),
                {
                    "case_id": case_id,
                    "kind": kind,
                    "payload": json.dumps(payload, default=str),
                    "created": utcnow(),
                },
            )

    async def list_artefacts(self, case_id: str, kind: str | None = None) -> list[dict]:
        where = "case_id = :case_id" + ("" if kind is None else " AND kind = :kind")
        params: dict = {"case_id": case_id}
        if kind is not None:
            params["kind"] = kind
        async with self._engine.connect() as conn:
            rows = (await conn.execute(
                text(f"SELECT kind, payload, created_at FROM artefacts WHERE {where} "
                     "ORDER BY created_at"),
                params,
            )).fetchall()
        return [
            {"kind": r.kind, "payload": r.payload, "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    @staticmethod
    def _to_case(row) -> Case:
        data = dict(row._mapping)
        if isinstance(data.get("history"), str):
            data["history"] = json.loads(data["history"])
        return Case.model_validate(data)
