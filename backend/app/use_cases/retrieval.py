"""Retrieval helper shared by all agent use cases.

Hybrid retrieval (Sprint 2.3): combine dense (pgvector) and sparse (full-text)
results via Reciprocal Rank Fusion, then optionally rerank. Dense catches
paraphrase; sparse catches exact figures/names/clause numbers that embeddings
blur — both matter for governance docs.
"""
from app.domain.models import Chunk
from app.domain.ports import Embedder, Reranker, VectorStore

RRF_C = 60  # reciprocal-rank-fusion constant (standard)


def rrf_fuse(result_lists: list[list[Chunk]], k: int) -> list[Chunk]:
    """Merge ranked lists by Reciprocal Rank Fusion: score = Σ 1/(C + rank)."""
    scores: dict[str, float] = {}
    by_ref: dict[str, Chunk] = {}
    for lst in result_lists:
        for rank, ch in enumerate(lst):
            scores[ch.ref] = scores.get(ch.ref, 0.0) + 1.0 / (RRF_C + rank + 1)
            by_ref.setdefault(ch.ref, ch)
    ordered = sorted(scores, key=lambda r: scores[r], reverse=True)
    return [by_ref[r].model_copy(update={"score": scores[r]}) for r in ordered[:k]]


async def retrieve(query: str, *, embedder: Embedder, vectors: VectorStore,
                   k: int = 8, case_id: str | None = None,
                   doc_types: list[str] | None = None,
                   entity: str | None = None,
                   reranker: Reranker | None = None) -> list[Chunk]:
    embedding = await embedder.embed_query(query)
    pool = max(k * 2, 12)
    dense = await vectors.search(embedding, k=pool, case_id=case_id,
                                 doc_types=doc_types, entity=entity)
    sparse = await vectors.keyword_search(query, k=pool, case_id=case_id,
                                          doc_types=doc_types, entity=entity)
    fused = rrf_fuse([dense, sparse], k=pool)
    if reranker is not None:
        return await reranker.rerank(query, fused, k=k)
    return fused[:k]


def format_context(chunks: list[Chunk]) -> str:
    """Render chunks as a source-tagged context block for grounding prompts."""
    return "\n\n".join(
        f'<source ref="{c.ref}" type="{c.doc_type}">\n{c.content}\n</source>'
        for c in chunks
    )
