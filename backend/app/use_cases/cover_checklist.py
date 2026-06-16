"""Cover-sheet completeness checklist — derived from the documents actually
attached to a case, with the required-collateral set varying by SOP.

Deterministic (rules decide, AI does not). The applicable SOP is taken from the
case's stored routing decision (set at the eligibility-check stage); each SOP
declares which collateral is required / recommended / not applicable. e.g. a
low-risk lease needs no feasibility study, while an M&A needs a legal review and
a Dewan Komisaris recommendation. Until a case has been routed, a conservative
default profile applies.
"""
import re

from pydantic import BaseModel

from app.domain.ports import CaseRepository

REQUIRED = "required"
RECOMMENDED = "recommended"
NA = "not_applicable"


class ChecklistItem(BaseModel):
    key: str
    label: str
    requirement: str          # required | recommended
    required: bool            # convenience: requirement == "required"
    present: bool
    matched: list[str]


class ChecklistReport(BaseModel):
    case_id: str
    sop: str | None           # SOP id the profile was selected for (None = default)
    items: list[ChecklistItem]
    complete: bool            # all REQUIRED items present
    missing: list[str]        # labels of required items not yet attached


# Collateral catalogue: key → (label, regex patterns matched against
# "<doc_type> <title>").
_CATALOGUE = {
    "cover_sheet": ("Lembar pengantar / Cover sheet",
                    [r"cover_sheet", r"lembar.?pengantar"]),
    "request": ("Surat permohonan / Nota Dinas",
                [r"surat.?permohonan", r"nota.?dinas", r"permohonan"]),
    "supporting": ("Dokumen pendukung (FS / valuasi / term sheet)",
                   [r"feasibility", r"valuasi", r"tesis", r"term.?sheet",
                    r"ringkasan", r"proyek", r"prospektus"]),
    "legal": ("Kajian hukum / Legal review", [r"kajian.?hukum", r"legal"]),
    "dekom": ("Surat rekomendasi Dewan Komisaris",
              [r"rekomendasi", r"dekom", r"komisaris"]),
}

# Per-SOP required-collateral profiles. Omitted keys fall back to the default.
_DEFAULT_PROFILE = {"cover_sheet": REQUIRED, "request": REQUIRED,
                    "supporting": REQUIRED, "legal": RECOMMENDED, "dekom": RECOMMENDED}

_PROFILES = {
    # Asset disposal — independent valuation matters; legal/Dekom advisory.
    "SOP-DAM-001": {"supporting": REQUIRED, "legal": RECOMMENDED, "dekom": RECOMMENDED},
    # Acquisition / investment — FS + legal required.
    "SOP-DAM-002": {"supporting": REQUIRED, "legal": REQUIRED, "dekom": RECOMMENDED},
    # Lease / utilization — low risk: no FS, no Dekom.
    "SOP-DAM-003": {"supporting": NA, "legal": RECOMMENDED, "dekom": NA},
    # Debt issuance — term sheet + legal + Dekom.
    "SOP-DAM-004": {"supporting": REQUIRED, "legal": REQUIRED, "dekom": REQUIRED},
    # M&A / spin-off / restructuring — full pack: FS + legal + Dekom.
    "SOP-DAM-005": {"supporting": REQUIRED, "legal": REQUIRED, "dekom": REQUIRED},
    # Capex / PSN — FS + Dekom; legal advisory.
    "SOP-DAM-006": {"supporting": REQUIRED, "legal": RECOMMENDED, "dekom": REQUIRED},
    # Asset write-off — light: supporting advisory, no Dekom.
    "SOP-DAM-007": {"supporting": RECOMMENDED, "legal": RECOMMENDED, "dekom": NA},
    # Equity capital markets (IPO / rights issue) — prospectus + legal + Dekom.
    "SOP-DAM-008": {"supporting": REQUIRED, "legal": REQUIRED, "dekom": REQUIRED},
    # Dissolution / liquidation — legal + Dekom required.
    "SOP-DAM-009": {"supporting": RECOMMENDED, "legal": REQUIRED, "dekom": REQUIRED},
}

_SOP_RE = re.compile(r"SOP-DAM-\d+")


def profile_for_sop(sop_id: str | None) -> dict[str, str]:
    overrides = _PROFILES.get(sop_id or "", {})
    return {**_DEFAULT_PROFILE, **overrides}


async def _resolve_sop(case_id: str, repository: CaseRepository) -> str | None:
    """Most recent routing decision's SOP id, if the case has been routed."""
    artefacts = await repository.list_artefacts(case_id, "routing_decision")
    if not artefacts:
        return None
    payload = artefacts[-1].get("payload", artefacts[-1])
    match = _SOP_RE.search(payload.get("applicable_sop", "") or "")
    return match.group(0) if match else None


async def build_cover_checklist(
    case_id: str, *, repository: CaseRepository, sop: str | None = None,
) -> ChecklistReport:
    sop_id = sop or await _resolve_sop(case_id, repository)
    profile = profile_for_sop(sop_id)

    docs = await repository.list_documents(case_id)
    blobs = []
    for d in docs:
        doc_type = d.doc_type.value if hasattr(d.doc_type, "value") else str(d.doc_type)
        blobs.append(f"{doc_type} {d.title}".lower())

    items: list[ChecklistItem] = []
    for key, (label, patterns) in _CATALOGUE.items():
        requirement = profile.get(key, RECOMMENDED)
        if requirement == NA:
            continue                                   # not applicable for this SOP
        matched = [d.title for d, blob in zip(docs, blobs)
                   if any(re.search(p, blob) for p in patterns)]
        items.append(ChecklistItem(
            key=key, label=label, requirement=requirement,
            required=requirement == REQUIRED,
            present=bool(matched), matched=matched,
        ))

    missing = [it.label for it in items if it.required and not it.present]
    return ChecklistReport(case_id=case_id, sop=sop_id, items=items,
                           complete=not missing, missing=missing)
