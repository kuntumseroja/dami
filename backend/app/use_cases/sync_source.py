"""Ingest documents from an external repository (OneDrive / SharePoint).

Lists items in a source folder and runs each through the standard ingestion
pipeline, so source-pulled documents get the same grounding-ready chunking,
entity scoping, classification, and audit trail as uploaded ones.
"""
from app.domain.models import (
    DEFAULT_ENTITY,
    BPIEntity,
    DataClassification,
    DocumentType,
    new_trace_id,
)
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    DocumentParser,
    DocumentSource,
    Embedder,
    ObjectStorage,
    VectorStore,
)
from app.use_cases.ingest_document import ingest_document


async def sync_from_source(
    *,
    source: DocumentSource,
    folder: str | None,
    doc_type: DocumentType,
    case_id: str | None,
    entity: BPIEntity = DEFAULT_ENTITY,
    classification: DataClassification = DataClassification.INTERNAL,
    embedder: Embedder,
    vectors: VectorStore,
    storage: ObjectStorage,
    repository: CaseRepository,
    audit: AuditLog,
    parser: DocumentParser | None = None,
) -> dict:
    trace_id = new_trace_id()
    items = await source.list_items(folder)
    results = []
    for item in items:
        data, meta = await source.fetch(item.external_id)
        res = await ingest_document(
            meta.name, data, doc_type, case_id,
            embedder=embedder, vectors=vectors, storage=storage,
            repository=repository, audit=audit, parser=parser,
            entity=entity, classification=classification,
        )
        results.append({"source_id": item.external_id, "name": meta.name,
                        "document_id": res.document_id, "chunks": res.chunks_indexed})

    audit.log(
        "source.synced",
        trace_id,
        {"folder": folder, "entity": entity.value, "doc_type": doc_type.value,
         "items_ingested": len(results)},
    )
    return {"folder": folder, "ingested": len(results), "documents": results,
            "trace_id": trace_id}
