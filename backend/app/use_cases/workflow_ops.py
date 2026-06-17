"""Workflow orchestration completion (Sprint 4.7, FR-6).

Assignable stage owners + task notifications (context / deadline / documents),
parallel workstreams with a merge gate before board preparation, and SLA
bottleneck alerts to supervisors. All append-only + audited.
"""
import uuid
from datetime import timedelta

from app.domain.models import (
    REQUIRED_WORKSTREAMS,
    STAGE_SLA_DAYS,
    Notification,
    new_trace_id,
    utcnow,
)
from app.domain.ports import AuditLog, CaseRepository

NOTIF_SCOPE = "__notifications__"      # global feed (no FK on artefacts.case_id)


async def _notify(to: str, kind: str, case_id: str, title: str, *,
                  body: str = "", deadline: str | None = None,
                  repository: CaseRepository) -> Notification:
    n = Notification(id=f"ntf_{uuid.uuid4().hex[:10]}", to=to, kind=kind,
                     case_id=case_id, title=title, body=body, deadline=deadline)
    await repository.save_artefact(NOTIF_SCOPE, "notification", n.model_dump(mode="json"))
    return n


async def list_notifications(user: str, *, repository: CaseRepository,
                             unread_only: bool = False) -> list[dict]:
    rows = await repository.list_artefacts(NOTIF_SCOPE, "notification")
    out = [r.get("payload", r) for r in rows if r.get("payload", r)["to"] == user]
    if unread_only:
        out = [n for n in out if not n.get("read")]
    return list(reversed(out))


async def assign_stage_owner(
    case_id: str, stage: str, owner: str, *, deadline_days: int = 3,
    repository: CaseRepository, audit: AuditLog,
) -> dict:
    """Assign a human owner to a stage + send them a task notification."""
    deadline = (utcnow() + timedelta(days=deadline_days)).date().isoformat()
    docs = await repository.list_documents(case_id)
    case = await repository.get(case_id)
    rec = {"case_id": case_id, "stage": stage, "owner": owner,
           "deadline": deadline, "at": utcnow().isoformat()}
    await repository.save_artefact(case_id, "stage_assignment", rec)
    await _notify(owner, "assignment", case_id,
                  title=f"Assigned: {stage} — {case.title if case else case_id}",
                  body=f"{len(docs)} document(s) attached. Due {deadline}.",
                  deadline=deadline, repository=repository)
    audit.log("workflow.assigned", new_trace_id(),
              {"case_id": case_id, "stage": stage, "owner": owner, "deadline": deadline})
    return rec


async def get_assignments(case_id: str, *, repository: CaseRepository) -> dict:
    rows = await repository.list_artefacts(case_id, "stage_assignment")
    latest: dict[str, dict] = {}
    for r in rows:
        p = r.get("payload", r)
        latest[p["stage"]] = p
    return latest


# --- Parallel workstreams + merge gate ---------------------------------------

async def set_workstream(
    case_id: str, stream: str, status: str, *,
    repository: CaseRepository, audit: AuditLog,
) -> dict:
    rec = {"case_id": case_id, "stream": stream, "status": status,
           "at": utcnow().isoformat()}
    await repository.save_artefact(case_id, "workstream", rec)
    audit.log("workflow.workstream", new_trace_id(),
              {"case_id": case_id, "stream": stream, "status": status})
    return rec


async def workstream_state(case_id: str, *, repository: CaseRepository) -> dict:
    rows = await repository.list_artefacts(case_id, "workstream")
    latest: dict[str, str] = {}
    for r in rows:
        p = r.get("payload", r)
        latest[p["stream"]] = p["status"]
    return latest


async def merge_gate_pending(case_id: str, *, repository: CaseRepository) -> list[str]:
    """Required workstreams not yet complete (block board prep until empty)."""
    state = await workstream_state(case_id, repository=repository)
    return [s for s in REQUIRED_WORKSTREAMS if state.get(s) != "complete"]


# --- SLA bottleneck alerts ---------------------------------------------------

def _stage_entered_at(case) -> "object":
    for ev in reversed(case.history):
        if ev.stage == case.stage.value:
            return ev.at
    return case.created_at


async def sla_scan(
    *, repository: CaseRepository, audit: AuditLog, supervisor: str = "supervisor",
    scope: str | None = None,
) -> list[dict]:
    """Find cases past their stage SLA and alert the supervisor (bottlenecks)."""
    now = utcnow()
    overdue = []
    for case in await repository.list_all(scope):
        if case.stage.value == "closed":
            continue
        sla = STAGE_SLA_DAYS.get(case.stage.value)
        if not sla:
            continue
        days = (now - _stage_entered_at(case)).days
        if days > sla:
            overdue.append({"case_id": case.case_id, "stage": case.stage.value,
                            "days_in_stage": days, "sla_days": sla})
            await _notify(supervisor, "sla_breach", case.case_id,
                          title=f"SLA breach: {case.title} stuck in {case.stage.value}",
                          body=f"{days}d in stage (SLA {sla}d).", repository=repository)
            audit.log("workflow.sla_breach", new_trace_id(),
                      {"case_id": case.case_id, "stage": case.stage.value,
                       "days_in_stage": days, "sla_days": sla})
    return overdue
