"""Tamper-evident, hash-chained audit ledger.

Integrity coverage: the SHA-256 chain hashes a CANONICAL JSON serialization of the
ENTIRE event document except the 'hash' field itself (sort_keys, compact separators).
That means every security-relevant field is protected: id, seq, requestId, ts, actorId,
actor, role, action, tool, inputSummary, outputSummary, policyRefs, risk, approval,
abstention, prevHash. Only 'hash' is excluded (it is the output).
"""
import json
import hashlib
from datetime import datetime, timezone

from db import db, next_counter

GENESIS = "GENESIS0" * 8


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(event: dict) -> str:
    e = {k: v for k, v in event.items() if k != "hash"}
    return json.dumps(e, sort_keys=True, separators=(",", ":"), default=str)


def chain_hash(prev: str, event: dict) -> str:
    return hashlib.sha256(f"{prev}|{canonical(event)}".encode()).hexdigest()


async def append_audit(events: list[dict], request_id: str) -> list[dict]:
    out = []
    for p in events:
        seq = await next_counter("EVT_SEQ")
        num = await next_counter("EVT")
        last = await db.audit_events.find_one(sort=[("seq", -1)], projection={"hash": 1})
        prev = last["hash"] if last else GENESIS
        evt = {
            "id": f"EVT-{num:04d}", "seq": seq,
            "requestId": p.get("requestId", request_id), "ts": p.get("ts") or now_iso(),
            "actorId": p.get("actorId", "system"), "actor": p.get("actor", "System"),
            "role": p.get("role", "system"), "action": p["action"], "tool": p.get("tool"),
            "inputSummary": p.get("inputSummary"), "outputSummary": p.get("summary") or p.get("outputSummary", ""),
            "summary": p.get("summary") or p.get("outputSummary", ""),
            "policyRefs": p.get("policyRefs", []), "risk": p.get("risk"),
            "approval": p.get("approval"), "abstention": p.get("abstention"),
            "interpreter": p.get("interpreter"), "prevHash": prev,
        }
        evt["hash"] = chain_hash(prev, evt)
        await db.audit_events.insert_one({**evt})
        evt.pop("_id", None)
        out.append(evt)
    return out


async def verify_chain() -> dict:
    events = await db.audit_events.find({}, {"_id": 0}).sort("seq", 1).to_list(5000)
    prev = GENESIS
    for i, e in enumerate(events):
        expect = chain_hash(prev, e)
        if e.get("prevHash") != prev or e.get("hash") != expect:
            return {"ok": False, "brokenAt": i, "event": e["id"], "count": len(events)}
        prev = e["hash"]
    return {"ok": True, "count": len(events)}


async def reconstruct_replay(request_id: str) -> dict:
    """Rebuild the historical decision path for a request PURELY from immutable audit events."""
    events = await db.audit_events.find({"requestId": request_id}, {"_id": 0}).sort("seq", 1).to_list(500)
    timeline = [{
        "seq": e["seq"], "ts": e["ts"], "actor": e["actor"], "role": e["role"],
        "action": e["action"], "tool": e.get("tool"), "detail": e.get("outputSummary"),
        "policyRefs": e.get("policyRefs", []), "risk": e.get("risk"),
        "approval": e.get("approval"), "abstention": e.get("abstention"),
        "hash": e.get("hash", "")[:12],
    } for e in events]
    return {"requestId": request_id, "events": len(events), "timeline": timeline}
