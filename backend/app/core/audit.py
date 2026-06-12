"""Append-only audit trail.

Every AI invocation, rule evaluation, and document mutation is recorded as a
JSON line. This is the auditability guarantee of the secure AI sandbox
(requirement E) and the personal-liability shield (requirement F): for any
output the platform can show exactly which inputs, sources, and rules
produced it.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings


def new_trace_id() -> str:
    return f"trc_{uuid.uuid4().hex[:16]}"


def audit_log(event: str, trace_id: str, payload: dict) -> None:
    settings = get_settings()
    audit_dir = Path(settings.dam_audit_log_path)
    audit_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "trace_id": trace_id,
        **payload,
    }
    day_file = audit_dir / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"
    with day_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def read_audit_log(limit: int = 200) -> list[dict]:
    settings = get_settings()
    audit_dir = Path(settings.dam_audit_log_path)
    if not audit_dir.exists():
        return []
    records: list[dict] = []
    for day_file in sorted(audit_dir.glob("*.jsonl"), reverse=True):
        with day_file.open(encoding="utf-8") as fh:
            records.extend(json.loads(line) for line in fh if line.strip())
        if len(records) >= limit:
            break
    records.sort(key=lambda r: r["ts"], reverse=True)
    return records[:limit]
