"""Filesystem ObjectStorage — tests and MinIO-less development."""
from pathlib import Path

from app.domain.ports import ObjectStorage


class LocalStorage(ObjectStorage):
    def __init__(self, root: str = "./data/objects"):
        self._root = Path(root)

    def put(self, key: str, data: bytes,
            content_type: str = "application/octet-stream") -> str:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return (self._root / key).read_bytes()
