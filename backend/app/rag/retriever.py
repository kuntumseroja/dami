"""Retriever facade used by all agents."""
from app.rag.embeddings import embed_query
from app.rag.vectorstore import Chunk, similarity_search


async def retrieve(
    query: str,
    k: int = 8,
    case_id: str | None = None,
    doc_types: list[str] | None = None,
) -> list[Chunk]:
    embedding = await embed_query(query)
    return await similarity_search(embedding, k=k, case_id=case_id, doc_types=doc_types)


def format_context(chunks: list[Chunk]) -> str:
    """Render chunks as a source-tagged context block for grounding prompts."""
    return "\n\n".join(
        f'<source ref="{c.ref}" type="{c.doc_type}">\n{c.content}\n</source>'
        for c in chunks
    )
