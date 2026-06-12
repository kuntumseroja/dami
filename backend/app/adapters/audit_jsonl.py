"""Append-only JSONL AuditLog adapter.

Sprint 6 moves this to WORM-capable object storage; the port stays the same.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.domain.ports import AuditLog


def new_trace_id() -> str:
    return f"trc_{uuid.uuid4().hex[:16]}"


class JsonlAuditLog(AuditLog):
    def __init__(self, directory: str):
        self._dir = Path(directory)

    def log(self, event: str, trace_id: str, payload: dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "trace_id": trace_id,
            **payload,
        }
        day_file = self._dir / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"
        with day_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def read(self, limit: int = 200) -> list[dict]:
        if not self._dir.exists():
            return []
        records: list[dict] = []
        for day_file in sorted(self._dir.glob("*.jsonl"), reverse=True):
            with day_file.open(encoding="utf-8") as fh:
                records.extend(json.loads(line) for line in fh if line.strip())
            if len(records) >= limit:
                break
        records.sort(key=lambda r: r["ts"], reverse=True)
        return records[:limit]
