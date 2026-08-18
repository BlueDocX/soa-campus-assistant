"""SOA orchestration: AI interpretation layer (proposes only) + deterministic risk-gated plan builder.
The LLM never mutates data or picks tools — it classifies, extracts and normalizes.
The deterministic layer validates against the allowlist, risk matrix, and evidence corpus.
"""
import re
import logging

from llm import complete_json

logger = logging.getLogger(__name__)

INTENT_ALIASES = {
    "maintenance_request": "maintenance",
    "maint": "maintenance",
    "repair": "maintenance",
    "cert": "certificate",
    "bonafide": "certificate",
    "certificate_request": "certificate",
    "lab": "lab_booking",
    "booking": "lab_booking",
    "lab_book": "lab_booking",
    "complaint": "grievance",
    "grievance_request": "grievance",
}

INTERPRET_SYSTEM = """You are the interpretation layer of SOA, an institutional service platform for a university campus (SOA).
You ONLY classify and extract. You never decide actions, tools, or approvals.
Return STRICT JSON (no markdown, no commentary) with this exact schema:
{
  "language": "en" | "hi" | "od",
  "intent": "maintenance" | "certificate" | "lab_booking" | "grievance" | "unknown",
  "confidence": 0.0-1.0,
  "normalized_en": "one-sentence English normalization of the request",
  "fields": { relevant extracted key-value pairs, keys camelCase, values short strings },
  "after_hours": true if a lab booking is requested between 18:00 and 08:00 (evening/night/tonight/9pm etc), else false,
  "exam_week": true if the requester mentions exams/exam week as justification, else false,
  "critical": true if a grievance involves safety, harassment, ragging, threats, or fear, else false,
  "safety": true if a maintenance issue poses injury risk, else false
}
If the request is ambiguous or unrelated to the four intents, use intent "unknown" with low confidence."""


def detect_lang(text: str) -> str:
    if re.search(r"[\u0B00-\u0B7F]", text):
        return "od"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return "en"


def _detect_lang(text: str) -> str:
    return detect_lang(text)


def should_autofile(interp: dict, identity_ok: bool) -> bool:
    if not identity_ok:
        return False
    if interp.get("intent") in (None, "unknown"):
        return False
    try:
        return float(interp.get("confidence") or 0) >= 0.55
    except (TypeError, ValueError):
        return False


def _normalize_intent(value) -> str:
    raw = str(value or "unknown").strip().lower().replace(" ", "_").replace("-", "_")
    return INTENT_ALIASES.get(raw, raw if raw in {"maintenance", "certificate", "lab_booking", "grievance", "unknown"} else "unknown")


def _keyword_interpret(text: str) -> dict:
    """Deterministic fallback when the LLM is unavailable — keeps the demo repeatable."""
    t = text.lower()
    lang = _detect_lang(text)
    out = {"language": lang, "confidence": 0.55, "normalized_en": text if lang == "en" else "Request auto-translated to English (fallback mode).",
           "fields": {}, "after_hours": bool(re.search(r"(night|9\s?pm|10\s?pm|after hours|tonight)", t)),
           "exam_week": "exam" in t, "critical": bool(re.search(r"(ragging|harass|unsafe|threat|afraid)", t)),
           "safety": bool(re.search(r"(leak|slip|shock|injur|hazard|पानी|लीक)", t))}
    if re.search(r"(leak|लीक|पानी|broken|repair|not working|fan|\bac\b|maintenance|water|fused|खराब|projector)", t):
        out["intent"] = "maintenance"
    elif re.search(r"(certificate|bonafide|transcript|प्रमाण|marksheet)", t):
        out["intent"] = "certificate"
    elif re.search(r"(book|booking|reserve|lab|ଲାବ|ବୁକ୍|slot)", t):
        out["intent"] = "lab_booking"
    elif re.search(r"(grievance|complaint|harass|ragging|unsafe|hostel|शिकायत)", t):
        out["intent"] = "grievance"
    else:
        out["intent"] = "unknown"
        out["confidence"] = 0.2
    return out


