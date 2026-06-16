"""Judgment-section contamination zero-gate (Sprint 3.3, FR-1 AC-1.4).

Judgment sections (analysis, recommendation) are human-only by design. This
gate guarantees no AI-authored text ever lands in a judgment section: any
judgment section that carries content not explicitly authored by a human is
blanked and recorded as a Sev-1 contamination incident. Deterministic — no
model call — so the gate itself cannot contaminate.
"""
from app.domain.models import NotaSection

HUMAN_AUTHORSHIP_PROMPT = (
    "Bagian pertimbangan/rekomendasi wajib ditulis oleh reviewer manusia. / "
    "Analysis & recommendation must be authored by a human reviewer."
)


def scan_contamination(sections: list[NotaSection]) -> list[str]:
    """Headings of judgment sections containing non-human-authored content."""
    return [
        s.heading for s in sections
        if s.kind == "judgment" and s.content.strip() and s.authored_by != "human"
    ]


def enforce_judgment_purity(
    sections: list[NotaSection],
) -> tuple[list[NotaSection], list[str]]:
    """Blank any contaminated judgment section. Returns (clean, violations)."""
    violations: list[str] = []
    out: list[NotaSection] = []
    for s in sections:
        if s.kind == "judgment" and s.content.strip() and s.authored_by != "human":
            violations.append(s.heading)
            out.append(s.model_copy(update={"content": "", "authored_by": None}))
        else:
            out.append(s)
    return out, violations
