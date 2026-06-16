"""Latency SLA targets per agent operation (Sprint 2.8).

Wall-clock budgets in milliseconds. The drafting SLA is the headline metric for
the ~30% productivity goal; the others bound the surrounding pipeline. Tune per
deployment — these are conservative demo defaults for managed Claude tiers.
"""

SLA_TARGETS_MS = {
    "agent.drafting": 60_000,
    "agent.consistency": 90_000,
    "agent.reconciliation": 60_000,
    "agent.extraction": 30_000,
    "agent.routing": 30_000,
    "orchestrator.pipeline_completed": 180_000,
}


def sla_target_ms(event: str) -> int | None:
    return SLA_TARGETS_MS.get(event)


def within_sla(event: str, latency_ms: float) -> bool | None:
    """True/False if the event has an SLA target, else None (untracked)."""
    target = SLA_TARGETS_MS.get(event)
    if target is None:
        return None
    return latency_ms <= target
