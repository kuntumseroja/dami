from pathlib import Path

from app.domain.models import RoutingRequest
from app.domain.rules import evaluate
from tests.conftest import (
    APPROVER,
    BPI_OVERSIGHT,
    DAM_DRAFTER,
    DIM_DRAFTER,
    DRAFTER,
    REVIEWER,
)


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
    # Storage key is namespaced by BPI entity (Phase 2 tenant seam)
    assert result["storage_key"].startswith(f"DAM/cases/{case_id}/")
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


# --- Phase 2 foundation: multi-tenancy (FR-9) ---------------------------------

def test_case_carries_bpi_entity_from_creator(client):
    dam = client.post("/api/cases", data={"title": "DAM case"}, headers=DAM_DRAFTER).json()
    dim = client.post("/api/cases", data={"title": "DIM case"}, headers=DIM_DRAFTER).json()
    assert dam["entity"] == "DAM"
    assert dim["entity"] == "DIM"


def test_tenant_isolation_on_list_and_get(client):
    dim = client.post("/api/cases", data={"title": "DIM only"}, headers=DIM_DRAFTER).json()
    dim_id = dim["case_id"]

    # A DAM user cannot list or fetch a DIM case
    dam_list = client.get("/api/cases", headers=DAM_DRAFTER).json()
    assert all(c["entity"] == "DAM" for c in dam_list)
    assert dim_id not in [c["case_id"] for c in dam_list]
    assert client.get(f"/api/cases/{dim_id}", headers=DAM_DRAFTER).status_code == 404

    # BPI oversight sees across entities
    all_list = client.get("/api/cases", headers=BPI_OVERSIGHT).json()
    assert dim_id in [c["case_id"] for c in all_list]


def test_tenant_isolation_blocks_cross_entity_advance(client):
    dim = client.post("/api/cases", data={"title": "DIM workflow"}, headers=DIM_DRAFTER).json()
    dim_id = dim["case_id"]
    # DAM user attempting to advance a DIM case sees not-found, not the case
    assert client.post(f"/api/cases/{dim_id}/advance", headers=DAM_DRAFTER).status_code == 404


# --- Phase 1 foundation: data classification (FR-5 / §11.1) -------------------

def test_document_carries_classification(client):
    case = client.post("/api/cases", data={"title": "Classified"}, headers=DAM_DRAFTER).json()
    case_id = case["case_id"]
    client.post(
        "/api/documents/ingest",
        files={"file": ("secret.txt", b"Restricted submission content")},
        data={"doc_type": "submission", "case_id": case_id, "classification": "restricted"},
        headers=DAM_DRAFTER,
    )
    docs = client.get(f"/api/cases/{case_id}/documents", headers=DAM_DRAFTER).json()
    assert docs[0]["classification"] == "restricted"
    assert docs[0]["entity"] == "DAM"


# --- Document source: OneDrive/SharePoint interface (local twin) ---------------

def test_sync_from_document_source(client, tmp_path):
    # Seed a fake OneDrive/SharePoint library folder
    src = Path("./.test-data/source/inbox")
    src.mkdir(parents=True, exist_ok=True)
    (src / "submission-001.txt").write_bytes(b"Permohonan dari OneDrive")
    (src / "submission-002.txt").write_bytes(b"Second submission")

    listed = client.get("/api/sources/items?folder=inbox", headers=DAM_DRAFTER)
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    case = client.post("/api/cases", data={"title": "From OneDrive"}, headers=DAM_DRAFTER).json()
    synced = client.post(
        "/api/sources/sync",
        data={"folder": "inbox", "doc_type": "submission", "case_id": case["case_id"]},
        headers=DAM_DRAFTER,
    )
    assert synced.status_code == 200, synced.text
    assert synced.json()["ingested"] == 2
    docs = client.get(f"/api/cases/{case['case_id']}/documents", headers=DAM_DRAFTER).json()
    assert len(docs) == 2
