"""Seeds users (RBAC), ingests policies into the RAG corpus (real embeddings), seeds labs,
and loads display fixtures. Idempotent-ish: `force` wipes demo collections and reseeds."""
import logging
from db import db
from audit import chain_hash, GENESIS, now_iso
from security import hash_password
import policy_store
from seed_data import POLICIES, SEED_REQUESTS, SEED_AUDIT, ESCROW_IDENTITY
import escrow

logger = logging.getLogger("soa.seed")

DEMO_USERS = [
    {"id": "USR-STU", "email": "student@soa.edu", "name": "Ananya Sahoo", "role": "student", "pw": "Student@123", "soaId": "2214-CSE-031"},
    {"id": "USR-APR", "email": "approver@soa.edu", "name": "Dr. R. Mishra", "role": "approver", "pw": "Approver@123"},
    {"id": "USR-OPS", "email": "operator@soa.edu", "name": "S. Behera", "role": "operator", "pw": "Operator@123"},
    {"id": "USR-AUD", "email": "auditor@soa.edu", "name": "K. Das", "role": "auditor", "pw": "Auditor@123"},
    {"id": "USR-ADM", "email": "admin@soa.edu", "name": "System Admin", "role": "admin", "pw": "Admin@123"},
]

LABS = [
    {"name": "Chemistry Lab 2", "openHour": 8, "closeHour": 18, "capacity": 30, "equipment": ["standard"]},
    {"name": "Physics Lab 3", "openHour": 8, "closeHour": 18, "capacity": 24, "equipment": ["oscilloscope", "standard"]},
    {"name": "CS Lab 1", "openHour": 8, "closeHour": 20, "capacity": 40, "equipment": ["workstations"]},
]

# Policy corpus with an explicit, GENUINE unresolved conflict (neither supersedes the other).
POLICY_DOCS = []
for p in POLICIES:
    d = dict(p)
    d.setdefault("status", "active")
    if d["id"] == "POL-EMRG":
        d["newer"] = True  # newer but an EXCEPTION, does not supersede the general rule
    POLICY_DOCS.append(d)


async def seed_all(force: bool = False):
    if force:
        for c in ("service_requests", "audit_events", "vault_log", "counters", "conversations",
                  "maintenance_tickets", "lab_bookings", "certificates", "grievances",
                  "identity_vault", "tool_executions", "policies", "policy_chunks", "users", "labs"):
            await db[c].delete_many({})

    # Users (RBAC)
    if await db.users.count_documents({}) == 0:
        for u in DEMO_USERS:
            await db.users.insert_one({"id": u["id"], "email": u["email"], "name": u["name"],
                                       "role": u["role"], "soaId": u.get("soaId"),
                                       "password_hash": hash_password(u["pw"]), "createdAt": now_iso()})
        logger.info("Seeded %d users", len(DEMO_USERS))

    # Labs
    if await db.labs.count_documents({}) == 0:
        for lab in LABS:
            await db.labs.insert_one({**lab})

    # Policies -> RAG corpus (real embeddings)
    if await db.policies.count_documents({}) == 0:
        for d in POLICY_DOCS:
            res = await policy_store.ingest_policy(d)
            logger.info("Ingested %s: %s chunks (%s)", d["id"], res["chunks"], res["embModel"])

    # Display fixtures + rebuilt hash chain (canonical hashing)
    if await db.service_requests.count_documents({}) == 0:
        await db.counters.insert_many([
            {"_id": "REQ", "value": 1046}, {"_id": "MT", "value": 2214}, {"_id": "CERT", "value": 117},
            {"_id": "CERTVER", "value": 400}, {"_id": "LAB", "value": 507}, {"_id": "GRV", "value": 931},
            {"_id": "EVT", "value": 10}, {"_id": "EVT_SEQ", "value": 10}, {"_id": "REQ_SEQ", "value": 6},
            {"_id": "TOOLEXEC", "value": 0},
        ])
        for i, r in enumerate(SEED_REQUESTS):
            await db.service_requests.insert_one({**r, "seq": i, "state": "COMPLETED"})
        prev = GENESIS
        for i, p in enumerate(SEED_AUDIT):
            evt = {"id": f"EVT-{i + 1:04d}", "seq": i + 1,
                   "requestId": p["requestId"], "ts": p["ts"], "actorId": "seed", "actor": p["actor"],
                   "role": p.get("role", "system"), "action": p["action"], "tool": None,
                   "inputSummary": None, "outputSummary": p["summary"], "summary": p["summary"],
                   "policyRefs": p.get("policyRefs", []), "risk": None, "approval": p.get("approval"),
                   "abstention": None, "interpreter": None, "prevHash": prev}
            evt["hash"] = chain_hash(prev, evt)
            prev = evt["hash"]
            await db.audit_events.insert_one(evt)
        logger.info("Seeded fixtures + rebuilt canonical hash chain")

    # Existing DBs from older seeds lack requesterId / vault rows — repair in place.
    seed_ids = [r["id"] for r in SEED_REQUESTS]
    await db.service_requests.update_many(
        {"id": {"$in": seed_ids}, "$or": [{"requesterId": None}, {"requesterId": {"$exists": False}}]},
        {"$set": {"requesterId": "USR-STU"}},
    )
    if await db.identity_vault.count_documents({"caseId": "REQ-1045"}) == 0:
        await escrow.store_identity("REQ-1045", ESCROW_IDENTITY)
        logger.info("Seeded escrow identity for REQ-1045")
