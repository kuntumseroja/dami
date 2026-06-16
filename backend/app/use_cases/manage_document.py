"""Document lifecycle use cases (preview + guarded removal).

Governance policy (hybrid): documents submitted by the SOE — the master
submission package — are immutable. They are the source of truth the whole
audit chain grounds against, so they cannot be removed or replaced here.
Supplementary material the analyst attaches afterwards CAN be removed before
the NOTA is finalized. Every removal is recorded in the audit trail.
"""
from app.domain.models import GovernanceDocument, new_trace_id
from app.domain.ports import AuditLog, CaseRepository, ObjectStorage, VectorStore


class DocumentLocked(Exception):
    """Raised when an immutable (master / SOE-submitted) document is removed."""


async def get_document_for_case(
    case_id: str, doc_id: str, *, repository: CaseRepository,
) -> GovernanceDocument:
    doc = await repository.get_document(doc_id)
    if doc is None or doc.case_id != case_id:
        raise KeyError(f"document {doc_id} not found in case {case_id}")
    return doc


async def remove_document(
    case_id: str, doc_id: str, *, actor: str, repository: CaseRepository,
    vectors: VectorStore, storage: ObjectStorage, audit: AuditLog,
) -> None:
    doc = await get_document_for_case(case_id, doc_id, repository=repository)
    if doc.is_master:
        raise DocumentLocked(
            "master submission documents are immutable and cannot be removed")

    trace_id = new_trace_id()
    chunks_removed = await vectors.delete_document(doc_id)
    if doc.storage_key:
        try:
            storage.delete(doc.storage_key)
        except Exception:  # noqa: BLE001 — object already gone is acceptable
            pass
    await repository.delete_document(doc_id)

    audit.log(
        "document.removed",
        trace_id,
        {
            "case_id": case_id,
            "document_id": doc_id,
            "title": doc.title,
            "actor": actor,
            "chunks_removed": chunks_removed,
        },
    )
