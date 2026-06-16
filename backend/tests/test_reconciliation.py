"""Financial & statistical reconciliation (Sprint 3.11, addendum A1).

The calculator is pure and deterministic — tested directly, no LLM. The model
only extracts operands; the arithmetic (and the catch) is ours.
"""
from app.domain.models import NumericClaim
from app.use_cases.reconcile_numbers import reconcile_claims, recompute


def test_recompute_formulas():
    assert abs(recompute("percentage_change", [420, 371]) - 13.207) < 0.01
    assert recompute("percentage_of", [40, 100]) == 40.0
    assert recompute("difference", [420, 371]) == 49
    assert recompute("sum", [255, 595]) == 850
    assert recompute("ratio", [850, 100]) == 8.5
    assert recompute("product", [2, 3, 4]) == 24


def test_recompute_uncomputable():
    assert recompute("ratio", [1, 0]) is None              # div by zero
    assert recompute("percentage_change", [5]) is None     # too few operands
    assert recompute("unknown_rel", [1, 2]) is None


def test_catches_planted_gain_error():
    # The planted Case-A defect: gain is (420-371)/371 = 13.2%, stated as 130%.
    claim = NumericClaim(
        description="Kenaikan terhadap nilai buku (gain on disposal %)",
        relationship="percentage_change", operands=[420_000_000_000, 371_000_000_000],
        claimed_result=130.0, unit="%", source_refs=["doc_A#1"],
    )
    [finding] = reconcile_claims([claim])
    assert finding.status == "mismatch"
    assert finding.severity == "critical"
    assert abs(finding.recomputed_result - 13.21) < 0.1
    assert "doc_A#1" in finding.source_refs


def test_correct_figure_passes():
    claim = NumericClaim(
        description="Total kebutuhan dana (sum of funding)",
        relationship="sum", operands=[255_000_000_000, 595_000_000_000],
        claimed_result=850_000_000_000, unit="IDR",
    )
    [finding] = reconcile_claims([claim])
    assert finding.status == "ok"
    assert finding.severity == "info"


def test_uncomputable_is_flagged_not_crashed():
    claim = NumericClaim(description="bad", relationship="ratio",
                         operands=[10, 0], claimed_result=5.0)
    [finding] = reconcile_claims([claim])
    assert finding.status == "uncomputable"
    assert finding.recomputed_result is None


def test_within_tolerance_passes():
    # rounding in the document (13.2% vs exact 13.207%) must not false-positive
    claim = NumericClaim(description="gain", relationship="percentage_change",
                         operands=[420, 371], claimed_result=13.2, unit="%")
    [finding] = reconcile_claims([claim])
    assert finding.status == "ok"
