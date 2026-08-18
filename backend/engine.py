"""Governed request pipeline. The LLM proposes (interpret + plan + conflict hypotheses); the
deterministic backend holds authority: it validates the plan against the tool allowlist, retrieves
real policy evidence, checks for contradictions, classifies risk, then ACTS / ASKS a human / ABSTAINS.
Consequential (approval-required) tools are NEVER executed here \u2014 they wait for an authenticated human.
"""
import logging

from db import db, next_counter
from audit import now_iso, append_audit
from orchestrator import interpret, LANG_LABELS
import planner
import policy_store
import risk_engine
import tools as toolmod

logger = logging.getLogger("soa.engine")

UNIT_BY_INTENT = {"maintenance": "Facilities \u00b7 Zone B", "certificate": "Academic Records",
                  "lab_booking": "Laboratory Services", "grievance": "Student Welfare"}
TYPE_LABEL = {"maintenance": "Maintenance", "certificate": "Certificate",
              "lab_booking": "Lab Booking", "grievance": "Grievance", "unknown": "Clarification"}
PRIMARY_ACTION = {"maintenance": "maintenance.create_ticket", "certificate": "certificate.generate",
                  "lab_booking": "lab.create_booking", "grievance": "grievance.create_case"}


def _step(n, title, tool, actor, risk, status, output):
    return {"n": n, "title": title, "tool": tool, "actor": actor, "risk": risk, "status": status, "output": output}


