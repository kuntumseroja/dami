"""Decision-tree visualization + what-if simulator (Sprint 4.2, FR-7/FR-4)."""
from app.domain.rules import decision_tree


def test_decision_tree_has_three_levels():
    t = decision_tree()
    assert t["sops"] and t["approval_rules"] and t["risk_rules"]
    # approval thresholds carry the delegation levels
    levels = {r["approval_level"] for r in t["approval_rules"]}
    assert {"ceo", "dewan_pengawas", "president"} <= levels
    assert all("tier" in r for r in t["risk_rules"])


def test_decision_tree_endpoint(client):
    t = client.get("/api/routing/decision-tree").json()
    assert {s["id"] for s in t["sops"]} >= {"SOP-DAM-001", "SOP-DAM-999"}


def test_simulate_returns_fired_path(client):
    r = client.get("/api/routing/simulate",
                   params={"request_type": "capital_expenditure",
                           "amount_idr": 32_000_000_000_000}).json()
    assert r["sop_id"] == "SOP-DAM-006"
    assert r["approval_level"] == "president"
    assert r["risk_tier"] == "high"
    # the fired path names one SOP + one approval + one risk rule
    assert r["rules_fired"][0] == "SOP-DAM-006"
    assert any(x.startswith("APR-") for x in r["rules_fired"])
    assert any(x.startswith("RSK-") for x in r["rules_fired"])


def test_simulate_draft_sop_falls_to_fallback(client):
    r = client.get("/api/routing/simulate",
                   params={"request_type": "strategic_partnership", "amount_idr": 1}).json()
    assert r["sop_id"] == "SOP-DAM-999"
