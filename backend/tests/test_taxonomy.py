"""Consistency taxonomy (Sprint 3.4, FR-2)."""
from app.domain.taxonomy import (
    CONSISTENCY_TYPES,
    SEVERITIES,
    default_severities,
    normalize_severity,
    severity_for,
)


def test_eight_plus_formatting_types():
    assert len(CONSISTENCY_TYPES) == 9          # 8 PRD types + formatting
    assert "numeric_mismatch" in CONSISTENCY_TYPES
    assert "contradictory_recommendation" in CONSISTENCY_TYPES


def test_default_severities_cover_all_types():
    d = default_severities()
    assert set(d) >= set(CONSISTENCY_TYPES)
    assert all(v in SEVERITIES for v in d.values())
    assert d["numeric_mismatch"] == "critical"
    assert d["formatting_inconsistency"] == "informational"


def test_normalize_keeps_valid_and_fixes_invalid():
    assert normalize_severity("date_mismatch", "critical") == "critical"   # valid kept
    assert normalize_severity("numeric_mismatch", None) == "critical"      # default
    assert normalize_severity("numeric_mismatch", "major") == "critical"   # legacy → default
    assert normalize_severity("formatting_inconsistency", "bogus") == "informational"


def test_severity_for_unknown_type_defaults_warning():
    assert severity_for("not_a_type") == "warning"


def test_taxonomy_endpoint(client):
    rows = client.get("/api/consistency/taxonomy").json()
    assert len(rows) == 9
    assert {r["type"] for r in rows} == set(CONSISTENCY_TYPES)
    assert all(r["default_severity"] in SEVERITIES for r in rows)
