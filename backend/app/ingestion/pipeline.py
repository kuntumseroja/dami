"""Document ingestion pipeline: parse → chunk → embed → index → extract.

Supports PDF and DOCX submissions, SOPs, templates, and historical NOTAs.
Extraction of structured fields is delegated to the extraction agent.
"""
import io
import uuid

from app.core.audit import audit_log, new_trace_id
from app.models.schemas import DocumentType, IngestionResult
from app.rag.embeddings import embed_texts
from app.rag.vectorstore import Chunk, upsert_chunks

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150


def parse_bytes(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        import docx

        document = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)
    return data.decode("utf-8", errors="replace")


def chunk_text(content: str) -> list[str]:
    content = content.strip()
    if not content:
        return []
    chunks, start = [], 0
    while start < len(content):
        end = start + CHUNK_SIZE
        chunks.append(content[start:end])
        start = end - CHUNK_OVERLAP
    return chunks


async def ingest_document(
    filename: str,
    data: bytes,
    doc_type: DocumentType,
    case_id: str | None = None,
) -> IngestionResult:
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    trace_id = new_trace_id()

    content = parse_bytes(filename, data)
    pieces = chunk_text(content)
    chunks = [
        Chunk(
            document_id=document_id,
            case_id=case_id,
            doc_type=doc_type.value,
            chunk_index=i,
            content=piece,
        )
        for i, piece in enumerate(pieces)
    ]
    embeddings = await embed_texts([c.content for c in chunks])
    indexed = await upsert_chunks(chunks, embeddings) if chunks else 0

    audit_log(
        "document.ingested",
        trace_id,
        {
            "document_id": document_id,
            "filename": filename,
            "doc_type": doc_type.value,
            "case_id": case_id,
            "chunks_indexed": indexed,
        },
    )
    return IngestionResult(document_id=document_id, chunks_indexed=indexed)
