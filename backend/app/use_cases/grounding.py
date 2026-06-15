"""Hard source-traceability gate (FR-1, AC-1.3 — Sprint 2.5).

The PRD's non-negotiable: the system must never render an unsourced generated
sentence. This gate runs at generation time over the drafted descriptive
sections and enforces, deterministically:

  * a descriptive section with content must cite at least one **resolvable**
    source ref (a ref that maps to a chunk actually retrieved for this case);
  * source refs that don't resolve (hallucinated citations) are stripped;
  * if nothing resolvable remains, the content is **suppressed** and replaced
    with a low-confidence / manual-input placeholder — it is never shown as if
    it were grounded;
  * the explicit insufficient-source marker ("[DATA TIDAK TERSEDIA …]") is an
    honest non-claim and passes through unchanged.

Judgment sections are out of scope (they are human-authored and empty).
This is deterministic — no extra model call — so it cannot itself hallucinate.
"""
from app.domain.models import NotaSection

DATA_UNAVAILABLE_MARKER = "[DATA TIDAK TERSEDIA"
LOW_CONFIDENCE_PLACEHOLDER = (
    "[Kepercayaan rendah — mohon dilengkapi secara manual / "
    "Low confidence — manual input required]"
)


def enforce_grounding(
    sections: list[NotaSection], valid_refs: set[str]
) -> tuple[list[NotaSection], dict]:
    """Apply the gate. Returns (gated_sections, report).

    `valid_refs` is the set of chunk refs (document_id#index) that were
    actually retrieved for this case — the only refs a section may legitimately
    cite.
    """
    report = {"checked": 0, "passed": 0, "suppressed": [], "stripped_refs": []}
    out: list[NotaSection] = []

    for s in sections:
        if s.kind != "descriptive":
            out.append(s)
            continue
        content = s.content.strip()
        if not content or DATA_UNAVAILABLE_MARKER in content:
            # empty or honest "data unavailable" — not an ungrounded claim
            out.append(s)
            continue

        report["checked"] += 1
        resolvable = [r for r in s.sources if r in valid_refs]
        unresolved = [r for r in s.sources if r not in valid_refs]
        if unresolved:
            report["stripped_refs"].extend(unresolved)

        if resolvable:
            report["passed"] += 1
            out.append(s.model_copy(update={"sources": resolvable, "grounded": True}))
        else:
            # content with no resolvable source — suppress, never render as grounded
            report["suppressed"].append(s.heading)
            out.append(s.model_copy(update={
                "content": LOW_CONFIDENCE_PLACEHOLDER, "sources": [], "grounded": False,
            }))

    return out, report
