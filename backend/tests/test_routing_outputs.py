"""Routing output completion: pre-conditions, timeline, ambiguity (4.3, FR-4)."""
from app.domain.models import RoutingRequest
from app.domain.rules import evaluate


def test_four_part_output_present():
    out = evaluate(RoutingRequest(case_id="t", request_type="asset_disposal",
                                  amount_idr=420_000_000_000))
    assert out["sop_id"] == "SOP-DAM-001"                 # (a) applicable SOP
    assert out["approval_required"] is True               # (b) required approvals
    assert "Independent KJPP valuation attached" in out["pre_conditions"]  # (c)
    assert out["expected_timeline_days"] == 7             # (d) timeline (ceo tier)
    assert out["ambiguous"] is False


def test_timeline_scales_with_approval_level():
    psn = evaluate(RoutingRequest(case_id="t", request_type="capital_expenditure",
                                  amount_idr=32_000_000_000_000))
    assert psn["approval_level"] == "president"
    assert psn["expected_timeline_days"] == 45


def test_unnecessary_approval_suppressed():
    # below the 1B delegation floor → no approval needed, flagged as suppressed
    out = evaluate(RoutingRequest(case_id="t", request_type="asset_lease",
                                  amount_idr=750_000_000))
    assert out["approval_required"] is False
    assert out["approval_suppressed"] is True


def test_ambiguous_routing_routes_to_resolver():
    # no specific SOP (falls to fallback) → ambiguous + named resolver
    out = evaluate(RoutingRequest(case_id="t", request_type="strategic_partnership",
                                  amount_idr=1_000_000_000))
    assert out["sop_id"] == "SOP-DAM-999"
    assert out["ambiguous"] is True
    assert out["resolver"]


def test_missing_amount_is_ambiguous():
    out = evaluate(RoutingRequest(case_id="t", request_type="asset_disposal",
                                  amount_idr=None))
    assert out["ambiguous"] is True


def test_simulate_endpoint_carries_four_part(client):
    r = client.get("/api/routing/simulate",
                   params={"request_type": "merger_acquisition",
                           "amount_idr": 4_200_000_000_000}).json()
    assert r["pre_conditions"] and r["expected_timeline_days"] == 21
    assert r["ambiguous"] is False
