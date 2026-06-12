from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import RoutingRequest
from app.workflow.rules import evaluate

client = TestClient(app)


def test_health():
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


def test_workflow_checkpoint_blocks_without_signoff():
    case = client.post("/api/cases", data={"title": "Test case"}).json()
    case_id = case["case_id"]
    # submission → evaluation is free; evaluation → board needs sign-off (medium risk)
    assert client.post(f"/api/cases/{case_id}/advance").status_code == 200
    assert client.post(f"/api/cases/{case_id}/advance").status_code == 409
    ok = client.post(f"/api/cases/{case_id}/advance", data={"signoff_by": "reviewer-1"})
    assert ok.status_code == 200
    assert ok.json()["stage"] == "board"
