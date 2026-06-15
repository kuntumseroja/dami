"""Hard source-traceability gate (Sprint 2.5, FR-1 AC-1.3)."""
from app.domain.models import NotaSection
from app.use_cases.grounding import (
    LOW_CONFIDENCE_PLACEHOLDER,
    enforce_grounding,
)

VALID = {"doc_1#0", "doc_1#1", "doc_2#0"}


def _desc(heading, content, sources):
    return NotaSection(heading=heading, kind="descriptive", content=content, sources=sources)


def test_grounded_section_passes_and_keeps_resolvable_refs():
    s = _desc("Latar Belakang", "PTPN III mengajukan divestasi.", ["doc_1#0", "bogus#9"])
    out, report = enforce_grounding([s], VALID)
    assert out[0].grounded is True
    assert out[0].content == "PTPN III mengajukan divestasi."
    assert out[0].sources == ["doc_1#0"]          # hallucinated ref stripped
    assert "bogus#9" in report["stripped_refs"]
    assert report["passed"] == 1 and report["suppressed"] == []


def test_ungrounded_content_is_suppressed():
    # content with only non-resolvable citations → must not be rendered as grounded
    s = _desc("Ringkasan", "Nilai transaksi Rp999 triliun.", ["ghost#1"])
    out, report = enforce_grounding([s], VALID)
    assert out[0].grounded is False
    assert out[0].content == LOW_CONFIDENCE_PLACEHOLDER
    assert out[0].sources == []
    assert "Ringkasan" in report["suppressed"]


def test_no_citation_content_is_suppressed():
    s = _desc("Data Pendukung", "Beberapa angka tanpa sumber.", [])
    out, report = enforce_grounding([s], VALID)
    assert out[0].grounded is False
    assert report["suppressed"] == ["Data Pendukung"]


def test_data_unavailable_marker_passes_through():
    s = _desc("Dasar Hukum", "[DATA TIDAK TERSEDIA — mohon dilengkapi]", [])
    out, report = enforce_grounding([s], VALID)
    assert out[0].content.startswith("[DATA TIDAK TERSEDIA")
    assert out[0].heading not in report["suppressed"]
    assert report["checked"] == 0     # honest non-claim is not a grounding check


def test_judgment_sections_untouched():
    s = NotaSection(heading="Rekomendasi", kind="judgment", content="", sources=[])
    out, _ = enforce_grounding([s], VALID)
    assert out[0] == s


def test_every_rendered_descriptive_section_is_grounded_or_flagged():
    """The FR-1 invariant: after the gate, no descriptive section has content
    that is neither grounded nor an explicit insufficient-source marker."""
    sections = [
        _desc("A", "Grounded claim.", ["doc_2#0"]),
        _desc("B", "Ungrounded claim.", ["nope#1"]),
        _desc("C", "[DATA TIDAK TERSEDIA — mohon dilengkapi]", []),
    ]
    out, _ = enforce_grounding(sections, VALID)
    for s in out:
        if s.kind != "descriptive" or not s.content.strip():
            continue
        ok = s.grounded or s.content.startswith("[DATA TIDAK TERSEDIA") \
            or s.content == LOW_CONFIDENCE_PLACEHOLDER
        assert ok, f"{s.heading} rendered ungrounded content"
