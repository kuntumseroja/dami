"""Paragraph-level draft review (Sprint 3.2, FR-1 AC-1.5).

Each accept / edit / reject is a discrete, tracked action stored as an artefact
and written to the audit trail — so the full review sequence is reconstructable
(who, when, which paragraph, action, final content). Export carries the
persistent AI-mistake disclaimer (addendum A4).
"""
from app.domain.models import (
    AI_DISCLAIMER,
    ParagraphAction,
    new_trace_id,
)
from app.domain.ports import AuditLog, CaseRepository

_KIND = "draft_action"


async def record_paragraph_action(
    action: ParagraphAction, *, repository: CaseRepository, audit: AuditLog,
) -> ParagraphAction:
    trace_id = new_trace_id()
    await repository.save_artefact(action.case_id, _KIND, action.model_dump(mode="json"))
    audit.log(
        "draft.paragraph_action",
        trace_id,
        {
            "case_id": action.case_id,
            "paragraph_id": action.paragraph_id,
            "action": action.action,
            "actor": action.actor,
            "final_content": action.final_content,
        },
    )
    return action


async def get_action_state(case_id: str, *, repository: CaseRepository) -> dict:
    """Latest action per paragraph (artefacts are append-only, in order)."""
    artefacts = await repository.list_artefacts(case_id, _KIND)
    latest: dict[str, dict] = {}
    for a in artefacts:
        payload = a.get("payload", a)
        latest[payload["paragraph_id"]] = payload
    return latest


async def export_nota_markdown(case_id: str, *, repository: CaseRepository) -> str:
    """Render the reviewed NOTA as Markdown, applying the latest paragraph
    actions, with the AI disclaimer always present (in-app + export, A4)."""
    drafts = await repository.list_artefacts(case_id, "nota_draft")
    if not drafts:
        raise KeyError(f"no draft for case {case_id}")
    draft = drafts[-1].get("payload", drafts[-1])
    state = await get_action_state(case_id, repository=repository)

    lines = [f"# {draft.get('title', 'NOTA')}", "", f"> {AI_DISCLAIMER}", ""]
    for s in draft.get("sections", []):
        act = state.get(s["heading"])
        if act and act["action"] == "reject":
            continue                                   # rejected → omitted
        content = s.get("content", "")
        status = ""
        if act:
            if act["action"] == "edit":
                content = act["final_content"]
                status = "  _(edited by reviewer)_"
            elif act["action"] == "accept":
                status = "  _(accepted)_"
        lines.append(f"## {s['heading']}{status}")
        lines.append(content or "_[pending]_")
        lines.append("")
    return "\n".join(lines)
