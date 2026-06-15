"""VectorStore adapter backed by Postgres + pgvector."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.models import Chunk
from app.domain.ports import VectorStore


class PgVectorStore(VectorStore):
    def __init__(self, engine: AsyncEngine, dim: int = 1024):
        self._engine = engine
        self._dim = dim

    async def init(self) -> None:
        ddl = f"""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS doc_chunks (
            id          BIGSERIAL PRIMARY KEY,
            document_id TEXT NOT NULL,
            case_id     TEXT,
            entity      TEXT NOT NULL DEFAULT 'DAM',
            doc_type    TEXT NOT NULL,
            chunk_index INT NOT NULL,
            content     TEXT NOT NULL,
            embedding   vector({self._dim})
        );
        CREATE INDEX IF NOT EXISTS doc_chunks_case_idx ON doc_chunks (case_id);
        CREATE INDEX IF NOT EXISTS doc_chunks_entity_idx ON doc_chunks (entity);
        """
        async with self._engine.begin() as conn:
            for stmt in ddl.strip().split(";"):
                if stmt.strip():
                    await conn.execute(text(stmt))

    async def replace_document(self, chunks: list[Chunk],
                               embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0
        async with self._engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM doc_chunks WHERE document_id = :doc_id"),
                {"doc_id": chunks[0].document_id},
            )
            for chunk, emb in zip(chunks, embeddings):
                await conn.execute(
                    text(
                        "INSERT INTO doc_chunks "
                        "(document_id, case_id, entity, doc_type, chunk_index, content, embedding) "
                        "VALUES (:d, :c, :ent, :t, :i, :x, :e)"
                    ),
                    {
                        "d": chunk.document_id,
                        "c": chunk.case_id,
                        "ent": chunk.entity.value,
                        "t": chunk.doc_type,
                        "i": chunk.chunk_index,
                        "x": chunk.content,
                        "e": str(emb),
                    },
                )
        return len(chunks)

    async def search(self, embedding: list[float], k: int = 8,
                     case_id: str | None = None,
                     doc_types: list[str] | None = None,
                     entity: str | None = None) -> list[Chunk]:
        where, params = ["1=1"], {"e": str(embedding), "k": k}
        if case_id:
            where.append("case_id = :case_id")
            params["case_id"] = case_id
        if doc_types:
            where.append("doc_type = ANY(:doc_types)")
            params["doc_types"] = doc_types
        if entity:
            where.append("entity = :entity")
            params["entity"] = entity
        sql = text(
            "SELECT document_id, case_id, entity, doc_type, chunk_index, content, "
            "1 - (embedding <=> :e) AS score "
            f"FROM doc_chunks WHERE {' AND '.join(where)} "
            "ORDER BY embedding <=> :e LIMIT :k"
        )
        async with self._engine.connect() as conn:
            rows = (await conn.execute(sql, params)).fetchall()
        return [
            Chunk(
                document_id=r.document_id,
                case_id=r.case_id,
                entity=r.entity,
                doc_type=r.doc_type,
                chunk_index=r.chunk_index,
                content=r.content,
                score=float(r.score),
            )
            for r in rows
        ]


class InMemoryVectorStore(VectorStore):
    """Cosine-similarity store for tests and DB-less development."""

    def __init__(self) -> None:
        self._rows: list[tuple[Chunk, list[float]]] = []

    async def init(self) -> None:
        return None

    async def replace_document(self, chunks: list[Chunk],
                               embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0
        doc_id = chunks[0].document_id
        self._rows = [(c, e) for c, e in self._rows if c.document_id != doc_id]
        self._rows.extend(zip(chunks, embeddings))
        return len(chunks)

    async def search(self, embedding: list[float], k: int = 8,
                     case_id: str | None = None,
                     doc_types: list[str] | None = None,
                     entity: str | None = None) -> list[Chunk]:
        def cosine(a: list[float], b: list[float]) -> float:
            return sum(x * y for x, y in zip(a, b))

        candidates = [
            (chunk, cosine(embedding, emb))
            for chunk, emb in self._rows
            if (case_id is None or chunk.case_id == case_id)
            and (doc_types is None or chunk.doc_type in doc_types)
            and (entity is None or chunk.entity.value == entity)
        ]
        candidates.sort(key=lambda pair: pair[1], reverse=True)
        return [
            chunk.model_copy(update={"score": score})
            for chunk, score in candidates[:k]
        ]