async def process_request(text: str, opts: dict, identity: dict = None) -> dict:
    actor = opts.get("actor", {})
    interp = await interpret(text)
    lang = interp.get("language", "en")
    intent = interp.get("intent", "unknown")
    normalized = interp.get("normalized_en") or text
    fields = interp.get("fields", {})
    interpreter = "llm" if interp.get("_ai") else "deterministic_fallback"
    rid = opts.get("force_id") or f"REQ-{await next_counter('REQ')}"
    seq = opts.get("force_seq") if opts.get("force_seq") is not None else await next_counter("REQ_SEQ")

    base = {
        "id": rid, "state": "INTERPRETING", "lang": lang, "langLabel": LANG_LABELS.get(lang, "English"),
        "original": text, "normalized": normalized, "intent": f"{intent}",
        "requester": None if opts.get("anonymous") else opts.get("requester", "Ananya Sahoo"),
        "requesterId": actor.get("id"), "anonymous": bool(opts.get("anonymous")),
        "viaVoice": bool(opts.get("via_voice")), "aiInterpreted": interp.get("_ai", False),
        "interpreter": interpreter, "typeLabel": TYPE_LABEL.get(intent, "Clarification"),
        "unit": UNIT_BY_INTENT.get(intent, "Service Desk"), "fields": fields, "evidence": [],
        "conflict": None, "diff": None, "pseudonym": None, "decision": None, "followUp": None,
        "messages": [], "createdAt": now_iso(), "seq": seq, "recordId": None, "recordLabel": None,
    }
    ctx = {"requestId": rid, "text": normalized, "interp": interp, "requester": base["requester"],
           "anonymous": base["anonymous"], "soaId": opts.get("soa_id"), "identity": identity,
           "actorId": actor.get("id", "system")}
    audit = [{"action": "interpret.normalize", "actor": "SOA Agent", "role": "system", "interpreter": interpreter,
              "summary": f"{base['langLabel']} request normalized \u00b7 intent {intent} \u00b7 conf {interp.get('confidence')}"}]

    # --- ABSTAIN: uncertainty ---
    if intent == "unknown" or float(interp.get("confidence", 0)) < 0.45:
        base.update({"state": "NEEDS_INFO", "status": "needs_info", "risk": "LOW", "autonomy": "NEEDS INFO",
                     "typeLabel": "Clarification", "unit": "Service Desk",
                     "abstention": {"decision": "ABSTAIN", "reason_code": "INSUFFICIENT_INFO",
                                    "reason": "Intent could not be confidently classified.",
                                    "recommended_action": "Ask requester for clarification"},
                     "followUp": "I cannot safely classify this yet. Is this about maintenance, a certificate, a lab booking, or a grievance \u2014 and where/when?",
                     "plan": [_step(1, "Normalize & detect intent", "interpret.normalize", "SOA Agent", "LOW", "done", "Confidence below threshold"),
                              _step(2, "Ask focused follow-up", "interpret.clarify", "SOA Agent", "LOW", "active", "Awaiting clarification")]})
        base["messages"].append({"id": "MSG-1", "author": "SOA Agent", "role": "agent", "text": base["followUp"], "ts": now_iso()})
        audit.append({"action": "governance.abstain", "actor": "Risk Gate", "role": "system",
                      "abstention": base["abstention"], "summary": "ABSTAIN \u00b7 INSUFFICIENT_INFO \u2192 focused follow-up"})
        await _persist(base, audit); return base

    # --- Plan (LLM proposes) + deterministic validation ---
    plan = await planner.generate_plan(interp)
    ok, errs = planner.validate_plan(plan)
    audit.append({"action": "plan.generate", "actor": "Planner", "role": "system",
                  "summary": f"Plan proposed by {plan.get('planner')} \u00b7 {len(plan.get('steps', []))} steps \u00b7 validation {'PASS' if ok else 'FAIL: ' + '; '.join(errs)}"})
    if not ok:
        plan = planner._fallback_plan(interp)

    # --- Real evidence retrieval (RAG) ---
    evidence = await policy_store.retrieve(normalized, k=4)
    base["evidence"] = [{"policy": e["policyId"], "ref": e["ref"], "stance": e["text"][:180], "score": e["score"]} for e in evidence]
    audit.append({"action": "evidence.retrieve", "actor": "Evidence Engine", "role": "system",
                  "policyRefs": [f"{e['policyId']} {e['ref']}" for e in evidence[:3]],
                  "summary": f"{len(evidence)} passages retrieved via {policy_store.emb.get_provider().name}"})

    primary = PRIMARY_ACTION.get(intent, "policy.search")

    # --- Generalized conflict detection -> ABSTAIN ---
    conflict = await policy_store.detect_conflict(normalized, evidence)
    if not conflict.get("conflict") and intent == "lab_booking" and (interp.get("after_hours") or interp.get("exam_week")):
        conflict = {
            "conflict": True, "confidence": 0.9, "evaluator": "deterministic_flags",
            "policy_a": "POL-LAB", "section_a": "§5.1",
            "stance_a": "Prohibits student bookings between 18:00 and 08:00.",
            "policy_b": "POL-EMRG", "section_b": "§1.2",
            "stance_b": "Permits supervised lab access at any hour during exam weeks.",
            "reason": "After-hours / exam-week lab request hits two live policies. Abstain instead of inventing a booking.",
        }
    if conflict.get("conflict"):
        base.update({"state": "ABSTAINED", "status": "abstained", "autonomy": "ABSTAINED",
                     "risk": risk_engine.classify(primary, interp, {"policy_uncertain": True})["risk"],
                     "unit": "Laboratory Coordinator" if intent == "lab_booking" else base["unit"],
                     "conflict": {"code": "CONFLICT_DETECTED",
                                  "a": {"policy": conflict["policy_a"], "ref": conflict["section_a"], "stance": conflict["stance_a"]},
                                  "b": {"policy": conflict["policy_b"], "ref": conflict["section_b"], "stance": conflict["stance_b"]},
                                  "confidence": conflict["confidence"], "reason": conflict["reason"],
                                  "routedTo": "Laboratory Coordinator" if intent == "lab_booking" else base["unit"]},
                     "abstention": {"decision": "ABSTAIN", "reason_code": "POLICY_CONFLICT",
                                    "reason": conflict["reason"], "recommended_action": f"Route to {base['unit']}"},
                     "plan": _display_plan(plan, evidence, halted_at="conflict")})
        audit.append({"action": "governance.conflict_check", "actor": "Risk Gate", "role": "system",
                      "policyRefs": [f"{conflict['policy_a']} {conflict['section_a']}", f"{conflict['policy_b']} {conflict['section_b']}"],
                      "abstention": base["abstention"],
                      "summary": f"CONFLICT_DETECTED (conf {conflict['confidence']}, {conflict['evaluator']}) \u2192 ABSTAIN, route to human"})
        await _persist(base, audit); return base

    # --- Risk classification (deterministic) ---
    rc = risk_engine.classify(primary, interp, {})
    base["risk"] = rc["risk"]
    audit.append({"action": "risk.classify", "actor": "Risk Gate", "role": "system", "risk": rc["risk"],
                  "summary": f"Risk {rc['risk']} \u00b7 factors: {', '.join(rc['factors']) or 'none'} \u00b7 approval {'required' if rc['requires_human_approval'] else 'not required'}"})

    # --- Execute non-consequential steps; gate consequential ones ---
    display, exec_audit, record = await _run_plan(plan, ctx, rc, primary, intent, fields, base)
    base["plan"] = display
    audit.extend(exec_audit)
    base.update(record)
    await _persist(base, audit)
    return base


