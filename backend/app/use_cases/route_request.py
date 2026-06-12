"""Routing use case — deterministic rules + LLM-generated explanation.

The rule engine decides; the model explains. The explanation is grounded in
the fired rules and never overrides them.
"""
from app.domain.models import new_trace_id
from app.domain.models import RoutingDecision, RoutingRequest
from app.domain.ports import AuditLog, CaseRepository, LLMGateway
from app.domain.rules import evaluate

EXPLAIN_SYSTEM = """You explain Danantara DAM routing decisions to governance \
officers. You are given the request and the deterministic rule outcomes. \
Write a short, plain-language explanation (3-5 sentences, Bahasa Indonesia \
followed by an English summary line) of why this SOP applies, whether \
approval is needed and at what level, and what the risk tier means for \
automation. Never contradict or second-guess the rule outcomes."""


async def route_request(
    request: RoutingRequest, *, llm: LLMGateway,
    repository: CaseRepository, audit: AuditLog,
) -> RoutingDecision:
    trace_id = new_trace_id()
    outcome = evaluate(request)

    explanation = await llm.complete(
        system=EXPLAIN_SYSTEM,
        prompt=(
            f"Request: {request.model_dump_json()}\n"
            f"Rule outcomes: SOP={outcome['sop']}, "
            f"approval_required={outcome['approval_required']}, "
            f"approval_level={outcome['approval_level']}, "
            f"risk_tier={outcome['risk_tier'].value}, "
            f"rules_fired={outcome['rules_fired']}"
        ),
        max_tokens=1024,
    )

    decision = RoutingDecision(
        case_id=request.case_id,
        applicable_sop=outcome["sop"],
        approval_required=outcome["approval_required"],
        approval_level=outcome["approval_level"],
        risk_tier=outcome["risk_tier"],
        rules_fired=outcome["rules_fired"],
        explanation=explanation,
        trace_id=trace_id,
    )
    await repository.save_artefact(request.case_id, "routing_decision",
                                   decision.model_dump(mode="json"))
    audit.log(
        "agent.routing",
        trace_id,
        {
            "case_id": request.case_id,
            "request": request.model_dump(),
            "rules_fired": outcome["rules_fired"],
            "decision": {
                "sop": outcome["sop"],
                "approval_required": outcome["approval_required"],
                "approval_level": outcome["approval_level"],
                "risk_tier": outcome["risk_tier"].value,
            },
            "model": llm.model,
        },
    )
    return decision
