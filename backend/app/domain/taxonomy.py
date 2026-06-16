"""Consistency-finding taxonomy (Sprint 3.4, FR-2).

The PRD's 8-type taxonomy with Critical / Warning / Informational severities.
Default severity per type is configurable: a YAML at CONSISTENCY_TAXONOMY env
(or config/consistency-taxonomy.yaml) can override the built-in defaults. Plain
env access keeps the domain framework-free (mirrors the SOP rule engine).
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

# 8 PRD finding types (+ formatting). Used as the ConsistencyFinding.kind enum.
CONSISTENCY_TYPES = [
    "numeric_mismatch",
    "date_mismatch",
    "entity_name_mismatch",
    "stale_version_reference",
    "missing_propagated_update",
    "contradictory_recommendation",
    "scope_deviation",
    "structural_omission",
    "formatting_inconsistency",
]

SEVERITIES = ["critical", "warning", "informational"]

_BUILTIN_DEFAULTS = {
    "numeric_mismatch": "critical",
    "date_mismatch": "warning",
    "entity_name_mismatch": "warning",
    "stale_version_reference": "warning",
    "missing_propagated_update": "critical",
    "contradictory_recommendation": "critical",
    "scope_deviation": "warning",
    "structural_omission": "warning",
    "formatting_inconsistency": "informational",
}


@lru_cache
def default_severities() -> dict:
    """Built-in defaults, overlaid with any config overrides."""
    cfg = Path(os.environ.get("CONSISTENCY_TAXONOMY", "../config/consistency-taxonomy.yaml"))
    if not cfg.exists():
        cfg = Path(__file__).resolve().parents[3] / "config/consistency-taxonomy.yaml"
    merged = dict(_BUILTIN_DEFAULTS)
    if cfg.exists():
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        for item in data.get("types", []):
            sev = item.get("default_severity")
            if item.get("type") in merged and sev in SEVERITIES:
                merged[item["type"]] = sev
    return merged


def severity_for(kind: str) -> str:
    return default_severities().get(kind, "warning")


def normalize_severity(kind: str, severity: str | None) -> str:
    """Trust a valid model-assigned severity; otherwise fall back to the
    configured default for the type."""
    return severity if severity in SEVERITIES else severity_for(kind)
