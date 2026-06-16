"""Retrieval eval harness (Sprint 2.4).

Loads a golden set (corpus + queries with known-relevant content), ingests the
corpus through the real chunker + embedder into an in-memory store, then scores
retrieval. Runs in two modes — `dense` (vector search only) and `hybrid`
(dense + sparse RRF + rerank) — so the hybrid lift from 2.3 is measured, not
asserted. Content-match relevance keeps it embedder-agnostic: it runs in CI on
the hash embedder today and on the enterprise embedder once 2.1 lands.
"""
from pathlib import Path

import yaml

from app.adapters.reranker import LexicalReranker
from app.adapters.vector_pgvector import InMemoryVectorStore
from app.domain.models import Chunk
from app.domain.ports import Embedder
from app.use_cases.chunking import semantic_chunks
from app.use_cases.retrieval import retrieve

_REPO = Path(__file__).resolve().parents[3]
GOLDEN_PATH = _REPO / "config" / "eval" / "retrieval_golden.yaml"

# Quality gate: a model/index change that drops below these fails CI.
MIN_HIT_AT_K = 0.80
DEFAULT_K = 5


def load_golden(path: Path = GOLDEN_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


async def build_store(corpus: list[dict], embedder: Embedder) -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    for doc in corpus:
        pieces = semantic_chunks(doc["text"])
        chunks = [
            Chunk(document_id=doc["id"], case_id="golden",
                  doc_type=doc.get("doc_type", "submission"),
                  chunk_index=i, content=piece)
            for i, piece in enumerate(pieces)
        ]
        embeddings = await embedder.embed_texts([c.content for c in chunks])
        await store.replace_document(chunks, embeddings)
    return store


def _hits(chunks: list[Chunk], must_contain: list[str]) -> list[bool]:
    """For each expected phrase, whether any retrieved chunk contains it."""
    blob = "\n".join(c.content.lower() for c in chunks)
    return [phrase.lower() in blob for phrase in must_contain]


def _first_relevant_rank(chunks: list[Chunk], must_contain: list[str]) -> int | None:
    wanted = [p.lower() for p in must_contain]
    for rank, c in enumerate(chunks, start=1):
        low = c.content.lower()
        if any(p in low for p in wanted):
            return rank
    return None


async def run_eval(golden: dict, embedder: Embedder, *, mode: str = "hybrid",
                   k: int = DEFAULT_K) -> dict:
    """Score one retrieval mode over the golden set. Returns a scorecard dict."""
    store = await build_store(golden["corpus"], embedder)
    reranker = LexicalReranker() if mode == "hybrid" else None

    n = 0
    hit_count = 0.0          # query hits (all expected phrases in top-k)
    recall_sum = 0.0         # fraction of expected phrases found, averaged
    mrr_sum = 0.0
    misses: list[str] = []

    for item in golden["queries"]:
        q, must = item["q"], item["must_contain"]
        if mode == "dense":
            embedding = await embedder.embed_query(q)
            chunks = await store.search(embedding, k=k, case_id="golden")
        else:
            chunks = await retrieve(q, embedder=embedder, vectors=store,
                                    reranker=reranker, k=k, case_id="golden")
        flags = _hits(chunks, must)
        n += 1
        recall_sum += sum(flags) / len(flags)
        if all(flags):
            hit_count += 1
        else:
            misses.append(q)
        rank = _first_relevant_rank(chunks, must)
        mrr_sum += (1.0 / rank) if rank else 0.0

    return {
        "mode": mode,
        "k": k,
        "n": n,
        "hit_at_k": round(hit_count / n, 4) if n else 0.0,
        "recall_at_k": round(recall_sum / n, 4) if n else 0.0,
        "mrr": round(mrr_sum / n, 4) if n else 0.0,
        "misses": misses,
    }
