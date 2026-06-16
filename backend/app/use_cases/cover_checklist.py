"""Cover-sheet completeness checklist — derived from the documents actually
attached to a case, not a static field on a PDF.

Deterministic (rules decide, AI does not): each required collateral item is
matched against the case's documents by type + filename pattern. The result
drives the cover sheet's "kelengkapan / completeness" status so it always
reflects reality as documents arrive or are removed.
"""
import re

from pydantic import BaseModel

from app.domain.ports import CaseRepository


class ChecklistItem(BaseModel):
    key: str
    label: str
    required: bool
    present: bool
    matched: list[str]


class ChecklistReport(BaseModel):
    case_id: str
    items: list[ChecklistItem]
    complete: bool                 # all REQUIRED items present
    missing: list[str]             # labels of required items not yet attached


# (key, label, required, regex patterns matched against "<doc_type> <title>")
_SPEC = [
    ("cover_sheet", "Lembar pengantar / Cover sheet", True,
     [r"cover_sheet", r"lembar.?pengantar"]),
    ("request", "Surat permohonan / Nota Dinas", True,
     [r"surat.?permohonan", r"nota.?dinas", r"permohonan"]),
    ("supporting", "Dokumen pendukung (FS / valuasi / term sheet)", True,
     [r"feasibility", r"valuasi", r"tesis", r"term.?sheet", r"ringkasan", r"proyek"]),
    ("legal", "Kajian hukum / Legal review", False,
     [r"kajian.?hukum", r"legal"]),
    ("dekom", "Surat rekomendasi Dewan Komisaris", False,
     [r"rekomendasi", r"dekom", r"komisaris"]),
]


async def build_cover_checklist(
    case_id: str, *, repository: CaseRepository,
) -> ChecklistReport:
    docs = await repository.list_documents(case_id)
    blobs = []
    for d in docs:
        doc_type = d.doc_type.value if hasattr(d.doc_type, "value") else str(d.doc_type)
        blobs.append((f"{doc_type} {d.title}".lower(), d.title))

    items: list[ChecklistItem] = []
    for key, label, required, patterns in _SPEC:
        matched = [title for blob, title in blobs
                   if any(re.search(p, blob) for p in patterns)]
        items.append(ChecklistItem(key=key, label=label, required=required,
                                   present=bool(matched), matched=matched))

    missing = [it.label for it in items if it.required and not it.present]
    return ChecklistReport(case_id=case_id, items=items,
                           complete=not missing, missing=missing)
