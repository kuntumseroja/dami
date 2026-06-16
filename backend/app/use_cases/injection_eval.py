"""Consistency-checker injection harness (Sprint 3.9, FR-2 metrics).

Loads the injection manifest (document sets with known planted discrepancies),
scores a run's findings into per-type precision / recall / F1, and gates a model
update against a frozen baseline (fail if recall drops beyond tolerance). The
scorer is pure (type-level, no LLM), so it runs in CI; the live run feeds real
`check_consistency` output into the same `score_run`.
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

# AC thresholds: numeric recall >= 0.93 (AC-2.2); other (semantic) recall >= 0.85
# (AC-2.3). A model update may not drop any type's recall by more than this.
NUMERIC_RECALL_MIN = 0.93
SEMANTIC_RECALL_MIN = 0.85
MAX_RECALL_DROP = 0.05


@lru_cache
def load_injections(path: str | None = None) -> dict:
    p = Path(path or os.environ.get("CONSISTENCY_INJECTIONS",
             "../config/eval/consistency-injections.yaml"))
    if not p.exists():
        p = Path(__file__).resolve().parents[3] / "config/eval/consistency-injections.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def score_run(results: list[dict]) -> dict:
    """results: [{case_id, expected: [kinds], found: [kinds]}] → metrics by type.

    Type-level set scoring per case: a type is a true positive if it is both
    expected and found; false negative if expected not found; false positive if
    found not expected.
    """
    tp: dict[str, int] = {}
    fp: dict[str, int] = {}
    fn: dict[str, int] = {}
    for r in results:
        expected, found = set(r["expected"]), set(r.get("found", []))
        for t in expected & found:
            tp[t] = tp.get(t, 0) + 1
        for t in expected - found:
            fn[t] = fn.get(t, 0) + 1
        for t in found - expected:
            fp[t] = fp.get(t, 0) + 1

    types = set(tp) | set(fp) | set(fn)
    per_type = {}
    for t in sorted(types):
        t_tp, t_fp, t_fn = tp.get(t, 0), fp.get(t, 0), fn.get(t, 0)
        precision = t_tp / (t_tp + t_fp) if (t_tp + t_fp) else 0.0
        recall = t_tp / (t_tp + t_fn) if (t_tp + t_fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_type[t] = {"tp": t_tp, "fp": t_fp, "fn": t_fn,
                       "precision": round(precision, 4), "recall": round(recall, 4),
                       "f1": round(f1, 4)}
    total_tp, total_fp, total_fn = sum(tp.values()), sum(fp.values()), sum(fn.values())
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    return {"per_type": per_type, "cases": len(results),
            "micro_recall": round(micro_recall, 4),
            "micro_precision": round(micro_prec, 4)}


def meets_thresholds(scores: dict) -> tuple[bool, list[str]]:
    """Check per-type recall against the AC thresholds."""
    failures = []
    for t, m in scores["per_type"].items():
        floor = NUMERIC_RECALL_MIN if t == "numeric_mismatch" else SEMANTIC_RECALL_MIN
        if m["recall"] < floor:
            failures.append(f"{t} recall {m['recall']} < {floor}")
    return (not failures), failures


def check_against_baseline(scores: dict, baseline: dict,
                           max_drop: float = MAX_RECALL_DROP) -> tuple[bool, list[str]]:
    """Model-update gate: no type's recall may regress beyond max_drop vs baseline."""
    regressions = []
    base = baseline.get("per_type", {})
    for t, m in scores["per_type"].items():
        prior = base.get(t, {}).get("recall")
        if prior is not None and m["recall"] < prior - max_drop:
            regressions.append(f"{t}: {m['recall']} < baseline {prior} - {max_drop}")
    return (not regressions), regressions
