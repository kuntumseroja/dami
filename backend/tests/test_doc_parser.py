"""Document-understanding pipeline (Sprint 2.10): native + OCR escalation.

The real Docling/Tesseract backends are optional heavy deps; here we use stub
parsers as in-memory twins so the escalation logic is tested without them.
"""
from app.adapters.doc_parser import (
    MIN_NATIVE_CHARS,
    LayeredDocumentParser,
    NativeTextParser,
    ParserUnavailable,
)
from app.domain.models import ParsedDocument
from app.domain.ports import DocumentParser


class _Stub(DocumentParser):
    def __init__(self, text, method, available=True):
        self._text, self._method, self._available = text, method, available

    def parse(self, filename, data):
        if not self._available:
            raise ParserUnavailable(self._method)
        return ParsedDocument(text=self._text, char_count=len(self._text),
                              method=self._method,
                              ocr_used=self._method not in ("native", "empty"))


def test_native_extracts_plaintext():
    out = NativeTextParser().parse("note.txt", b"Permohonan sewa aset Rp500 juta")
    assert out.method == "native"
    assert "Rp500" in out.text
    assert out.ocr_used is False


def test_native_empty_when_no_text():
    out = NativeTextParser().parse("blank.txt", b"")
    assert out.method == "empty"
    assert out.char_count == 0


def test_layered_keeps_native_when_text_is_rich():
    rich = "x" * (MIN_NATIVE_CHARS + 10)
    native = _Stub(rich, "native")
    layered = LayeredDocumentParser(native, [_Stub("OCR TEXT", "docling")])
    out = layered.parse("doc.pdf", b"%PDF")
    assert out.method == "native"          # no escalation — native was enough
    assert out.ocr_used is False


def test_layered_escalates_to_ocr_for_scanned_doc():
    native = _Stub("", "empty")            # scanned PDF → no native text
    ocr_text = "Hasil OCR dokumen pindaian " * 5
    layered = LayeredDocumentParser(native, [_Stub(ocr_text, "docling")])
    out = layered.parse("scan.pdf", b"%PDF")
    assert out.method == "docling"
    assert out.ocr_used is True
    assert out.char_count > MIN_NATIVE_CHARS


def test_layered_falls_through_unavailable_backend():
    native = _Stub("", "empty")
    layered = LayeredDocumentParser(native, [
        _Stub("never", "docling", available=False),   # docling not installed
        _Stub("Tesseract OCR output here aplenty", "tesseract"),
    ])
    out = layered.parse("scan.pdf", b"%PDF")
    assert out.method == "tesseract"       # skipped docling, used fallback


def test_layered_returns_best_effort_when_no_ocr_available():
    native = _Stub("tiny", "native")
    layered = LayeredDocumentParser(native, [_Stub("x", "docling", available=False)])
    out = layered.parse("scan.pdf", b"%PDF")
    assert out.method == "native"          # nothing better available; no crash
