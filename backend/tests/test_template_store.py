"""NOTA template store + mandatory-field enforcement (Sprint 3.1, addendum A3/A5)."""
from app.adapters.template_store import YamlTemplateStore
from app.domain.models import NotaSection
from app.use_cases.draft_nota import mandatory_status


def _store():
    # No config dir → built-in catalogue (3 template types).
    return YamlTemplateStore(config_dir=None)


def test_builtin_catalogue_has_three_template_types():
    ids = {t.id for t in _store().list()}
    assert {"nota-standard", "nota-strategic", "cover-sheet"} <= ids


def test_cover_sheet_is_first_class_template():
    cover = _store().get("cover-sheet")
    assert cover is not None and cover.applies_to == []   # selected by id, not SOP


def test_select_by_sop_then_default():
    s = _store()
    assert s.select("SOP-DAM-005").id == "nota-strategic"   # M&A → strategic
    assert s.select("SOP-DAM-003").id == "nota-standard"    # lease → default ("*")
    assert s.select(None).id == "nota-standard"             # unknown → default


def test_loads_from_config_dir_when_present():
    from pathlib import Path
    cfg = Path(__file__).resolve().parents[2] / "config" / "templates"
    if cfg.is_dir():
        ids = {t.id for t in YamlTemplateStore(str(cfg)).list()}
        assert "nota-standard" in ids


def test_mandatory_missing_flags_ungrounded_required_section():
    template = _store().get("nota-standard")
    sections = [
        NotaSection(heading="Latar Belakang (Background)", kind="descriptive",
                    content="Grounded.", sources=["d#0"], grounded=True),
        NotaSection(heading="Ringkasan Permohonan (Request Summary)", kind="descriptive",
                    content="[DATA TIDAK TERSEDIA — lengkapi]", sources=[], grounded=True),
        NotaSection(heading="Dasar Hukum & Referensi (Legal Basis & References)",
                    kind="descriptive", content="", sources=[], grounded=False),
        # Data Pendukung mandatory but absent entirely
        NotaSection(heading="Kronologi & Status (Chronology & Status)", kind="descriptive",
                    content="", sources=[], grounded=False),  # optional → not blocking
    ]
    missing, complete = mandatory_status(template, sections)
    assert complete is False
    assert "Ringkasan Permohonan (Request Summary)" in missing   # data-unavailable
    assert "Dasar Hukum & Referensi (Legal Basis & References)" in missing  # suppressed
    assert "Data Pendukung (Supporting Data)" in missing          # absent
    assert "Kronologi & Status (Chronology & Status)" not in missing  # optional
    assert "Latar Belakang (Background)" not in missing           # grounded ok


def test_complete_when_all_mandatory_grounded():
    template = _store().get("cover-sheet")
    sections = [NotaSection(heading=s.heading, kind="descriptive", content="ok",
                            sources=["d#0"], grounded=True)
                for s in template.descriptive]
    missing, complete = mandatory_status(template, sections)
    assert complete is True and missing == []
