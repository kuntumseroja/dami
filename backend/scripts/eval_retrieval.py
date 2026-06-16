#!/usr/bin/env python
"""Print the retrieval eval scorecard; exit non-zero if below the quality gate.

Used by the nightly CI job and runnable locally:
    python -m scripts.eval_retrieval
"""
import asyncio
import sys

from app.adapters.embedder_hash import HashEmbedder
from app.use_cases.eval_retrieval import MIN_HIT_AT_K, load_golden, run_eval


async def _main() -> int:
    golden = load_golden()
    embedder = HashEmbedder()
    hybrid = await run_eval(golden, embedder, mode="hybrid")
    dense = await run_eval(golden, embedder, mode="dense")

    print(f"Golden retrieval eval — {hybrid['n']} queries, k={hybrid['k']}, "
          "embedder=hash (floor)\n")
    print(f"  {'metric':<14}{'dense':>10}{'hybrid':>10}{'lift':>10}")
    for m in ("hit_at_k", "recall_at_k", "mrr"):
        d, h = dense[m], hybrid[m]
        print(f"  {m:<14}{d:>10.4f}{h:>10.4f}{h - d:>+10.4f}")

    if hybrid["misses"]:
        print("\n  hybrid misses:")
        for q in hybrid["misses"]:
            print(f"    - {q}")

    ok = hybrid["hit_at_k"] >= MIN_HIT_AT_K and hybrid["hit_at_k"] >= dense["hit_at_k"]
    print(f"\n  gate hit_at_k >= {MIN_HIT_AT_K}: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
