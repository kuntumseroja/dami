"""Judgment-section contamination zero-gate (Sprint 3.3, FR-1 AC-1.4)."""
from app.domain.models import NotaSection
from app.use_cases.contamination import (
    enforce_judgment_purity,
    scan_contamination,
)


def _pkg(judgment_content="", authored_by=None):
    return [
        NotaSection(heading="Latar Belakang", kind="descriptive",
                    content="Fakta tersumber.", authored_by="ai"),
        NotaSection(heading="Rekomendasi", kind="judgment",
                    content=judgment_content, authored_by=authored_by),
    ]


def test_clean_packages_have_zero_contamination():
    # 5 normal drafts: judgment sections empty → no contamination (AC-1.4)
    for _ in range(5):
        sections, violations = enforce_judgment_purity(_pkg())
        assert violations == []
        assert scan_contamination(sections) == []


def test_ai_authored_judgment_is_blanked_and_flagged():
    sections, violations = enforce_judgment_purity(
        _pkg(judgment_content="AI menyarankan menyetujui.", authored_by="ai"))
    assert violations == ["Rekomendasi"]
    judgment = next(s for s in sections if s.kind == "judgment")
    assert judgment.content == ""              # AI text removed
    assert judgment.authored_by is None
    assert scan_contamination(sections) == []  # clean after the gate


def test_human_authored_judgment_is_allowed():
    sections, violations = enforce_judgment_purity(
        _pkg(judgment_content="Analisis reviewer manusia.", authored_by="human"))
    assert violations == []
    judgment = next(s for s in sections if s.kind == "judgment")
    assert judgment.content == "Analisis reviewer manusia."   # preserved


def test_descriptive_ai_content_untouched():
    sections, violations = enforce_judgment_purity(_pkg())
    desc = next(s for s in sections if s.kind == "descriptive")
    assert desc.content == "Fakta tersumber." and desc.authored_by == "ai"
    assert violations == []
