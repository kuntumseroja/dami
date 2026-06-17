"""Multi-dimensional risk scoring (Sprint 4.5, FR-8)."""
from app.domain.risk_scoring import score_request


def test_five_dimensions_scored():
    s = score_request(amount_idr=1_000_000_000, request_category="asset_lease",
                      entity="Pelindo", precedent_count=5)
    ids = {d["id"] for d in s["dimensions"]}
    assert ids == {"transaction_value", "entity_risk", "novelty",
                   "precedent_availability", "regulatory_exposure"}


def test_low_risk_lease_is_fully_automated():
    s = score_request(amount_idr=500_000_000, request_category="asset_lease",
                      entity="Pelindo", precedent_count=5)
    assert s["automated"] is True
    assert s["flagged_dimensions"] == []


def test_large_mna_is_assisted():
    s = score_request(amount_idr=56_000_000_000_000, request_category="merger_acquisition",
                      entity="MIND ID", precedent_count=0)
    assert s["automated"] is False
    # value, regulatory, novelty, precedent all above threshold
    assert "transaction_value" in s["flagged_dimensions"]
    assert "regulatory_exposure" in s["flagged_dimensions"]


def test_novelty_and_precedent_react_to_history():
    novel = score_request(amount_idr=100_000_000, request_category="asset_lease",
                          precedent_count=0)
    seen = score_request(amount_idr=100_000_000, request_category="asset_lease",
                         precedent_count=5)
    nov = {d["id"]: d["score"] for d in novel["dimensions"]}
    sn = {d["id"]: d["score"] for d in seen["dimensions"]}
    assert nov["novelty"] > sn["novelty"]
    assert nov["precedent_availability"] > sn["precedent_availability"]
    assert novel["automated"] is False and seen["automated"] is True


def test_endpoint(client):
    r = client.get("/api/risk/score", params={
        "request_category": "ipo", "amount_idr": 9_000_000_000_000,
        "entity": "PGEO", "precedents": 0}).json()
    assert r["automated"] is False and r["total"] > 0
