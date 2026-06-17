"""Multi-dimensional risk scoring (Sprint 4.5, FR-8).

Five deterministic dimensions — transaction value, entity risk, novelty,
precedent availability, regulatory exposure — each scored 0..1 from config.
Below threshold on ALL dimensions → fully automated path; any dimension at/above
threshold → human-in-the-loop with the score + flagged dimensions surfaced.
Config-driven (env/file), framework-free (mirrors the SOP rule engine).
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

_DIM_NAMES = {
    "transaction_value": "Transaction value",
    "entity_risk": "Entity risk rating",
    "novelty": "Novelty",
    "precedent_availability": "Precedent availability",
    "regulatory_exposure": "Regulatory exposure",
}


@lru_cache
def load_config() -> dict:
    cfg = Path(os.environ.get("RISK_SCORING_CONFIG", "../config/risk-scoring.yaml"))
    if not cfg.exists():
        cfg = Path(__file__).resolve().parents[3] / "config/risk-scoring.yaml"
    return yaml.safe_load(cfg.read_text(encoding="utf-8"))


def _value_score(amount: float, cfg: dict) -> float:
    for band in cfg["value_bands"]:
        if band["max"] is None or amount < band["max"]:
            return float(band["score"])
    return 1.0


def _entity_score(entity: str, cfg: dict) -> float:
    ratings = cfg.get("entity_ratings", {})
    for key, val in ratings.items():
        if key != "default" and key.lower() in (entity or "").lower():
            return float(val)
    return float(ratings.get("default", 0.3))


def score_request(*, amount_idr: float | None, request_category: str,
                  entity: str = "", precedent_count: int = 0) -> dict:
    cfg = load_config()
    threshold = float(cfg.get("threshold", 0.5))
    low = int(cfg.get("precedent_low_count", 2))
    amount = amount_idr or 0.0

    precedent = 0.2 if precedent_count >= low else (0.6 if precedent_count == 1 else 0.9)
    scores = {
        "transaction_value": _value_score(amount, cfg),
        "entity_risk": _entity_score(entity, cfg),
        "novelty": 0.2 if precedent_count > 0 else 0.8,
        "precedent_availability": precedent,
        "regulatory_exposure": float(
            cfg.get("regulatory_exposure", {}).get(request_category, 0.6)),
    }
    weights = cfg["weights"]
    dims = []
    for key, sc in scores.items():
        dims.append({"id": key, "name": _DIM_NAMES.get(key, key),
                     "score": round(sc, 3), "weight": weights.get(key, 0),
                     "flagged": sc >= threshold})
    total = round(sum(scores[k] * weights.get(k, 0) for k in scores), 4)
    flagged = [d["id"] for d in dims if d["flagged"]]
    automated = not flagged
    return {
        "dimensions": dims, "total": total, "threshold": threshold,
        "flagged_dimensions": flagged, "automated": automated,
        "recommendation": ("Fully automated path — all dimensions below threshold"
                           if automated else
                           "Human-in-the-loop — review flagged dimension(s)"),
    }
