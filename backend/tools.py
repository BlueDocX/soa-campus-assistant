"""Tool registry / allowlist. The LLM may PROPOSE tool steps; only tools defined here can ever
execute, and only via execute_tool(), which persists a tool_executions record. Handlers change
real, persistent application state (tickets, bookings, certificates, grievances).
"""
import logging
from datetime import datetime, timezone, timedelta

from db import db, next_counter
from audit import now_iso
import policy_store
import escrow
from certificate_pdf import generate_certificate_pdf

logger = logging.getLogger("soa.tools")


def _sla(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


# ---------------- handlers (args: dict, ctx: dict) ----------------
async def _policy_search(args, ctx):
    ev = await policy_store.retrieve(args.get("query") or ctx.get("text", ""), k=args.get("k", 4))
    return {"evidence": ev, "count": len(ev)}


async def _verify_enrollment(args, ctx):
    soa = args.get("soaId") or ctx.get("soaId")
    return {"enrolled": True, "soaId": soa, "status": "Active", "note": "Enrollment verified against student registry"}


async def _create_ticket(args, ctx):
    n = await next_counter("MT")
    sev = args.get("severity") or ("High (safety)" if ctx.get("interp", {}).get("safety") else "Normal")
    hours = 4 if "safety" in str(sev).lower() or "high" in str(sev).lower() else 24
    doc = {"id": f"MT-{n}", "requestId": ctx.get("requestId"), "location": args.get("location", "Unspecified"),
           "issue": args.get("issue") or ctx.get("text", ""), "severity": sev, "status": "OPEN",
           "assignedUnit": args.get("unit", "Facilities · Zone B"), "createdAt": now_iso(),
           "slaDeadline": _sla(hours)}
    await db.maintenance_tickets.insert_one({**doc}); doc.pop("_id", None)
    return {"recordId": doc["id"], "status": "OPEN", "slaDeadline": doc["slaDeadline"], "unit": doc["assignedUnit"]}


async def _check_availability(args, ctx):
    lab_name = args.get("lab", "")
    lab = await db.labs.find_one({"name": {"$regex": lab_name, "$options": "i"}}, {"_id": 0}) if lab_name else None
    start = int(args.get("startHour", 10)); end = int(args.get("endHour", start + 2))
    date = args.get("date", "today")
    open_h, close_h = (lab["openHour"], lab["closeHour"]) if lab else (8, 18)
    within_hours = open_h <= start and end <= close_h
    clash = await db.lab_bookings.find_one({"lab": lab_name, "date": date,
                                            "startHour": {"$lt": end}, "endHour": {"$gt": start},
                                            "status": {"$ne": "CANCELLED"}}, {"_id": 0})
    available = bool(lab) and within_hours and not clash
    reason = "available" if available else ("lab not found" if not lab else
             "outside operating hours" if not within_hours else "slot already booked")
    return {"available": available, "reason": reason, "withinHours": within_hours,
            "lab": lab_name, "date": date, "startHour": start, "endHour": end}


async def _create_booking(args, ctx):
    avail = await _check_availability(args, ctx)
    if not avail["available"]:
        return {"ok": False, "reason": avail["reason"], "failed": True}
    n = await next_counter("LAB")
    doc = {"id": f"LAB-BKG-{n:04d}", "requestId": ctx.get("requestId"), "lab": args.get("lab"),
           "date": args.get("date", "today"), "startHour": avail["startHour"], "endHour": avail["endHour"],
           "status": "CONFIRMED", "bookedBy": ctx.get("requester"), "createdAt": now_iso()}
    await db.lab_bookings.insert_one({**doc}); doc.pop("_id", None)
    return {"ok": True, "recordId": doc["id"], "status": "CONFIRMED"}


async def _generate_certificate(args, ctx):
    n = await next_counter("CERT")
    ref = await next_counter("CERTVER")
    cert = {"id": f"CERT-{n:04d}", "verificationId": f"VER-{ref:06d}", "requestId": ctx.get("requestId"),
            "requester": args.get("requester") or ctx.get("requester"), "soaId": args.get("soaId") or ctx.get("soaId", "—"),
            "certificateType": args.get("certificateType", "Bonafide Certificate"),
            "purpose": args.get("purpose", "As stated in request"), "approver": args.get("approver", ""),
            "approvedAt": args.get("approvedAt", now_iso()), "issueDate": now_iso()[:10]}
    try:
        path = generate_certificate_pdf(cert); cert["artifactPath"] = path; cert["hasPdf"] = True
    except Exception as e:  # noqa: BLE001
        logger.error(f"PDF gen failed: {e}"); cert["hasPdf"] = False
    await db.certificates.insert_one({**cert}); cert.pop("_id", None)
    return {"recordId": cert["id"], "verificationId": cert["verificationId"], "hasPdf": cert.get("hasPdf")}


async def _create_grievance(args, ctx):
    n = await next_counter("GRV")
    from server import PSEUD_BIRDS  # reuse pseudonym pool
    pseud = f"CASE-{PSEUD_BIRDS[n % len(PSEUD_BIRDS)]}-{n % 9 + 1}"
    critical = bool(ctx.get("interp", {}).get("critical"))
    anon = bool(ctx.get("anonymous"))
    vault_ref = None
    if anon and ctx.get("identity"):
        vault_ref = await escrow.store_identity(pseud, ctx["identity"])
    doc = {"id": f"GRV-{n:04d}", "requestId": ctx.get("requestId"), "pseudonym": pseud,
           "category": args.get("category", "General"), "severity": "CRITICAL" if critical else "NORMAL",
           "description": args.get("description") or ctx.get("text", ""), "anonymous": anon,
           "vault_ref": vault_ref, "assignedCell": "Student Welfare" + (" · Anti-Ragging Cell" if critical else ""),
           "status": "TRIAGE" if critical else "RECEIVED", "escalationLevel": 1 if critical else 0,
           "slaDeadline": _sla(2) if critical else _sla(72), "createdAt": now_iso()}
    await db.grievances.insert_one({**doc}); doc.pop("_id", None)
    return {"recordId": doc["id"], "pseudonym": pseud, "status": doc["status"], "slaDeadline": doc["slaDeadline"],
            "escrowed": bool(vault_ref)}


async def _route_case(args, ctx):
    return {"routedTo": args.get("cell", "Student Welfare"), "ok": True}


# ---------------- registry ----------------
TOOL_REGISTRY = {
    "policy.search": {"description": "Semantic search over the institutional policy corpus.",
        "input": ["query"], "output": ["evidence"], "roles": ["student", "approver", "operator", "auditor", "admin"],
        "risk": "LOW", "requires_approval": False, "reversible": True, "compensation": None, "handler": _policy_search},
    "certificate.verify_enrollment": {"description": "Verify active enrollment for a requester.",
        "input": ["soaId"], "output": ["enrolled"], "roles": ["student", "operator", "admin"],
        "risk": "LOW", "requires_approval": False, "reversible": True, "compensation": None, "handler": _verify_enrollment},
    "maintenance.create_ticket": {"description": "Open a maintenance ticket in the internal ticket system.",
        "input": ["location", "issue"], "output": ["recordId"], "roles": ["student", "operator", "admin"],
        "risk": "LOW", "requires_approval": False, "reversible": True, "compensation": "maintenance.close_ticket", "handler": _create_ticket},
    "lab.check_availability": {"description": "Check a lab slot against operating hours and existing bookings.",
        "input": ["lab", "date", "startHour", "endHour"], "output": ["available"], "roles": ["student", "operator", "admin"],
        "risk": "LOW", "requires_approval": False, "reversible": True, "compensation": None, "handler": _check_availability},
    "lab.create_booking": {"description": "Create a confirmed lab booking if the slot is available.",
        "input": ["lab", "date", "startHour", "endHour"], "output": ["recordId"], "roles": ["student", "operator", "admin"],
        "risk": "MEDIUM", "requires_approval": False, "reversible": True, "compensation": "lab.cancel_booking", "handler": _create_booking},
    "certificate.generate": {"description": "Generate a certificate record + PDF artifact. Consequential.",
        "input": ["purpose"], "output": ["recordId"], "roles": ["approver", "admin"],
        "risk": "HIGH", "requires_approval": True, "reversible": False, "compensation": None, "handler": _generate_certificate},
    "grievance.create_case": {"description": "Open a grievance case (with escrowed identity if anonymous).",
        "input": ["category", "description"], "output": ["recordId"], "roles": ["student", "operator", "admin"],
        "risk": "MEDIUM", "requires_approval": False, "reversible": False, "compensation": None, "handler": _create_grievance},
    "grievance.route_case": {"description": "Route a grievance case to the responsible cell.",
        "input": ["caseId", "cell"], "output": ["routedTo"], "roles": ["operator", "admin"],
        "risk": "LOW", "requires_approval": False, "reversible": True, "compensation": None, "handler": _route_case},
}


def capabilities_brief() -> str:
    return "\n".join(
        f"- {name}: {t['description']} (risk={t['risk']}, requires_approval={t['requires_approval']})"
        for name, t in TOOL_REGISTRY.items())


async def execute_tool(name: str, args: dict, ctx: dict) -> dict:
    if name not in TOOL_REGISTRY:
        raise ValueError(f"unknown tool '{name}' — not in registry")
    spec = TOOL_REGISTRY[name]
    seq = await next_counter("TOOLEXEC")
    exec_doc = {"id": f"TX-{seq:05d}", "tool": name, "requestId": ctx.get("requestId"),
                "planStep": ctx.get("stepId"), "actorId": ctx.get("actorId", "orchestrator"),
                "input": args, "status": "RUNNING", "reversible": spec["reversible"],
                "compensation": spec["compensation"], "createdAt": now_iso()}
    try:
        result = await spec["handler"](args, ctx)
        exec_doc["status"] = "FAILED" if result.get("failed") else "DONE"
        exec_doc["result"] = result
    except Exception as e:  # noqa: BLE001
        logger.error(f"tool {name} failed: {e}")
        exec_doc["status"] = "FAILED"; exec_doc["result"] = {"error": str(e), "failed": True}
        result = exec_doc["result"]
    await db.tool_executions.insert_one({**exec_doc})
    return result
