"""Deterministic hash-based Embedder.

Zero-dependency fallback so the platform runs end-to-end without an external
embedding service. Sprint 2 replaces this with an enterprise embedding model
behind the same port.
"""
import hashlib
import math

from app.domain.ports import Embedder

EMBEDDING_DIM = 1024


def _hash_embed(value: str) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    for token in value.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashEmbedder(Embedder):
    dim = EMBEDDING_DIM

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embed(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return _hash_embed(query)
