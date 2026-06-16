"""SOP authoring & lifecycle — only-approved-active routing + coverage (4.1, FR-7)."""
from datetime import date

from app.domain.models import RoutingRequest
from app.domain.rules import _sop_active, evaluate, sop_catalogue, sop_coverage


def test_active_flag_respects_status_and_effective_date():
    assert _sop_active({"status": "approved", "effective_date": "2026-01-01"}) is True
    assert _sop_active({"status": "draft", "effective_date": "2026-01-01"}) is False
    future = date(date.today().year + 1, 1, 1).isoformat()
    assert _sop_active({"status": "approved", "effective_date": future}) is False
    assert _sop_active({"status": "approved"}) is True          # no date → active


def test_approved_sop_routes():
    out = evaluate(RoutingRequest(case_id="t", request_type="asset_disposal",
                                  amount_idr=1_000_000_000))
    assert out["sop_id"] == "SOP-DAM-001"
    assert out["sop_version"] == 1


def test_draft_sop_never_routes_falls_to_fallback():
    # SOP-DAM-010 (draft) matches request_type strategic_partnership but is skipped
    out = evaluate(RoutingRequest(case_id="t", request_type="strategic_partnership",
                                  amount_idr=1_000_000_000))
    assert out["sop_id"] == "SOP-DAM-999"     # fell through to fallback


def test_catalogue_exposes_lifecycle_metadata():
    cat = {s["id"]: s for s in sop_catalogue()}
    assert cat["SOP-DAM-001"]["status"] == "approved" and cat["SOP-DAM-001"]["active"] is True
    assert cat["SOP-DAM-010"]["status"] == "draft" and cat["SOP-DAM-010"]["active"] is False
    assert cat["SOP-DAM-001"]["owner"]


def test_coverage_counts_only_active_sops():
    cov = sop_coverage(["asset_disposal", "ipo", "strategic_partnership"])
    assert cov["categories"]["asset_disposal"] == "SOP-DAM-001"
    assert cov["categories"]["ipo"] == "SOP-DAM-008"
    assert cov["categories"]["strategic_partnership"] is None    # only draft SOP → uncovered
    assert cov["served"] == 2 and cov["total"] == 3
