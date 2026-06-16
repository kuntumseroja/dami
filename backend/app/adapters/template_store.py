"""NOTA template store (Sprint 3.1).

Templates are data: a YAML file per template under config/templates/. Adding a
template introduces a new NOTA structure with zero code change. A set of
built-in templates is the safety net when no config dir is present (tests /
DB-less dev), so the catalogue is never empty.
"""
from pathlib import Path

import yaml

from app.domain.models import NotaTemplate, TemplateSection
from app.domain.ports import TemplateStore

# Built-in catalogue (mirrors config/templates/*.yaml). Three template types so
# coverage can be measured across structures (AC-1.2). The default ("*") serves
# any SOP not explicitly mapped.
_BUILTINS: list[NotaTemplate] = [
    NotaTemplate(
        id="nota-standard", name="NOTA Standar (default)", applies_to=["*"],
        sections=[
            TemplateSection(heading="Latar Belakang (Background)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Ringkasan Permohonan (Request Summary)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Dasar Hukum & Referensi (Legal Basis & References)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Kronologi & Status (Chronology & Status)", kind="descriptive", mandatory=False),
            TemplateSection(heading="Data Pendukung (Supporting Data)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Analisis & Pertimbangan (Analysis & Considerations)", kind="judgment", mandatory=True),
            TemplateSection(heading="Rekomendasi (Recommendation)", kind="judgment", mandatory=True),
        ],
    ),
    NotaTemplate(
        id="nota-strategic", name="NOTA Aksi Strategis (M&A / investasi / pasar modal)",
        applies_to=["SOP-DAM-002", "SOP-DAM-004", "SOP-DAM-005", "SOP-DAM-006", "SOP-DAM-008"],
        sections=[
            TemplateSection(heading="Latar Belakang (Background)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Ringkasan Permohonan (Request Summary)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Dasar Hukum & Referensi (Legal Basis & References)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Kajian Kelayakan & Finansial (Commercial & Financial Feasibility)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Struktur Transaksi (Transaction Structure)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Manajemen Risiko & Kepatuhan (Risk & Compliance / ESG)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Analisis & Pertimbangan (Analysis & Considerations)", kind="judgment", mandatory=True),
            TemplateSection(heading="Rekomendasi (Recommendation)", kind="judgment", mandatory=True),
        ],
    ),
    NotaTemplate(
        id="cover-sheet", name="Lembar Pengantar / Cover Sheet", applies_to=[],
        sections=[
            TemplateSection(heading="Identitas Permohonan (Request Identity)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Ringkasan Aksi Korporasi (Action Summary)", kind="descriptive", mandatory=True),
            TemplateSection(heading="Kelengkapan & Klasifikasi (Completeness & Classification)", kind="descriptive", mandatory=True),
        ],
    ),
]


class YamlTemplateStore(TemplateStore):
    def __init__(self, config_dir: str | None = None):
        self._templates: dict[str, NotaTemplate] = {}
        loaded = self._load_dir(config_dir) if config_dir else []
        for t in (loaded or _BUILTINS):
            self._templates[t.id] = t

    @staticmethod
    def _load_dir(config_dir: str) -> list[NotaTemplate]:
        path = Path(config_dir)
        if not path.is_dir():
            return []
        out: list[NotaTemplate] = []
        for f in sorted(path.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if data:
                out.append(NotaTemplate.model_validate(data))
        return out

    def get(self, template_id: str) -> NotaTemplate | None:
        return self._templates.get(template_id)

    def list(self) -> list[NotaTemplate]:
        return list(self._templates.values())

    def select(self, sop_id: str | None) -> NotaTemplate:
        if sop_id:
            for t in self._templates.values():
                if sop_id in t.applies_to:
                    return t
        for t in self._templates.values():
            if "*" in t.applies_to:
                return t
        # last resort: first non-cover-sheet template, else first
        return next((t for t in self._templates.values() if t.applies_to),
                    next(iter(self._templates.values())))
