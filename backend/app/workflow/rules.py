"""Deterministic SOP rule engine.

Routing decisions (which SOP applies, whether approval is required, risk
tier) are made by these rules alone — never by the LLM. The LLM's only role
in routing is to phrase a plain-language explanation of the rules that fired.
This split is the liability shield: outcomes are reproducible from the YAML
rulebook, and the audit trail records exactly which rule ids fired.
"""
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import get_settings
from app.models.schemas import RiskTier, RoutingRequest


@lru_cache
def load_rulebook() -> dict:
    sop_dir = Path(get_settings().sop_config_dir)
    rules_file = sop_dir / "routing-rules.yaml"
    if not rules_file.exists():
        # Resolve relative to repo root when running from backend/
        rules_file = Path(__file__).resolve().parents[3] / "config/sop/routing-rules.yaml"
    with rules_file.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _matches_type(rule_types, request_type: str) -> bool:
    if rule_types is None:
        return True
    if isinstance(rule_types, str):
        return rule_types == request_type
    return request_type in rule_types


def evaluate(request: RoutingRequest) -> dict:
    """Return {sop, approval_required, approval_level, risk_tier, rules_fired}."""
    book = load_rulebook()
    fired: list[str] = []

    # 1. SOP selection — first match wins, last entry is the fallback.
    sop = book["sops"][-1]
    for candidate in book["sops"]:
        applies = candidate.get("applies_when", {})
        rule_type = applies.get("request_type")
        if rule_type is None and candidate is not book["sops"][-1]:
            continue
        if rule_type is not None and not _matches_type(rule_type, request.request_type):
            continue
        sop = candidate
        break
    fired.append(sop["id"])

    # 2. Approval threshold (delegation of authority).
    amount = request.amount_idr or 0.0
    approval = book["approval_rules"][-1]
    for rule in book["approval_rules"]:
        ceiling = rule.get("max_amount_idr")
        if ceiling is None or amount < ceiling:
            approval = rule
            break
    fired.append(approval["id"])

    # 3. Risk tier — drives automation level.
    tier_rule = book["risk_rules"][-1]
    for rule in book["risk_rules"]:
        ceiling = rule.get("max_amount_idr")
        if ceiling is not None and amount >= ceiling:
            continue
        if not _matches_type(rule.get("request_types"), request.request_type):
            continue
        tier_rule = rule
        break
    fired.append(tier_rule["id"])

    return {
        "sop": f'{sop["id"]} — {sop["name"]}',
        "approval_required": approval["approval_required"],
        "approval_level": approval.get("approval_level"),
        "risk_tier": RiskTier(tier_rule["tier"]),
        "rules_fired": fired,
    }
