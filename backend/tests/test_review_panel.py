"""NOTA Review Panel — config + citation gate (Sprint 3.10).

The orchestration is LLM-driven (verified live); here we test the deterministic
pieces: roster config and the citation gate that drops uncited findings (RVW-003).
"""
from app.use_cases.review_panel import (
    _dimension_index,
    _reviewer_roles,
    is_grounded_citation,
    panel_config,
)


def test_panel_config_has_dimensions_and_roles():
    cfg = panel_config()
    assert len(cfg["dimensions"]) >= 8
    ids = {d["id"] for d in cfg["dimensions"]}
    assert {"DIM-LEGAL", "DIM-FINANCE", "DIM-RISK", "DIM-CALC", "DIM-ACCURACY"} <= ids


def test_reviewer_roles_are_the_md_lenses():
    ids = {r["id"] for r in _reviewer_roles()}
    assert {"md_investment", "md_risk", "md_legal", "md_finance"} <= ids
    # deterministic helpers run on a different tier, not as reasoning reviewers
    assert "accuracy_verifier" not in ids
    assert "financial_reconciliation" not in ids


def test_dimension_index_maps_id_to_name():
    idx = _dimension_index()
    assert idx["DIM-LEGAL"]["name"].lower().startswith("legal")


def test_citation_gate_accepts_source_ref_and_rule_id():
    valid = {"doc_abc#0", "doc_abc#1"}
    assert is_grounded_citation("doc_abc#0", valid) is True       # resolvable source
    assert is_grounded_citation("APR-003", valid) is True          # fired rule id
    assert is_grounded_citation("SOP-DAM-005", valid) is True
    assert is_grounded_citation("DIM-CALC", valid) is True


def test_citation_gate_drops_uncited_or_hallucinated():
    valid = {"doc_abc#0"}
    assert is_grounded_citation("doc_ghost#9", valid) is False     # hallucinated ref
    assert is_grounded_citation("", valid) is False                # no citation
    assert is_grounded_citation("the submission letter", valid) is False  # prose, not a ref
