"""Routing agent — deterministic rules + LLM-generated explanation.

The rule engine decides; the model explains. The explanation is grounded in
the fired rules and never overrides them.
"""
from app.agents.base import get_client, model_id
from app.core.audit import audit_log, new_trace_id
from app.models.schemas import RoutingDecision, RoutingRequest
from app.workflow.rules import evaluate

EXPLAIN_SYSTEM = """You explain Danantara DAM routing decisions to governance \
officers. You are given the request and the deterministic rule outcomes. \
Write a short, plain-language explanation (3-5 sentences, Bahasa Indonesia \
followed by an English summary line) of why this SOP applies, whether \
approval is needed and at what level, and what the risk tier means for \
automation. Never contradict or second-guess the rule outcomes."""


async def route_request(request: RoutingRequest) -> RoutingDecision:
    trace_id = new_trace_id()
    outcome = evaluate(request)

    client = get_client()
    response = await client.messages.create(
        model=model_id(),
        max_tokens=1024,
        system=EXPLAIN_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Request: {request.model_dump_json()}\n"
                f"Rule outcomes: SOP={outcome['sop']}, "
                f"approval_required={outcome['approval_required']}, "
                f"approval_level={outcome['approval_level']}, "
                f"risk_tier={outcome['risk_tier'].value}, "
                f"rules_fired={outcome['rules_fired']}"
            ),
        }],
    )
    explanation = next((b.text for b in response.content if b.type == "text"), "")

    audit_log(
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
            "model": model_id(),
        },
    )
    return RoutingDecision(
        case_id=request.case_id,
        applicable_sop=outcome["sop"],
        approval_required=outcome["approval_required"],
        approval_level=outcome["approval_level"],
        risk_tier=outcome["risk_tier"],
        rules_fired=outcome["rules_fired"],
        explanation=explanation,
        trace_id=trace_id,
    )
