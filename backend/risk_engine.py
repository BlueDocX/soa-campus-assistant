"""Deterministic risk engine. The LLM may propose indicators, but final risk is computed here
from explicit governance factors. Returns risk class + factors + approval requirement.
Risk classes: LOW, MEDIUM, HIGH, CRITICAL. (ABSTAINED is an OUTCOME, not a risk class.)
"""
from typing import Dict

# action -> base governance profile
ACTION_PROFILE = {
    "maintenance.create_ticket": {"base": "LOW", "reversible": True, "changes_record": False},
    "lab.create_booking":        {"base": "MEDIUM", "reversible": True, "changes_record": True},
    "certificate.generate":      {"base": "HIGH", "reversible": False, "changes_record": True,
                                   "academic_record": True, "requires_named_authority": True},
    "grievance.create_case":     {"base": "MEDIUM", "reversible": False, "changes_record": True,
                                   "identity_sensitive": True},
}

ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _bump(risk: str, steps: int = 1) -> str:
    i = min(ORDER.index(risk) + steps, len(ORDER) - 1)
    return ORDER[i]


def classify(action: str, interp: Dict, context: Dict = None) -> Dict:
    context = context or {}
    prof = ACTION_PROFILE.get(action, {"base": "MEDIUM", "reversible": True, "changes_record": False})
    risk = prof["base"]
    factors = []

    if prof.get("changes_record"):
        factors.append("changes_official_record")
    if prof.get("academic_record"):
        factors.append("changes_official_academic_record")
    if prof.get("requires_named_authority"):
        factors.append("requires_named_authority")
    if not prof.get("reversible", True):
        factors.append("non_reversible_action")
    if prof.get("identity_sensitive"):
        factors.append("identity_privacy_sensitive")

    # Safety / severity escalation
    if interp.get("safety"):
        factors.append("physical_safety_impact")
    if interp.get("critical"):
        factors.append("critical_welfare_impact")
        risk = _bump(risk)
    # Policy uncertainty raises risk
    if context.get("policy_uncertain"):
        factors.append("policy_version_uncertainty")
        risk = _bump(risk)

    requires_approval = risk in ("HIGH", "CRITICAL") or prof.get("requires_named_authority", False)
    return {"risk": risk, "factors": factors, "requires_human_approval": requires_approval,
            "reversible": prof.get("reversible", True)}
