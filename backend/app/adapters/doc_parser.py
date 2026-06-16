"""Document-understanding adapters (Sprint 2.10).

A layered pipeline turns uploaded bytes into text for chunking/indexing:

  1. NativeTextParser   — pypdf / python-docx / plain-text. Fast, no extra deps.
  2. DoclingParser      — IBM Granite-Docling: layout-aware OCR for scanned or
                          image-heavy PDFs (tables, multi-column governance docs).
  3. TesseractParser    — open-source OCR fallback when Docling is unavailable.

The heavy OCR backends are imported lazily and are entirely optional: if their
libraries/binaries aren't installed they raise ParserUnavailable and the layered
parser simply skips them. So the default image stays lean (native-only) and OCR
is enabled per-deployment via DOC_PARSER=layered once docling/tesseract are
provisioned.
"""
import io

from app.domain.models import ParsedDocument
from app.domain.ports import DocumentParser

# Below this many extracted characters a PDF is treated as scanned/image-only
# and escalated to OCR.
MIN_NATIVE_CHARS = 96


class ParserUnavailable(RuntimeError):
    """An OCR backend's libraries or system binaries are not installed."""


class NativeTextParser(DocumentParser):
    def parse(self, filename: str, data: bytes) -> ParsedDocument:
        name = filename.lower()
        if name.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif name.endswith(".docx"):
            import docx

            text = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
        else:
            text = data.decode("utf-8", errors="replace")
        text = text.strip()
        return ParsedDocument(
            text=text, char_count=len(text),
            method="native" if text else "empty",
        )


class DoclingParser(DocumentParser):
    """IBM Granite-Docling layout-aware conversion. Lazy import."""

    def parse(self, filename: str, data: bytes) -> ParsedDocument:
        try:
            from docling.datamodel.base_models import DocumentStream
            from docling.document_converter import DocumentConverter
        except ImportError as exc:                       # not provisioned
            raise ParserUnavailable("docling not installed") from exc

        stream = DocumentStream(name=filename, stream=io.BytesIO(data))
        result = DocumentConverter().convert(stream)
        text = result.document.export_to_markdown().strip()
        return ParsedDocument(text=text, char_count=len(text),
                              method="docling", ocr_used=True)


class TesseractParser(DocumentParser):
    """Tesseract OCR fallback (PDF rasterized via pdf2image; images direct)."""

    def parse(self, filename: str, data: bytes) -> ParsedDocument:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise ParserUnavailable("pytesseract/Pillow not installed") from exc

        name = filename.lower()
        if name.endswith(".pdf"):
            try:
                from pdf2image import convert_from_bytes
            except ImportError as exc:
                raise ParserUnavailable("pdf2image not installed") from exc
            images = convert_from_bytes(data)
        else:
            images = [Image.open(io.BytesIO(data))]
        text = "\n".join(pytesseract.image_to_string(img) for img in images).strip()
        return ParsedDocument(text=text, char_count=len(text),
                              method="tesseract", ocr_used=True)


class LayeredDocumentParser(DocumentParser):
    """Native first; escalate to the OCR chain when native text is too thin."""

    def __init__(self, native: DocumentParser, ocr_chain: list[DocumentParser],
                 min_native_chars: int = MIN_NATIVE_CHARS):
        self._native = native
        self._ocr_chain = ocr_chain
        self._min = min_native_chars

    def parse(self, filename: str, data: bytes) -> ParsedDocument:
        best = self._native.parse(filename, data)
        if best.char_count >= self._min:
            return best
        # Scanned / image-only — try each OCR backend, keep the richest result.
        for ocr in self._ocr_chain:
            try:
                candidate = ocr.parse(filename, data)
            except ParserUnavailable:
                continue
            except Exception:  # noqa: BLE001 — a flaky OCR backend must not break ingest
                continue
            if candidate.char_count > best.char_count:
                best = candidate
        return best
