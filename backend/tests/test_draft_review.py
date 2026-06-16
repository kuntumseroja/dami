"""Paragraph accept/edit/reject + AI disclaimer (Sprint 3.2, FR-1 AC-1.5, A4)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import AI_DISCLAIMER, NotaDraft, NotaSection, ParagraphAction
from app.use_cases.draft_review import (
    export_nota_markdown,
    get_action_state,
    record_paragraph_action,
)


async def _seed_draft(repo):
    draft = NotaDraft(
        case_id="c1", title="NOTA Uji", model="m", trace_id="t",
        sections=[
            NotaSection(heading="Latar Belakang", kind="descriptive", content="Asli A"),
            NotaSection(heading="Ringkasan", kind="descriptive", content="Asli B"),
            NotaSection(heading="Data Pendukung", kind="descriptive", content="Asli C"),
        ],
    )
    await repo.save_artefact("c1", "nota_draft", draft.model_dump(mode="json"))


def test_draft_carries_disclaimer():
    assert NotaDraft(case_id="c", title="t", model="m", trace_id="x",
                     sections=[]).disclaimer == AI_DISCLAIMER


@pytest.mark.asyncio
async def test_action_sequence_is_reconstructable():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _seed_draft(repo)
    seq = [
        ParagraphAction(case_id="c1", paragraph_id="Latar Belakang", action="accept", actor="u1"),
        ParagraphAction(case_id="c1", paragraph_id="Ringkasan", action="edit",
                        final_content="Teks revisi reviewer", actor="u2"),
        ParagraphAction(case_id="c1", paragraph_id="Ringkasan", action="accept", actor="u2"),  # later wins
        ParagraphAction(case_id="c1", paragraph_id="Data Pendukung", action="reject", actor="u1"),
    ]
    for a in seq:
        await record_paragraph_action(a, repository=repo, audit=audit)

    state = await get_action_state("c1", repository=repo)
    assert state["Latar Belakang"]["action"] == "accept"
    assert state["Ringkasan"]["action"] == "accept"        # latest action wins
    assert state["Data Pendukung"]["action"] == "reject"
    # full sequence preserved in the append-only artefact log
    raw = await repo.list_artefacts("c1", "draft_action")
    assert len(raw) == 4


@pytest.mark.asyncio
async def test_export_applies_actions_and_includes_disclaimer():
    repo, audit = InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")
    await _seed_draft(repo)
    await record_paragraph_action(
        ParagraphAction(case_id="c1", paragraph_id="Ringkasan", action="edit",
                        final_content="Teks revisi", actor="u1"),
        repository=repo, audit=audit)
    await record_paragraph_action(
        ParagraphAction(case_id="c1", paragraph_id="Data Pendukung", action="reject", actor="u1"),
        repository=repo, audit=audit)

    md = await export_nota_markdown("c1", repository=repo)
    assert AI_DISCLAIMER in md                  # disclaimer always present on export
    assert "Teks revisi" in md                  # edited content used
    assert "Asli B" not in md                   # original replaced by edit
    assert "Data Pendukung" not in md           # rejected section omitted
    assert "Asli A" in md                       # untouched section kept
