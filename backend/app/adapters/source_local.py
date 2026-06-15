"""Local-folder DocumentSource — dev/test twin for the Graph adapter.

Mirrors a OneDrive/SharePoint document library with a directory on disk so
the ingestion-from-source path can be exercised without Microsoft 365.
"""
from pathlib import Path

from app.domain.ports import DocumentSource, SourceItem


class LocalFolderSource(DocumentSource):
    def __init__(self, root: str):
        self._root = Path(root)

    async def list_items(self, folder: str | None = None) -> list[SourceItem]:
        base = self._root / folder if folder else self._root
        if not base.exists():
            return []
        return [
            SourceItem(
                external_id=str(p.relative_to(self._root)),
                name=p.name,
                path=str(p.relative_to(self._root)),
                size_bytes=p.stat().st_size,
            )
            for p in sorted(base.rglob("*"))
            if p.is_file()
        ]

    async def fetch(self, external_id: str) -> tuple[bytes, SourceItem]:
        p = self._root / external_id
        data = p.read_bytes()
        return data, SourceItem(
            external_id=external_id, name=p.name, path=external_id,
            size_bytes=len(data),
        )
