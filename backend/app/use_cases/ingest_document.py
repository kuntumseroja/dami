"""Document ingestion: store original → parse → chunk → embed → index → register.

Supports PDF, DOCX, and plain-text submissions, SOPs, templates, and
historical NOTAs.
"""
import uuid

from app.domain.models import (
    DEFAULT_ENTITY,
    BPIEntity,
    Chunk,
    DataClassification,
    DocumentType,
    GovernanceDocument,
    IngestionResult,
    new_trace_id,
)
from app.adapters.doc_parser import NativeTextParser
from app.domain.ports import (
    AuditLog,
    CaseRepository,
    DocumentParser,
    Embedder,
    ObjectStorage,
    VectorStore,
)
from app.use_cases.chunking import semantic_chunks


def parse_bytes(filename: str, data: bytes) -> str:
    """Back-compat shim — native text extraction only."""
    return NativeTextParser().parse(filename, data).text


def chunk_text(content: str) -> list[str]:
    # Structure-aware chunking (Sprint 2.2): never splits a numbered clause.
    return semantic_chunks(content)


async def ingest_document(
    filename: str,
    data: bytes,
    doc_type: DocumentType,
    case_id: str | None,
    *,
    embedder: Embedder,
    vectors: VectorStore,
    storage: ObjectStorage,
    repository: CaseRepository,
    audit: AuditLog,
    parser: DocumentParser | None = None,
    entity: BPIEntity = DEFAULT_ENTITY,
    classification: DataClassification = DataClassification.INTERNAL,
) -> IngestionResult:
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    trace_id = new_trace_id()

    # 1. Preserve the original file (evidence trail), namespaced by entity.
    storage_key = f"{entity.value}/cases/{case_id or 'unassigned'}/{document_id}/{filename}"
    storage.put(storage_key, data)

    # 2. Document understanding (2.10): native text → OCR escalation if scanned.
    parser = parser or NativeTextParser()
    parsed = parser.parse(filename, data)
    pieces = chunk_text(parsed.text)
    chunks = [
        Chunk(
            document_id=document_id,
            case_id=case_id,
            entity=entity,
            doc_type=doc_type.value,
            chunk_index=i,
            content=piece,
        )
        for i, piece in enumerate(pieces)
    ]
    embeddings = await embedder.embed_texts([c.content for c in chunks])
    indexed = await vectors.replace_document(chunks, embeddings)

    # 3. Register document metadata (submissions are the master record).
    await repository.save_document(
        GovernanceDocument(
            id=document_id,
            case_id=case_id,
            entity=entity,
            classification=classification,
            doc_type=doc_type,
            title=filename,
            is_master=doc_type in (DocumentType.SUBMISSION, DocumentType.COVER_SHEET),
            storage_key=storage_key,
        )
    )

    audit.log(
        "document.ingested",
        trace_id,
        {
            "document_id": document_id,
            "filename": filename,
            "doc_type": doc_type.value,
            "case_id": case_id,
            "entity": entity.value,
            "classification": classification.value,
            "storage_key": storage_key,
            "chunks_indexed": indexed,
            "parse_method": parsed.method,
            "char_count": parsed.char_count,
            "ocr_used": parsed.ocr_used,
        },
    )
    return IngestionResult(document_id=document_id, chunks_indexed=indexed,
                           storage_key=storage_key)
