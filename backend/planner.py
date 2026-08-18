"""Agentic planner: the LLM PROPOSES a structured multi-step plan; the deterministic validator
rejects unknown tools, bad dependencies (missing refs / cycles) and malformed schemas BEFORE any
execution. A deterministic fallback plan keeps the demo reliable if the LLM is unavailable/invalid.
"""
import logging
from typing import Dict, List, Tuple

from llm import complete_json
from tools import TOOL_REGISTRY, capabilities_brief

logger = logging.getLogger("soa.planner")

PLANNER_SYSTEM = """You are the PLANNER of SOA, a governed institutional service platform. Given a normalized
request, extracted fields and the ALLOWED capabilities, propose a minimal ordered plan. You may ONLY use tools
from the provided allowlist — never invent tools. You do not execute anything; a deterministic backend validates
and runs your plan. Return STRICT JSON only:
{"goal": str, "intent": "maintenance|certificate|lab_booking|grievance", "confidence": 0-1,
 "steps": [{"id": "step_1", "action": str, "tool": "<allowlisted tool>", "args": {..}, "depends_on": ["step_x"]}]}
Keep 2-5 steps. Always retrieve policy evidence (policy.search) before consequential actions."""


def _fallback_plan(interp: Dict) -> Dict:
    intent = interp.get("intent", "unknown")
    f = interp.get("fields", {})
    steps = [{"id": "step_1", "action": "retrieve policy evidence", "tool": "policy.search",
              "args": {"query": interp.get("normalized_en", "")}, "depends_on": []}]
    if intent == "maintenance":
        steps.append({"id": "step_2", "action": "create maintenance ticket", "tool": "maintenance.create_ticket",
                      "args": {"location": f.get("location", ""), "issue": interp.get("normalized_en", ""),
                               "severity": "High (safety)" if interp.get("safety") else "Normal"},
                      "depends_on": ["step_1"]})
    elif intent == "certificate":
        steps.append({"id": "step_2", "action": "verify enrollment", "tool": "certificate.verify_enrollment",
                      "args": {}, "depends_on": ["step_1"]})
        steps.append({"id": "step_3", "action": "issue certificate", "tool": "certificate.generate",
                      "args": {"purpose": f.get("purpose", "As stated"), "certificateType": f.get("certificateType", "Bonafide Certificate")},
                      "depends_on": ["step_1", "step_2"]})
    elif intent == "lab_booking":
        steps.append({"id": "step_2", "action": "check availability", "tool": "lab.check_availability",
                      "args": {"lab": f.get("lab", ""), "date": f.get("date", "today")}, "depends_on": ["step_1"]})
        steps.append({"id": "step_3", "action": "create booking", "tool": "lab.create_booking",
                      "args": {"lab": f.get("lab", ""), "date": f.get("date", "today")}, "depends_on": ["step_1", "step_2"]})
    elif intent == "grievance":
        steps.append({"id": "step_2", "action": "create grievance case", "tool": "grievance.create_case",
                      "args": {"category": f.get("category", "General"), "description": interp.get("normalized_en", "")},
                      "depends_on": ["step_1"]})
        steps.append({"id": "step_3", "action": "route case", "tool": "grievance.route_case",
                      "args": {"cell": "Student Welfare"}, "depends_on": ["step_2"]})
    return {"goal": interp.get("normalized_en", ""), "intent": intent,
            "confidence": interp.get("confidence", 0.5), "steps": steps, "planner": "deterministic_fallback"}


async def generate_plan(interp: Dict) -> Dict:
    if interp.get("intent") in (None, "unknown"):
        return {"goal": interp.get("normalized_en", ""), "intent": "unknown", "confidence": interp.get("confidence", 0.2),
                "steps": [], "planner": "none"}
    try:
        prompt = (f"Normalized request: {interp.get('normalized_en')}\nIntent: {interp.get('intent')}\n"
                  f"Fields: {interp.get('fields', {})}\n\nAllowed tools:\n{capabilities_brief()}\n\nReturn the JSON plan now.")
        plan = await complete_json(PLANNER_SYSTEM, prompt)
        plan["planner"] = "llm"
        ok, errs = validate_plan(plan)
        if not ok:
            logger.warning(f"LLM plan invalid {errs}; using fallback")
            return _fallback_plan(interp)
        return plan
    except Exception as e:  # noqa: BLE001
        logger.warning(f"planner LLM failed ({e}); using fallback")
        return _fallback_plan(interp)


def validate_plan(plan: Dict) -> Tuple[bool, List[str]]:
    errs = []
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return False, ["no steps"]
    ids = set()
    for s in steps:
        if not isinstance(s, dict) or "id" not in s or "tool" not in s:
            errs.append("malformed step"); continue
        ids.add(s["id"])
        if s["tool"] not in TOOL_REGISTRY:
            errs.append(f"unknown tool: {s['tool']}")
    for s in steps:
        for dep in s.get("depends_on", []):
            if dep not in ids:
                errs.append(f"missing dependency {dep} in {s.get('id')}")
    # cycle detection
    graph = {s["id"]: list(s.get("depends_on", [])) for s in steps if "id" in s}
    state = {}

    def dfs(node):
        state[node] = 1
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                return True
            if state.get(nxt, 0) == 0 and dfs(nxt):
                return True
        state[node] = 2
        return False
    for n in graph:
        if state.get(n, 0) == 0 and dfs(n):
            errs.append("circular dependency"); break
    return (len(errs) == 0), errs