def _display_plan(plan, evidence, halted_at=None):
    out = []
    for i, s in enumerate(plan.get("steps", []), 1):
        status = "done" if s["tool"] == "policy.search" else ("abstained" if halted_at == "conflict" else "cancelled")
        out.append(_step(i, s.get("action", s["tool"]), s["tool"], "Evidence Engine" if s["tool"] == "policy.search" else "Orchestrator",
                         toolmod.TOOL_REGISTRY.get(s["tool"], {}).get("risk", "LOW"), status,
                         "2 passages retrieved \u00b7 contradiction found" if halted_at == "conflict" and s["tool"] == "policy.search" else "Not executed \u2014 abstention"))
    return out


async def _run_plan(plan, ctx, rc, primary, intent, fields, base):
    display, audit, record = [], [], {}
    n = 0
    pending = None
    for s in plan.get("steps", []):
        n += 1
        tool = s["tool"]; spec = toolmod.TOOL_REGISTRY.get(tool, {})
        args = s.get("args", {})
        ctx["stepId"] = s.get("id")
        if tool == "policy.search":
            display.append(_step(n, s.get("action", "Retrieve evidence"), tool, "Evidence Engine", "LOW", "done", "Policy evidence retrieved"))
            continue
        # consequential (approval-required) primary action -> BLOCK, wait for human
        if tool == primary and rc["requires_human_approval"]:
            display.append(_step(n, s.get("action", tool), tool, "Awaiting human approver", spec.get("risk", "HIGH"), "blocked",
                                 "Paused \u2014 awaiting authenticated human approval"))
            pending = {"tool": tool, "args": args, "stepN": n}
            continue
        # execute
        result = await toolmod.execute_tool(tool, args, ctx)
        if result.get("failed"):
            display.append(_step(n, s.get("action", tool), tool, "Orchestrator", spec.get("risk", "LOW"), "cancelled",
                                 f"FAILED: {result.get('reason') or result.get('error')}"))
            record.update({"state": "FAILED", "status": "abstained", "autonomy": "ABSTAINED",
                           "abstention": {"decision": "ABSTAIN", "reason_code": "TOOL_FAILURE",
                                          "reason": result.get("reason") or result.get("error"),
                                          "recommended_action": f"Route to {base['unit']}"}})
            audit.append({"action": f"tool.{tool}", "tool": tool, "actor": "Orchestrator", "role": "system",
                          "summary": f"Tool {tool} FAILED \u00b7 {result.get('reason') or result.get('error')}"})
            record.setdefault("recordId", None)
            return display, audit, record
        rec_id = result.get("recordId")
        display.append(_step(n, s.get("action", tool), tool, "Orchestrator", spec.get("risk", "LOW"), "done",
                             f"{rec_id or 'done'} \u00b7 {result.get('status', 'OK')}"))
        audit.append({"action": f"tool.{tool}", "tool": tool, "actor": "Orchestrator", "role": "system",
                      "policyRefs": [], "summary": f"{tool} \u2192 {rec_id or result}"})
        if tool == primary:
            record["recordId"] = rec_id
            if intent == "maintenance":
                record.update({"state": "COMPLETED", "status": "completed", "autonomy": "AUTO-EXECUTED", "recordLabel": "Maintenance Ticket"})
            elif intent == "lab_booking":
                record.update({"state": "COMPLETED", "status": "completed", "autonomy": "AUTO-DRAFT", "recordLabel": "Lab Booking"})
            elif intent == "grievance":
                record.update({"state": "ESCALATED", "status": "in_triage", "autonomy": "HUMAN TRIAGE" if fields.get("urgency") else "ROUTED",
                               "recordLabel": "Grievance Case", "pseudonym": result.get("pseudonym"),
                               "urgency": "CRITICAL" if base.get("interpreterCritical") else ("CRITICAL" if result.get("status") == "TRIAGE" else "NORMAL")})
                if base.get("anonymous"):
                    record["requester"] = result.get("pseudonym")
                record["slaDeadline"] = result.get("slaDeadline")

    if pending:
        record.update({"state": "AWAITING_APPROVAL", "status": "awaiting_approval", "autonomy": "AWAITING APPROVAL",
                       "recordLabel": "Certificate Request", "approver": "Dr. R. Mishra \u00b7 Academic Approver",
                       "pendingTool": pending["tool"], "pendingArgs": pending["args"],
                       "diff": {"action": "ISSUE_CERTIFICATE", "before": "No certificate on record for this purpose",
                                "after": "Certificate issued \u00b7 PDF artifact generated \u00b7 requester notified"}})
        audit.append({"action": "governance.gate", "actor": "Risk Gate", "role": "system", "approval": "PENDING",
                      "summary": f"Consequential action {pending['tool']} blocked \u00b7 awaiting authenticated approver"})
    return display, audit, record


