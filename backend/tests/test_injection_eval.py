"""Consistency-checker injection harness (Sprint 3.9, FR-2 metrics)."""
from app.use_cases.injection_eval import (
    check_against_baseline,
    load_injections,
    meets_thresholds,
    score_run,
)


def test_manifest_has_ten_cases_covering_the_taxonomy():
    cases = load_injections()["cases"]
    assert len(cases) >= 10
    kinds = {k for c in cases for k in c["expected"]}
    assert {"numeric_mismatch", "date_mismatch", "entity_name_mismatch",
            "contradictory_recommendation", "structural_omission"} <= kinds


def _results_from_manifest(found_fn):
    return [{"case_id": c["id"], "expected": c["expected"],
             "found": found_fn(c["expected"])} for c in load_injections()["cases"]]


def test_perfect_run_scores_full_recall():
    scores = score_run(_results_from_manifest(lambda exp: exp))   # found == expected
    assert scores["micro_recall"] == 1.0
    ok, failures = meets_thresholds(scores)
    assert ok and failures == []


def test_missed_numeric_fails_threshold():
    # checker misses every numeric_mismatch → numeric recall 0 < 0.93
    scores = score_run(_results_from_manifest(
        lambda exp: [k for k in exp if k != "numeric_mismatch"]))
    ok, failures = meets_thresholds(scores)
    assert ok is False
    assert any("numeric_mismatch" in f for f in failures)


def test_precision_drops_with_spurious_findings():
    scores = score_run([
        {"case_id": "x", "expected": ["numeric_mismatch"],
         "found": ["numeric_mismatch", "date_mismatch", "scope_deviation"]},
    ])
    assert scores["per_type"]["numeric_mismatch"]["recall"] == 1.0
    assert scores["per_type"]["date_mismatch"]["precision"] == 0.0   # false positive


def test_baseline_gate_flags_regression():
    baseline = {"per_type": {"numeric_mismatch": {"recall": 1.0}}}
    good = {"per_type": {"numeric_mismatch": {"recall": 0.97}}}
    bad = {"per_type": {"numeric_mismatch": {"recall": 0.80}}}
    assert check_against_baseline(good, baseline)[0] is True
    ok, regressions = check_against_baseline(bad, baseline)
    assert ok is False and regressions
