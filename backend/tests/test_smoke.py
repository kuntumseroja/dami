from pathlib import Path

from app.domain.models import RoutingRequest
from app.domain.rules import evaluate
from tests.conftest import APPROVER, DRAFTER, REVIEWER


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_routing_rules_low_value_lease_is_automated():
    outcome = evaluate(
        RoutingRequest(case_id="t1", request_type="asset_lease", amount_idr=500_000_000)
    )
    assert outcome["approval_required"] is False
    assert outcome["risk_tier"].value == "low"
    assert "SOP-DAM-003" in outcome["sop"]


def test_routing_rules_high_value_needs_board():
    outcome = evaluate(
        RoutingRequest(case_id="t2", request_type="investment", amount_idr=600_000_000_000)
    )
    assert outcome["approval_required"] is True
    assert outcome["approval_level"] == "board_of_commissioners"
    assert outcome["risk_tier"].value == "high"


def test_unauthenticated_request_rejected_outside_dev(client):
    assert client.post("/api/cases", data={"title": "x"}).status_code == 401


def test_checkpoint_requires_approver_role(client):
    case = client.post("/api/cases", data={"title": "Test case"}, headers=DRAFTER).json()
    case_id = case["case_id"]

    # submission → evaluation: no checkpoint
    assert client.post(f"/api/cases/{case_id}/advance", headers=DRAFTER).status_code == 200
    # evaluation is a human checkpoint for medium-risk: reviewer alone is not enough
    denied = client.post(f"/api/cases/{case_id}/advance", headers=REVIEWER)
    assert denied.status_code == 403
    # approver advances, and the sign-off identity is the authenticated user
    ok = client.post(f"/api/cases/{case_id}/advance", headers=APPROVER)
    assert ok.status_code == 200
    body = ok.json()
    assert body["stage"] == "board"
    assert body["history"][-1]["actor"] == "user-approver"


def test_ingestion_stores_original_and_registers_document(client, tmp_path):
    case = client.post("/api/cases", data={"title": "Ingest case"}, headers=DRAFTER).json()
    case_id = case["case_id"]

    response = client.post(
        "/api/documents/ingest",
        files={"file": ("submission.txt", b"Permohonan sewa aset senilai Rp500.000.000")},
        data={"doc_type": "submission", "case_id": case_id},
        headers=DRAFTER,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["chunks_indexed"] >= 1
    assert result["storage_key"].startswith(f"cases/{case_id}/")
    # Original preserved on the storage backend
    assert (Path("./.test-data/objects") / result["storage_key"]).exists()

    docs = client.get(f"/api/cases/{case_id}/documents", headers=DRAFTER).json()
    assert len(docs) == 1
    assert docs[0]["is_master"] is True
    assert docs[0]["storage_key"] == result["storage_key"]


def test_risk_tier_change_requires_role(client):
    case = client.post("/api/cases", data={"title": "Risk case"}, headers=DRAFTER).json()
    case_id = case["case_id"]
    denied = client.post(f"/api/cases/{case_id}/risk-tier",
                         data={"tier": "low"}, headers=DRAFTER)
    assert denied.status_code == 403
    ok = client.post(f"/api/cases/{case_id}/risk-tier",
                     data={"tier": "low"}, headers=REVIEWER)
    assert ok.status_code == 200
    assert ok.json()["risk_tier"] == "low"
