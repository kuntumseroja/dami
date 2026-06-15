"""DocumentSource adapter for Microsoft 365 — OneDrive and SharePoint.

Both OneDrive and SharePoint document libraries are exposed by Microsoft
Graph as *drives*, so one adapter covers both: point it at a user's OneDrive
drive (current DAM state) or a SharePoint site's document library (the
governed target). Authentication is app-only (client credentials) so no
governance content leaves the DAM-approved boundary except to Microsoft 365,
which is already DAM's system of record.

Network egress to Graph must be allow-listed in the deployment's networking
policy; under an edge/air-gapped profile this source is simply not attached.
"""
from __future__ import annotations

import httpx

from app.domain.ports import DocumentSource, SourceItem

GRAPH = "https://graph.microsoft.com/v1.0"
LOGIN = "https://login.microsoftonline.com"


class GraphDocumentSource(DocumentSource):
    def __init__(self, *, tenant_id: str, client_id: str, client_secret: str,
                 drive_id: str):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._drive_id = drive_id   # OneDrive drive id or SharePoint library drive id

    async def _token(self) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{LOGIN}/{self._tenant_id}/oauth2/v2.0/token",
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def list_items(self, folder: str | None = None) -> list[SourceItem]:
        token = await self._token()
        path = f"/root:/{folder}:/children" if folder else "/root/children"
        url = f"{GRAPH}/drives/{self._drive_id}{path}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            items = resp.json().get("value", [])
        return [
            SourceItem(
                external_id=it["id"],
                name=it["name"],
                path=(it.get("parentReference", {}).get("path", "") + "/" + it["name"]),
                modified=it.get("lastModifiedDateTime"),
                size_bytes=it.get("size"),
            )
            for it in items
            if "file" in it  # skip folders
        ]

    async def fetch(self, external_id: str) -> tuple[bytes, SourceItem]:
        token = await self._token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            meta = await client.get(
                f"{GRAPH}/drives/{self._drive_id}/items/{external_id}", headers=headers)
            meta.raise_for_status()
            m = meta.json()
            content = await client.get(
                f"{GRAPH}/drives/{self._drive_id}/items/{external_id}/content",
                headers=headers)
            content.raise_for_status()
        item = SourceItem(
            external_id=m["id"], name=m["name"],
            path=m.get("parentReference", {}).get("path", "") + "/" + m["name"],
            modified=m.get("lastModifiedDateTime"), size_bytes=m.get("size"),
        )
        return content.content, item
