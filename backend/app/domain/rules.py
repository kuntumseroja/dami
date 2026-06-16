"""Deterministic SOP rule engine.

Routing decisions (which SOP applies, whether approval is required, risk
tier) are made by these rules alone — never by the LLM. The LLM's only role
in routing is to phrase a plain-language explanation of the rules that fired.
This split is the liability shield: outcomes are reproducible from the YAML
rulebook, and the audit trail records exactly which rule ids fired.
"""
import os
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from app.domain.models import RiskTier, RoutingRequest


@lru_cache
def load_rulebook() -> dict:
    # Rulebook location: SOP_CONFIG_DIR env var, falling back to the repo's
    # config/sop directory. Plain env access keeps the domain framework-free.
    sop_dir = Path(os.environ.get("SOP_CONFIG_DIR", "../config/sop"))
    rules_file = sop_dir / "routing-rules.yaml"
    if not rules_file.exists():
        rules_file = Path(__file__).resolve().parents[3] / "config/sop/routing-rules.yaml"
    with rules_file.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _matches_type(rule_types, request_type: str) -> bool:
    if rule_types is None:
        return True
    if isinstance(rule_types, str):
        return rule_types == request_type
    return request_type in rule_types


def _sop_active(sop: dict, today: date | None = None) -> bool:
    """Only an approved SOP whose effective_date has arrived may route (4.1)."""
    if sop.get("status", "approved") != "approved":
        return False
    eff = sop.get("effective_date")
    if not eff:
        return True
    eff_date = eff if isinstance(eff, date) else date.fromisoformat(str(eff))
    return eff_date <= (today or date.today())


def evaluate(request: RoutingRequest) -> dict:
    """Return {sop, approval_required, approval_level, risk_tier, rules_fired}."""
    book = load_rulebook()
    fired: list[str] = []

    # 1. SOP selection — first ACTIVE match wins; last entry is the fallback.
    #    Draft/retired/not-yet-effective SOPs are skipped (4.1 only-approved-active).
    sop = book["sops"][-1]
    for candidate in book["sops"]:
        if not _sop_active(candidate):
            continue
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
        "sop_id": sop["id"],
        "sop_version": sop.get("version"),
        "approval_required": approval["approval_required"],
        "approval_level": approval.get("approval_level"),
        "risk_tier": RiskTier(tier_rule["tier"]),
        "rules_fired": fired,
    }


def sop_catalogue() -> list[dict]:
    """All SOPs with lifecycle metadata + computed active flag (4.1)."""
    return [
        {"id": s["id"], "name": s["name"], "version": s.get("version"),
         "owner": s.get("owner"), "status": s.get("status", "approved"),
         "effective_date": str(s.get("effective_date")) if s.get("effective_date") else None,
         "active": _sop_active(s),
         "request_types": s.get("applies_when", {}).get("request_type")}
        for s in load_rulebook()["sops"]
    ]


def sop_coverage(categories: list[str]) -> dict:
    """Which request categories are served by an ACTIVE (approved) SOP (4.1)."""
    covered = {}
    for cat in categories:
        match = next((s["id"] for s in load_rulebook()["sops"]
                      if _sop_active(s)
                      and _matches_type(s.get("applies_when", {}).get("request_type"), cat)
                      and s.get("applies_when", {}).get("request_type") is not None), None)
        covered[cat] = match            # None → only the fallback covers it
    served = sum(1 for v in covered.values() if v)
    return {"categories": covered, "served": served, "total": len(categories),
            "coverage": round(served / len(categories), 4) if categories else 0.0}