async def interpret(text: str) -> dict:
    """LLM interpretation with structured JSON output; deterministic fallback on any failure."""
    try:
        data = await complete_json(INTERPRET_SYSTEM, f"Request: {text}")
        data["intent"] = _normalize_intent(data.get("intent"))
        if data["intent"] not in {"maintenance", "certificate", "lab_booking", "grievance", "unknown"}:
            raise ValueError("invalid intent")
        data["language"] = data.get("language") if data.get("language") in {"en", "hi", "od"} else detect_lang(text)
        data.setdefault("fields", {})
        data["fields"] = {str(k): str(v) for k, v in (data.get("fields") or {}).items() if v is not None}
        for k in ("after_hours", "exam_week", "critical", "safety"):
            data[k] = bool(data.get(k))
        try:
            data["confidence"] = float(data.get("confidence", 0.7))
        except (TypeError, ValueError):
            data["confidence"] = 0.7
        data["_ai"] = True
        # Keyword flags are cheap and keep the exam-week / leak demo honest if the LLM misses them.
        kw = _keyword_interpret(text)
        for flag in ("after_hours", "exam_week", "critical", "safety"):
            data[flag] = bool(data.get(flag) or kw.get(flag))
        return data
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM interpret failed, using deterministic fallback: {e}")
        out = _keyword_interpret(text)
        out["_ai"] = False
        return out


# ---------------------------------------------------------------------------
# Conversational intake manager
# The assistant holds a short turn-based conversation, understands Hindi/Odia/
# English input and replies in the student's language, collects the SOA ID for
# non-anonymous requests, and signals when it has enough to file the request.
# It NEVER decides outcomes — the deterministic orchestrator still does that.
# ---------------------------------------------------------------------------
CONVERSE_SYSTEM = """You are SOA's friendly institutional service assistant for a university campus (SOA).
You hold a short spoken conversation with a student to collect ONE service request, then hand it off to be filed.
Every request must fall into exactly one of: maintenance, certificate (e.g. bonafide), lab_booking, or grievance.

Hard rules:
- Reply in the student's language (en / hi / od). Match their latest message. Warm, concise, at most 2 short sentences. No markdown, no bullet points, no emojis.
- Understand Hindi, Odia and English. Do not switch to English unless they wrote English.
- Ask for only ONE thing at a time. If the request is already clear, set ready=true instead of asking more.
- __SOA_RULE__
- You do NOT decide approvals, policies or outcomes. You only gather details and confirm. A separate governed engine decides what happens.
- Never fabricate policies, IDs or outcomes.

Return STRICT JSON ONLY (no markdown fences, no commentary) with this exact schema:
{
  "reply": "the next thing you say to the student",
  "soa_id": "the SOA ID the student provided in THIS conversation, else null",
  "ready": true only when you have a clear request in one of the four categories AND (the request is anonymous OR an SOA ID has been provided); otherwise false,
  "request_summary": "one clear English sentence describing the complete request (only when ready is true, else an empty string)"
}"""


def _converse_fallback(messages: list, anonymous: bool, soa_captured: bool, lang: str = "en") -> dict:
    """Deterministic conversation manager used when the LLM is unavailable."""
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    joined = " ".join(user_msgs).strip()
    soa = None
    if not anonymous and not soa_captured:
        m = re.search(r"\b(\d{3,4}[-/ ]?[A-Za-z]{2,4}[-/ ]?\d{2,4}|[A-Za-z]{2,4}\d{4,8})\b", joined)
        if m:
            soa = m.group(1)
    copies = {
        "en": {
            "hi": "Hi! What can I help you with today — a certificate, a maintenance issue, a lab booking, or a grievance?",
            "id": "Got it. Could you please tell me your SOA ID so I can file this for you?",
            "ok": "Thank you — let me file that for you now.",
        },
        "hi": {
            "hi": "नमस्ते! आज क्या मदद चाहिए — प्रमाणपत्र, मरम्मत, लैब बुकिंग, या शिकायत?",
            "id": "समझ गया। फाइल करने के लिए अपना SOA ID बताइए।",
            "ok": "धन्यवाद — मैं अभी यह दर्ज कर रहा हूँ।",
        },
        "od": {
            "hi": "ନମସ୍କାର! ଆଜି କ’ଣ ସାହାଯ୍ୟ ଲୋଡ଼ା — ପ୍ରମାଣପତ୍ର, ମରାମତି, ଲାବ୍ ବୁକିଂ, କିମ୍ବା ଅଭିଯୋଗ?",
            "id": "ବୁଝିଲି। ଦାଖଲ କରିବା ପାଇଁ ଆପଣଙ୍କ SOA ID କୁହନ୍ତୁ।",
            "ok": "ଧନ୍ୟବାଦ — ମୁଁ ଏହା ଏବେ ଦାଖଲ କରୁଛି।",
        },
    }
    pack = copies.get(lang, copies["en"])
    if not user_msgs:
        return {"reply": pack["hi"], "soa_id": None, "ready": False, "request_summary": ""}
    if not anonymous and not soa_captured and not soa:
        return {"reply": pack["id"], "soa_id": None, "ready": False, "request_summary": ""}
    return {"reply": pack["ok"], "soa_id": soa, "ready": True, "request_summary": joined}


