"""Retrieval helper shared by all agent use cases."""
from app.domain.models import Chunk
from app.domain.ports import Embedder, VectorStore


async def retrieve(query: str, *, embedder: Embedder, vectors: VectorStore,
                   k: int = 8, case_id: str | None = None,
                   doc_types: list[str] | None = None) -> list[Chunk]:
    embedding = await embedder.embed_query(query)
    return await vectors.search(embedding, k=k, case_id=case_id, doc_types=doc_types)


def format_context(chunks: list[Chunk]) -> str:
    """Render chunks as a source-tagged context block for grounding prompts."""
    return "\n\n".join(
        f'<source ref="{c.ref}" type="{c.doc_type}">\n{c.content}\n</source>'
        for c in chunks
    )
