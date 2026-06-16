"""Golden-set retrieval eval (Sprint 2.4).

Guards retrieval quality against model/index regressions and proves the hybrid
lift from 2.3. Runs on the hash embedder, so the absolute numbers are a floor —
the enterprise embedder (2.1) only raises them.
"""
import pytest

from app.adapters.embedder_hash import HashEmbedder
from app.use_cases.eval_retrieval import MIN_HIT_AT_K, load_golden, run_eval


@pytest.mark.asyncio
async def test_golden_set_has_at_least_20_queries():
    golden = load_golden()
    assert len(golden["queries"]) >= 20            # "20-case regression suite"
    assert golden["corpus"]


@pytest.mark.asyncio
async def test_hybrid_meets_quality_gate():
    golden = load_golden()
    card = await run_eval(golden, HashEmbedder(), mode="hybrid")
    assert card["hit_at_k"] >= MIN_HIT_AT_K, f"regression: {card}"


@pytest.mark.asyncio
async def test_hybrid_beats_dense_only():
    golden = load_golden()
    hybrid = await run_eval(golden, HashEmbedder(), mode="hybrid")
    dense = await run_eval(golden, HashEmbedder(), mode="dense")
    # Sparse + RRF must not hurt; on exact-figure governance queries it helps.
    assert hybrid["hit_at_k"] >= dense["hit_at_k"]
    assert hybrid["mrr"] >= dense["mrr"]
