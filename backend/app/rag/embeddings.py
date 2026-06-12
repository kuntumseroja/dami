"""Embedding provider.

Default implementation is a deterministic hash-based embedding so the
platform runs end-to-end with zero external embedding dependency. Swap
`embed_texts` for an enterprise embedding service (e.g. Voyage AI, or an
on-prem model) before production — the interface is the only contract.
"""
import hashlib
import math

from app.rag.vectorstore import EMBEDDING_DIM


def _hash_embed(value: str) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    for token in value.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return [_hash_embed(t) for t in texts]


async def embed_query(query: str) -> list[float]:
    return _hash_embed(query)