async def _persist(base, audit_events):
    await db.service_requests.replace_one({"id": base["id"]}, {**base}, upsert=True)
    base.pop("_id", None)
    ctx_rid = base["id"]
    # attach requestId to all audit events
    for e in audit_events:
        e.setdefault("requestId", ctx_rid)
    await append_audit(audit_events, ctx_rid)


async def execute_pending_certificate(req: dict, approver: dict, reason: str) -> dict:
    """Runs the deferred consequential tool AFTER authenticated human approval."""
    tool = req.get("pendingTool", "certificate.generate")
    args = dict(req.get("pendingArgs", {}))
    args.update({"requester": req.get("requester"), "soaId": (req.get("fields") or {}).get("soaId"),
                 "approver": approver["name"], "approvedAt": now_iso(),
                 "purpose": (req.get("fields") or {}).get("purpose", args.get("purpose", "As stated"))})
    ctx = {"requestId": req["id"], "actorId": approver["id"], "requester": req.get("requester"),
           "soaId": args.get("soaId")}
    result = await toolmod.execute_tool(tool, args, ctx)
    plan = [dict(s) for s in req["plan"]]
    for s in plan:
        if s.get("status") == "blocked":
            s["status"] = "done"; s["actor"] = approver["name"]
            s["output"] = f"Approved by {approver['name']} \u00b7 {result.get('recordId')} issued"
    plan.append(_step(len(plan) + 1, "Notify requester & write audit", "grievance.route_case" if False else "notify",
                      "Orchestrator", "LOW", "done", "Requester notified \u00b7 certificate artifact ready"))
    update = {"status": "completed", "state": "COMPLETED", "autonomy": "HUMAN APPROVED",
              "recordId": result.get("recordId"), "verificationId": result.get("verificationId"),
              "hasPdf": result.get("hasPdf"), "plan": plan, "pendingTool": None,
              "decision": {"by": approver["name"], "decision": "APPROVED", "reason": reason, "at": now_iso()}}
    await db.service_requests.update_one({"id": req["id"]}, {"$set": update})
    reason_txt = reason or "\u2014"
    await append_audit([{"action": "approval.approve", "actor": approver["name"], "actorId": approver["id"],
                         "role": "approver", "approval": "APPROVED", "policyRefs": ["POL-CERT \u00a73.2"],
                         "summary": f"APPROVED by {approver['name']} \u00b7 {result.get('recordId')} generated \u00b7 reason: {reason_txt}"}], req["id"])
    return await db.service_requests.find_one({"id": req["id"]}, {"_id": 0})