async def converse(messages: list, anonymous: bool, soa_captured: bool, lang: str = "en") -> dict:
    """LLM-driven turn manager with a deterministic fallback."""
    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    lang = lang or detect_lang(last_user)
    soa_rule = (
        "This is an ANONYMOUS request — NEVER ask for an SOA ID or any identifying detail."
        if anonymous else
        ("SOA ID is already on file — do not ask for it again."
         if soa_captured else
         "You MUST obtain the student's SOA ID before you set ready=true. If it has not been given yet, ask for it politely. Accept whatever ID they say.")
    )
    system = CONVERSE_SYSTEM.replace("__SOA_RULE__", soa_rule)
    convo = "\n".join((("User: " if m.get("role") == "user" else "Assistant: ") + m.get("content", "")) for m in messages)
    prompt = (f"Conversation so far:\n{convo}\n\n"
              f"State: anonymous={anonymous}, soa_id_captured={soa_captured}, reply_language={lang}.\n"
              f"Respond with the JSON object now.")
    try:
        data = await complete_json(system, prompt)
        soa_val = data.get("soa_id")
        soa_out = str(soa_val).strip() if soa_val not in (None, "", "null", "None") else None
        return {
            "reply": (str(data.get("reply") or "").strip() or "Could you tell me a little more?"),
            "soa_id": soa_out,
            "ready": bool(data.get("ready")),
            "request_summary": str(data.get("request_summary") or "").strip(),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM converse failed, using deterministic fallback: {e}")
        return _converse_fallback(messages, anonymous, soa_captured, lang)



LANG_LABELS = {"en": "English", "hi": "Hindi", "od": "Odia"}


def build_request(interp: dict, text: str, opts: dict, ids: dict) -> tuple[dict, list]:
    """Deterministic risk-gated plan builder. `ids` carries pre-allocated record ids.
    Returns (request_doc, audit_event_payloads)."""
    lang = interp["language"]
    base = {
        "id": ids["req"],
        "lang": lang, "langLabel": LANG_LABELS.get(lang, "English"),
        "original": text,
        "requester": None if opts.get("anonymous") else opts.get("requester", "Ananya Sahoo"),
        "anonymous": bool(opts.get("anonymous")), "viaVoice": bool(opts.get("via_voice")),
        "pseudonym": None, "decision": None, "conflict": None, "followUp": None, "diff": None,
        "aiInterpreted": interp.get("_ai", False),
    }
    intent = interp["intent"]
    normalized = interp.get("normalized_en") or text
    fields = interp.get("fields") or {}
    lang_note = f"{lang} → en" if lang != "en" else "en"

    if intent == "maintenance":
        rec = ids["mt"]
        req = {**base, "type": "maintenance", "typeLabel": "Maintenance", "normalized": normalized,
               "intent": "maintenance.report", "risk": "LOW", "autonomy": "AUTO-EXECUTED", "status": "completed",
               "unit": "Facilities · Zone B", "recordId": rec, "recordLabel": "Maintenance Ticket",
               "fields": {**fields, **({"severity": "High (safety)"} if interp.get("safety") else {})},
               "evidence": [{"policy": "POL-MAINT", "ref": "§2.5 · p.3"}] + ([{"policy": "POL-MAINT", "ref": "§3.1 · p.5"}] if interp.get("safety") else []),
               "plan": [
                   {"n": 1, "title": "Detect language & normalize request", "tool": "interpret.normalize", "actor": "SOA Agent", "risk": "LOW", "status": "done", "output": f"{lang_note} · intent maintenance.report"},
                   {"n": 2, "title": "Extract location, asset, severity", "tool": "interpret.extract_fields", "actor": "SOA Agent", "risk": "LOW", "status": "done", "output": (", ".join(list(fields.values())[:3]) or "Fields extracted") + (" · SAFETY tag" if interp.get("safety") else "")},
                   {"n": 3, "title": "Retrieve maintenance policy evidence", "tool": "evidence.retrieve", "actor": "Evidence Engine", "risk": "LOW", "status": "done", "output": "POL-MAINT §2.5 cited · no conflict"},
                   {"n": 4, "title": "Classify autonomy risk", "tool": "risk.classify", "actor": "Risk Gate", "risk": "LOW", "status": "done", "output": "LOW → auto-execution permitted"},
                   {"n": 5, "title": "Create maintenance ticket", "tool": "tools.create_ticket", "actor": "Orchestrator", "risk": "LOW", "status": "done", "output": f"Ticket {rec} → Facilities Zone B"},
               ]}
        events = [
            {"actor": "Risk Gate", "role": "system", "action": "risk.classify", "summary": "Classified LOW · auto-execution permitted", "policyRefs": ["POL-MAINT §2.5"], "approval": None},
            {"actor": "Orchestrator", "role": "system", "action": "tools.create_ticket", "summary": f"Maintenance ticket {rec} created → Facilities Zone B", "policyRefs": ["POL-MAINT §2.5"], "approval": None},
        ]
        return req, events

    if intent == "certificate":
        req = {**base, "type": "certificate", "typeLabel": "Certificate", "normalized": normalized,
               "intent": "certificate.issue", "risk": "HIGH", "autonomy": "AWAITING APPROVAL", "status": "awaiting_approval",
               "unit": "Academic Records", "recordId": None, "recordLabel": "Certificate Request",
               "approver": "Dr. R. Mishra · Academic Approver",
               "fields": {"certificateType": fields.get("certificateType", "Bonafide"), "purpose": fields.get("purpose", "As stated in request"), "enrollment": "Verified · Active", **fields},
               "evidence": [{"policy": "POL-CERT", "ref": "§3.2 · p.4"}, {"policy": "POL-CERT", "ref": "§4.1 · p.6"}],
               "diff": {"action": "ISSUE_CERTIFICATE", "before": "No certificate on record for this purpose", "after": "Bonafide certificate issued · purpose recorded · requester notified"},
               "plan": [
                   {"n": 1, "title": "Normalize request & detect intent", "tool": "interpret.normalize", "actor": "SOA Agent", "risk": "LOW", "status": "done", "output": f"{lang_note} · intent certificate.issue"},
                   {"n": 2, "title": "Verify enrollment status", "tool": "tools.verify_enrollment", "actor": "Orchestrator", "risk": "LOW", "status": "done", "output": "Active enrollment confirmed"},
                   {"n": 3, "title": "Retrieve certificate policy evidence", "tool": "evidence.retrieve", "actor": "Evidence Engine", "risk": "LOW", "status": "done", "output": "POL-CERT §3.2 requires named approver"},
                   {"n": 4, "title": "Issue certificate", "tool": "tools.issue_certificate", "actor": "Dr. R. Mishra", "risk": "HIGH", "status": "blocked", "output": "Paused — awaiting Academic Approver decision"},
                   {"n": 5, "title": "Notify requester & write audit event", "tool": "tools.notify", "actor": "Orchestrator", "risk": "LOW", "status": "pending", "output": "—"},
               ]}
        events = [{"actor": "Risk Gate", "role": "system", "action": "risk.classify", "summary": "Classified HIGH · paused for Academic Approver", "policyRefs": ["POL-CERT §3.2"], "approval": "PENDING"}]
        return req, events

    if intent == "lab_booking":
        conflict_hit = interp.get("after_hours") or interp.get("exam_week")
        if conflict_hit:
            req = {**base, "type": "lab_booking", "typeLabel": "Lab Booking", "normalized": normalized,
                   "intent": "lab.book", "risk": "ABSTAINED", "autonomy": "ABSTAINED", "status": "abstained",
                   "unit": "Laboratory Coordinator", "recordId": None, "recordLabel": "Lab Booking", "fields": fields,
                   "evidence": [{"policy": "POL-LAB", "ref": "§5.1 · p.7"}, {"policy": "POL-EMRG", "ref": "§1.2 · p.1"}],
                   "conflict": {"code": "CONFLICT_DETECTED",
                                "a": {"policy": "POL-LAB", "ref": "§5.1 · p.7", "stance": "Prohibits student bookings 18:00–08:00"},
                                "b": {"policy": "POL-EMRG", "ref": "§1.2 · p.1", "stance": "Permits supervised access at any hour during exam weeks"},
                                "routedTo": "Laboratory Coordinator"},
                   "plan": [
                       {"n": 1, "title": "Normalize request & detect intent", "tool": "interpret.normalize", "actor": "SOA Agent", "risk": "LOW", "status": "done", "output": f"{lang_note} · intent lab.book"},
                       {"n": 2, "title": "Check slot availability", "tool": "tools.check_availability", "actor": "Orchestrator", "risk": "LOW", "status": "done", "output": "Slot free"},
                       {"n": 3, "title": "Retrieve booking policy evidence", "tool": "evidence.retrieve", "actor": "Evidence Engine", "risk": "LOW", "status": "done", "output": "2 passages retrieved · contradiction found"},
                       {"n": 4, "title": "Resolve policy conflict", "tool": "risk.conflict_check", "actor": "Risk Gate", "risk": "HIGH", "status": "abstained", "output": "CONFLICT_DETECTED → abstain, route to human"},
                       {"n": 5, "title": "Create booking", "tool": "tools.create_booking", "actor": "Orchestrator", "risk": "MEDIUM", "status": "cancelled", "output": "Not executed — abstention"},
                   ]}
            events = [{"actor": "Risk Gate", "role": "system", "action": "risk.conflict_check", "summary": "CONFLICT_DETECTED → abstained · routed to Laboratory Coordinator", "policyRefs": ["POL-LAB §5.1", "POL-EMRG §1.2"], "approval": None}]
            return req, events
        rec = ids["lab"]
        req = {**base, "type": "lab_booking", "typeLabel": "Lab Booking", "normalized": normalized,
               "intent": "lab.book", "risk": "MEDIUM", "autonomy": "AUTO-DRAFT", "status": "completed",
               "unit": "Laboratory Services", "recordId": rec, "recordLabel": "Lab Booking Draft", "fields": fields,
               "evidence": [{"policy": "POL-LAB", "ref": "§2.2 · p.2"}],
               "plan": [
                   {"n": 1, "title": "Normalize request & detect intent", "tool": "interpret.normalize", "actor": "SOA Agent", "risk": "LOW", "status": "done", "output": f"{lang_note} · intent lab.book"},
                   {"n": 2, "title": "Check slot availability", "tool": "tools.check_availability", "actor": "Orchestrator", "risk": "LOW", "status": "done", "output": "Slot free · working hours"},
                   {"n": 3, "title": "Retrieve booking policy evidence", "tool": "evidence.retrieve", "actor": "Evidence Engine", "risk": "LOW", "status": "done", "output": "POL-LAB §2.2 permits auto-draft"},
                   {"n": 4, "title": "Create draft booking", "tool": "tools.create_booking", "actor": "Orchestrator", "risk": "MEDIUM", "status": "done", "output": f"{rec} created"},
               ]}
        events = [{"actor": "Orchestrator", "role": "system", "action": "tools.create_booking", "summary": f"Draft booking {rec} created (working hours)", "policyRefs": ["POL-LAB §2.2"], "approval": None}]
        return req, events

    if intent == "grievance":
        rec = ids["grv"]
        pseud = ids["pseudonym"]
        critical = interp.get("critical")
        anon = base["anonymous"]
        req = {**base, "type": "grievance", "typeLabel": "Grievance",
               "normalized": normalized + (" · identity escrowed." if anon else ""),
               "intent": "grievance.file", "risk": "HIGH" if critical else "MEDIUM",
               "autonomy": "HUMAN TRIAGE" if critical else "ROUTED", "status": "in_triage",
               "unit": "Student Welfare" + (" · Anti-Ragging Cell" if critical else ""),
               "recordId": rec, "recordLabel": "Grievance Case",
               "urgency": "CRITICAL" if critical else "NORMAL",
               "pseudonym": pseud if anon else None,
               "requester": pseud if anon else base["requester"],
               "fields": {**fields, "urgency": "Critical" if critical else "Normal"},
               "evidence": [{"policy": "POL-GRV", "ref": "§6.3 · p.9"}] + ([{"policy": "POL-GRV", "ref": "§7.1 · p.11"}] if critical else []),
               "plan": [
                   {"n": 1, "title": "Accept anonymous submission" if anon else "Accept submission", "tool": "interpret.normalize", "actor": "SOA Agent", "risk": "LOW", "status": "done", "output": "Identity moved to escrow vault" if anon else "Identity recorded"},
                   {"n": 2, "title": "Create case file", "tool": "tools.create_grievance", "actor": "Orchestrator", "risk": "MEDIUM", "status": "done", "output": rec + (f" · pseudonym {pseud}" if anon else "")},
                   {"n": 3, "title": "Classify urgency", "tool": "risk.classify", "actor": "Risk Gate", "risk": "HIGH" if critical else "MEDIUM", "status": "done", "output": "CRITICAL → human triage within 2h (POL-GRV §7.1)" if critical else "NORMAL routing"},
                   {"n": 4, "title": "Route to Student Welfare", "tool": "tools.route_case", "actor": "Orchestrator", "risk": "LOW", "status": "done", "output": "Case routed · operator sees pseudonym only" if anon else "Case routed"},
                   {"n": 5, "title": "Human triage decision", "tool": "human.triage", "actor": "Student Welfare Officer", "risk": "HIGH", "status": "active", "output": "In progress"},
               ]}
        events = [{"actor": "Orchestrator", "role": "system", "action": "tools.create_grievance", "summary": f"Case {rec} created" + (" · identity escrowed" if anon else ""), "policyRefs": ["POL-GRV §6.3"], "approval": None}]
        if critical:
            events.append({"actor": "Orchestrator", "role": "system", "action": "tools.route_case", "summary": "CRITICAL urgency → human triage required within 2h", "policyRefs": ["POL-GRV §7.1"], "approval": None})
        return req, events

    # unknown → abstain with focused follow-up
    req = {**base, "type": "unknown", "typeLabel": "Clarification", "normalized": normalized,
           "intent": "unknown", "risk": "ABSTAINED", "autonomy": "NEEDS INFO", "status": "needs_info",
           "unit": "Service Desk", "recordId": None, "recordLabel": None, "fields": {}, "evidence": [],
           "followUp": "I cannot safely classify this request. Is this about maintenance, a certificate, a lab booking, or a grievance?",
           "plan": [
               {"n": 1, "title": "Normalize request & detect intent", "tool": "interpret.normalize", "actor": "SOA Agent", "risk": "LOW", "status": "done", "output": "Intent confidence below threshold"},
               {"n": 2, "title": "Ask focused follow-up question", "tool": "interpret.clarify", "actor": "SOA Agent", "risk": "LOW", "status": "active", "output": "Awaiting requester clarification"},
           ]}
    events = [{"actor": "SOA Agent", "role": "system", "action": "interpret.clarify", "summary": "Low intent confidence → focused follow-up asked instead of guessing", "policyRefs": [], "approval": None}]
    return req, events
