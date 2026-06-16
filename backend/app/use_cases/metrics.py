"""Latency metrics aggregation (Sprint 2.8).

Pure function over audit records — every agent logs `latency_ms`, so the audit
trail doubles as the performance record. Computes per-operation p50/p95/max and
SLA breach rate against the targets in `domain.sla`.
"""
from app.domain.sla import sla_target_ms


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def summarize_latency(records: list[dict]) -> dict:
    """Group audit records by event and summarize latency vs SLA."""
    buckets: dict[str, list[float]] = {}
    for r in records:
        ms = r.get("latency_ms")
        if isinstance(ms, (int, float)):
            buckets.setdefault(r.get("event", "unknown"), []).append(float(ms))

    summary = {}
    for event, vals in buckets.items():
        vals.sort()
        target = sla_target_ms(event)
        breaches = sum(1 for v in vals if target is not None and v > target)
        summary[event] = {
            "count": len(vals),
            "p50_ms": round(_percentile(vals, 0.50)),
            "p95_ms": round(_percentile(vals, 0.95)),
            "max_ms": round(vals[-1]),
            "sla_ms": target,
            "breaches": breaches,
            "breach_rate": round(breaches / len(vals), 4) if vals else 0.0,
            "within_sla": breaches == 0 if target is not None else None,
        }
    return summary
