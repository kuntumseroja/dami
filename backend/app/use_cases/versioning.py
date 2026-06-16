"""Document version control (Sprint 3.8, FR-3).

Full version history (author / timestamp / change summary), checkout/check-in
locking to prevent concurrent-edit conflicts, diffs between versions, and
immutability once the case is submitted to the senior review queue. A master-
document edit surfaces dependents that may now be out of sync (propagation).
"""
import difflib

from app.domain.models import (
    DocumentImmutable,
    DocumentLocked,
    DocumentVersion,
    NotLockHolder,
    new_trace_id,
)
from app.domain.ports import AuditLog, CaseRepository

_VER = "document_version"
_LOCK = "document_lock"


async def case_immutable(case_id: str, *, repository: CaseRepository) -> bool:
    """Frozen once submitted to the review queue (3.6 review_submission exists)."""
    return bool(await repository.list_artefacts(case_id, "review_submission"))


async def _versions(case_id: str, document_id: str, repository: CaseRepository) -> list[dict]:
    rows = await repository.list_artefacts(case_id, _VER)
    out = [r.get("payload", r) for r in rows]
    return sorted([v for v in out if v["document_id"] == document_id],
                  key=lambda v: v["version"])


async def list_versions(case_id: str, document_id: str, *,
                        repository: CaseRepository) -> list[dict]:
    return await _versions(case_id, document_id, repository)


async def current_lock(case_id: str, document_id: str, *,
                       repository: CaseRepository) -> str | None:
    rows = await repository.list_artefacts(case_id, _LOCK)
    holder = None
    for r in rows:
        p = r.get("payload", r)
        if p["document_id"] == document_id:
            holder = p.get("locked_by")        # latest wins; None = released
    return holder


async def checkout(case_id: str, document_id: str, *, user: str,
                   repository: CaseRepository, audit: AuditLog) -> None:
    if await case_immutable(case_id, repository=repository):
        raise DocumentImmutable("case submitted to review — documents are frozen")
    holder = await current_lock(case_id, document_id, repository=repository)
    if holder and holder != user:
        raise DocumentLocked(f"checked out by {holder}")
    await repository.save_artefact(case_id, _LOCK,
                                   {"document_id": document_id, "locked_by": user})
    audit.log("document.checkout", new_trace_id(),
              {"case_id": case_id, "document_id": document_id, "actor": user})


async def checkin(case_id: str, document_id: str, *, user: str, content: str,
                  change_summary: str, repository: CaseRepository,
                  audit: AuditLog) -> DocumentVersion:
    if await case_immutable(case_id, repository=repository):
        raise DocumentImmutable("case submitted to review — documents are frozen")
    holder = await current_lock(case_id, document_id, repository=repository)
    if holder != user:
        raise NotLockHolder(f"check-in requires holding the lock (held by {holder})")
    versions = await _versions(case_id, document_id, repository)
    nxt = (versions[-1]["version"] + 1) if versions else 1
    ver = DocumentVersion(document_id=document_id, version=nxt, content=content,
                          author=user, change_summary=change_summary)
    await repository.save_artefact(case_id, _VER, ver.model_dump(mode="json"))
    await repository.save_artefact(case_id, _LOCK,
                                   {"document_id": document_id, "locked_by": None})
    audit.log("document.version", new_trace_id(),
              {"case_id": case_id, "document_id": document_id, "version": nxt,
               "author": user, "change_summary": change_summary})
    return ver


async def diff_versions(case_id: str, document_id: str, a: int, b: int, *,
                        repository: CaseRepository) -> str:
    versions = {v["version"]: v for v in await _versions(case_id, document_id, repository)}
    if a not in versions or b not in versions:
        raise KeyError("version not found")
    left, right = versions[a]["content"].splitlines(), versions[b]["content"].splitlines()
    return "\n".join(difflib.unified_diff(
        left, right, fromfile=f"v{a}", tofile=f"v{b}", lineterm=""))


async def propagation_status(case_id: str, document_id: str, *,
                             repository: CaseRepository) -> dict:
    """A master edit (version > 1) may leave derived artefacts out of sync."""
    versions = await _versions(case_id, document_id, repository)
    doc = await repository.get_document(document_id)
    is_master = bool(doc and doc.is_master)
    derived_kinds = ("nota_draft", "consistency_report", "reconciliation_report")
    dependents = []
    for k in derived_kinds:
        if await repository.list_artefacts(case_id, k):
            dependents.append(k)
    stale = is_master and len(versions) > 1 and bool(dependents)
    return {"document_id": document_id, "is_master": is_master,
            "versions": len(versions), "dependents": dependents,
            "dependents_possibly_stale": stale}
