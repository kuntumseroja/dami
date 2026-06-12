"""Explainability query surface.

Reconstructs the full decision trace for any output: which sources were
retrieved, which rules fired, which model produced which text, and who
signed off. Built on the append-only audit log.
"""
from app.core.audit import read_audit_log


def trace_for_case(case_id: str, limit: int = 1000) -> list[dict]:
    return [r for r in read_audit_log(limit) if r.get("case_id") == case_id]


def trace_by_id(trace_id: str, limit: int = 5000) -> list[dict]:
    return [
        r for r in read_audit_log(limit)
        if r.get("trace_id") == trace_id or trace_id in r.get("child_traces", [])
    ]
