"""Draft-latency SLA instrumentation (Sprint 2.8)."""
from app.domain.sla import sla_target_ms, within_sla
from app.use_cases.metrics import summarize_latency
from tests.conftest import DRAFTER


def test_within_sla_classification():
    assert within_sla("agent.drafting", 1000) is True
    assert within_sla("agent.drafting", sla_target_ms("agent.drafting") + 1) is False
    assert within_sla("unknown.event", 1) is None      # untracked op


def test_summarize_latency_percentiles_and_breaches():
    target = sla_target_ms("agent.drafting")
    records = (
        [{"event": "agent.drafting", "latency_ms": ms}
         for ms in [1000, 2000, 3000, 4000]]
        + [{"event": "agent.drafting", "latency_ms": target + 5000}]   # 1 breach
        + [{"event": "agent.routing", "latency_ms": 500}]
        + [{"event": "agent.drafting"}]                                # no latency → ignored
    )
    s = summarize_latency(records)
    d = s["agent.drafting"]
    assert d["count"] == 5
    assert d["max_ms"] == target + 5000
    assert d["p50_ms"] == 3000
    assert d["breaches"] == 1
    assert d["within_sla"] is False
    assert s["agent.routing"]["count"] == 1
    assert s["agent.routing"]["within_sla"] is True


def test_latency_metrics_endpoint(client):
    r = client.get("/api/metrics/latency", headers=DRAFTER)
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
