"""Reranker adapters (Sprint 2.3).

LexicalReranker: a cheap, deterministic default — reorders candidates by how
many distinct query terms each chunk covers, then by its fusion score. No model
call. Swap for a cross-encoder or LLM reranker (same port) when approved; the
retrieval use case is unchanged.
"""
import re

from app.domain.models import Chunk
from app.domain.ports import Reranker


class LexicalReranker(Reranker):
    async def rerank(self, query: str, chunks: list[Chunk], k: int = 8) -> list[Chunk]:
        terms = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 2}
        if not terms:
            return chunks[:k]

        def key(c: Chunk):
            ctext = c.content.lower()
            covered = sum(1 for t in terms if t in ctext)          # distinct-term coverage
            density = sum(ctext.count(t) for t in terms)           # tie-break: term frequency
            return (covered, density, c.score)

        return sorted(chunks, key=key, reverse=True)[:k]
