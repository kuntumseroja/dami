"""pgvector-backed chunk store.

Documents are chunked at ingestion and stored with embeddings so agents can
ground every generated sentence in retrievable source text — the primary
hallucination control for the secure AI sandbox.
"""
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings

EMBEDDING_DIM = 1024

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url)
    return _engine


DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS doc_chunks (
    id          BIGSERIAL PRIMARY KEY,
    document_id TEXT NOT NULL,
    case_id     TEXT,
    doc_type    TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector({EMBEDDING_DIM})
);
CREATE INDEX IF NOT EXISTS doc_chunks_case_idx ON doc_chunks (case_id);
"""


@dataclass
class Chunk:
    document_id: str
    case_id: str | None
    doc_type: str
    chunk_index: int
    content: str
    score: float = 0.0

    @property
    def ref(self) -> str:
        return f"{self.document_id}#{self.chunk_index}"


async def init_store() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                await conn.execute(text(stmt))


async def upsert_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM doc_chunks WHERE document_id = :doc_id"),
            {"doc_id": chunks[0].document_id} if chunks else {"doc_id": ""},
        )
        for chunk, emb in zip(chunks, embeddings):
            await conn.execute(
                text(
                    "INSERT INTO doc_chunks "
                    "(document_id, case_id, doc_type, chunk_index, content, embedding) "
                    "VALUES (:d, :c, :t, :i, :x, :e)"
                ),
                {
                    "d": chunk.document_id,
                    "c": chunk.case_id,
                    "t": chunk.doc_type,
                    "i": chunk.chunk_index,
                    "x": chunk.content,
                    "e": str(emb),
                },
            )
    return len(chunks)


async def similarity_search(
    embedding: list[float],
    k: int = 8,
    case_id: str | None = None,
    doc_types: list[str] | None = None,
) -> list[Chunk]:
    engine = get_engine()
    where, params = ["1=1"], {"e": str(embedding), "k": k}
    if case_id:
        where.append("case_id = :case_id")
        params["case_id"] = case_id
    if doc_types:
        where.append("doc_type = ANY(:doc_types)")
        params["doc_types"] = doc_types
    sql = text(
        "SELECT document_id, case_id, doc_type, chunk_index, content, "
        "1 - (embedding <=> :e) AS score "
        f"FROM doc_chunks WHERE {' AND '.join(where)} "
        "ORDER BY embedding <=> :e LIMIT :k"
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(sql, params)).fetchall()
    return [
        Chunk(
            document_id=r.document_id,
            case_id=r.case_id,
            doc_type=r.doc_type,
            chunk_index=r.chunk_index,
            content=r.content,
            score=float(r.score),
        )
        for r in rows
    ]
