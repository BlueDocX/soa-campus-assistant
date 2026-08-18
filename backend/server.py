import os
import uuid
import base64
import logging
from pathlib import Path

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import httpx
from db import db
from audit import append_audit, verify_chain, reconstruct_replay, now_iso
from security import (get_current_user, require_perm, require_role, verify_password,
                      create_access_token, PERMISSIONS)
from orchestrator import interpret, converse, detect_lang  # noqa: F401
from llm import status as llm_status
import engine
import policy_store
import escrow
from seed import seed_all
from tools import TOOL_REGISTRY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("soa")

DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
PSEUD_BIRDS = ["MYNA", "KOEL", "HANSA", "SARUS", "BAYA", "SHAMA"]

app = FastAPI(title="SOA API")
api_router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    email: str
    password: str


class DemoLoginIn(BaseModel):
    role: str


class RequestIn(BaseModel):
    text: str
    anonymous: bool = False
    via_voice: bool = False


class DecisionIn(BaseModel):
    decision: str
    reason: str = ""


class MessageIn(BaseModel):
    text: str


class VaultIn(BaseModel):
    case_id: str
    justification: str


class TamperIn(BaseModel):
    index: int = 2


class RollbackIn(BaseModel):
    event_id: str


class ConvStartIn(BaseModel):
    anonymous: bool = False


def _public_user(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"],
            "soaId": u.get("soaId"), "perms": sorted(PERMISSIONS.get(u["role"], set()))}


# ---------- auth ----------
@api_router.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower().strip()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return {"token": create_access_token(user), "user": _public_user(user)}


@api_router.post("/auth/demo-login")
async def demo_login(body: DemoLoginIn):
    if not DEMO_MODE:
        raise HTTPException(403, "Demo login disabled")
    user = await db.users.find_one({"role": body.role})
    if not user:
        raise HTTPException(404, "No demo user for role")
    return {"token": create_access_token(user), "user": _public_user(user)}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return _public_user(user)


# ---------- policies ----------
@api_router.get("/policies")
async def get_policies(user: dict = Depends(get_current_user)):
    return await policy_store.list_policies()


@api_router.post("/policies")
async def ingest_policy_route(policy: dict, user: dict = Depends(require_perm("policy.manage"))):
    res = await policy_store.ingest_policy(policy)
    await append_audit([{"action": "policy.ingest", "actor": user["name"], "actorId": user["id"],
                         "role": user["role"], "summary": f"Policy {policy.get('id')} ingested \u00b7 {res['chunks']} chunks"}],
                       policy.get("id", "policy"))
    return res


@api_router.get("/policies/search")
async def search_policies(q: str, user: dict = Depends(get_current_user)):
    return await policy_store.retrieve(q, k=5)


# ---------- requests ----------
@api_router.get("/requests")
async def list_requests(user: dict = Depends(get_current_user)):
    q = {} if "request.read_all" in user["perms"] else {"requesterId": user["id"]}
    return await db.service_requests.find(q, {"_id": 0, "pendingArgs": 0}).sort([("seq", -1)]).to_list(500)


@api_router.get("/requests/{req_id}")
async def get_request(req_id: str, user: dict = Depends(get_current_user)):
    doc = await db.service_requests.find_one({"id": req_id}, {"_id": 0, "pendingArgs": 0})
    if not doc:
        raise HTTPException(404, "Request not found")
    if "request.read_all" not in user["perms"] and doc.get("requesterId") not in (user["id"], None):
        raise HTTPException(403, "Not authorized to view this request")
    return doc


@api_router.post("/requests")
async def create_request(body: RequestIn, user: dict = Depends(require_perm("request.create"))):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Empty request text")
    identity = {"name": user["name"], "email": user["email"], "soaId": user.get("soaId")} if body.anonymous else None
    opts = {"anonymous": body.anonymous, "via_voice": body.via_voice, "requester": user["name"],
            "soa_id": user.get("soaId"), "actor": user}
    return await engine.process_request(text, opts, identity=identity)


@api_router.post("/requests/{req_id}/decision")
async def decide(req_id: str, body: DecisionIn, user: dict = Depends(require_perm("approval.decide"))):
    doc = await db.service_requests.find_one({"id": req_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Request not found")
    if doc["status"] != "awaiting_approval":
        raise HTTPException(409, "Request is not awaiting approval")
    if body.decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be approve|reject")

    if body.decision == "approve":
        return await engine.execute_pending_certificate(doc, user, body.reason)

    plan = [dict(s) for s in doc["plan"]]
    for s in plan:
        if s.get("status") in ("blocked", "pending"):
            s["status"] = "cancelled"; s["output"] = "Rejected by approver"
    await db.service_requests.update_one({"id": req_id}, {"$set": {
        "status": "rejected", "state": "REJECTED", "autonomy": "HUMAN REJECTED", "plan": plan, "pendingTool": None,
        "decision": {"by": user["name"], "decision": "REJECTED", "reason": body.reason, "at": now_iso()}}})
    reason_txt = body.reason or "\u2014"
    await append_audit([{"action": "approval.reject", "actor": user["name"], "actorId": user["id"],
                         "role": "approver", "approval": "REJECTED", "policyRefs": ["POL-CERT \u00a73.2"],
                         "summary": f"REJECTED by {user['name']} \u00b7 reason: {reason_txt}"}], req_id)
    return await db.service_requests.find_one({"id": req_id}, {"_id": 0})


@api_router.post("/requests/{req_id}/messages")
async def add_message(req_id: str, body: MessageIn, user: dict = Depends(get_current_user)):
    doc = await db.service_requests.find_one({"id": req_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Request not found")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Empty message")
    msgs = doc.get("messages", [])
    msgs.append({"id": f"MSG-{len(msgs) + 1}", "author": user["name"], "role": user["role"], "text": text, "ts": now_iso()})
    if doc["status"] != "needs_info":
        await db.service_requests.update_one({"id": req_id}, {"$set": {"messages": msgs}})
        return await db.service_requests.find_one({"id": req_id}, {"_id": 0})
    combined = f"{doc['original']} \u2014 Clarification: {text}"
    opts = {"anonymous": doc.get("anonymous"), "via_voice": doc.get("viaVoice"), "requester": doc.get("requester"),
            "soa_id": user.get("soaId"), "actor": user, "force_id": req_id, "force_seq": doc.get("seq", 0)}
    identity = {"name": user["name"], "email": user["email"], "soaId": user.get("soaId")} if doc.get("anonymous") else None
    new = await engine.process_request(combined, opts, identity=identity)
    agent_txt = (f"Reclassified as {new['typeLabel']} \u00b7 outcome: {new.get('recordId') or new.get('autonomy')}."
                 if new["status"] != "needs_info" else new.get("followUp", "Still need more detail."))
    new_msgs = msgs + [{"id": f"MSG-{len(msgs) + 1}", "author": "SOA Agent", "role": "agent", "text": agent_txt, "ts": now_iso()}]
    await db.service_requests.update_one({"id": req_id}, {"$set": {"messages": new_msgs}})
    return await db.service_requests.find_one({"id": req_id}, {"_id": 0})


# ---------- audit ----------
@api_router.get("/audit")
async def list_audit(user: dict = Depends(get_current_user)):
    return await db.audit_events.find({}, {"_id": 0}).sort("seq", 1).to_list(3000)


@api_router.post("/audit/verify")
async def verify(user: dict = Depends(require_perm("audit.verify"))):
    return await verify_chain()


@api_router.get("/audit/replay/{req_id}")
async def replay(req_id: str, user: dict = Depends(get_current_user)):
    return await reconstruct_replay(req_id)


@api_router.post("/audit/tamper")
async def tamper(body: TamperIn, user: dict = Depends(require_perm("audit.tamper"))):
    if not DEMO_MODE:
        raise HTTPException(403, "Tamper simulation only in demo mode")
    events = await db.audit_events.find({}).sort("seq", 1).to_list(3000)
    if not events:
        raise HTTPException(404, "No events")
    idx = min(max(body.index, 0), len(events) - 1)
    t = events[idx]
    await db.audit_events.update_one({"id": t["id"]}, {"$set": {
        "summary": t["summary"] + " [TAMPERED]", "outputSummary": t.get("outputSummary", "") + " [TAMPERED]"}})
    return {"tampered": t["id"], "index": idx}


@api_router.post("/audit/rollback")
async def rollback(body: RollbackIn, user: dict = Depends(require_role("auditor", "admin"))):
    evt = await db.audit_events.find_one({"id": body.event_id}, {"_id": 0})
    if not evt:
        raise HTTPException(404, "Event not found")
    tool = evt.get("tool")
    spec = TOOL_REGISTRY.get(tool or "", {})
    reversible = spec.get("reversible", False) and bool(spec.get("compensation"))
    if reversible:
        summary = f"Compensating action '{spec['compensation']}' recorded for {evt['id']} ({tool}) \u2014 reversible; history preserved"
        action = "tools.compensate"
    else:
        summary = f"{evt['id']} ({tool or evt['action']}) is NON-REVERSIBLE \u2014 remediation required rather than rollback"
        action = "tools.remediation_required"
    created = await append_audit([{"action": action, "actor": user["name"], "actorId": user["id"],
                                   "role": user["role"], "tool": spec.get("compensation"), "summary": summary}],
                                 evt["requestId"])
    return {**created[0], "reversible": reversible}


# ---------- vault ----------
@api_router.post("/vault/access")
async def vault_access(body: VaultIn, user: dict = Depends(require_perm("vault.access"))):
    if not body.justification.strip():
        raise HTTPException(400, "Justification required (POL-GRV \u00a76.3)")
    identity = await escrow.reveal_identity(body.case_id, user, body.justification.strip())
    if identity is None:
        raise HTTPException(404, "No escrowed identity for this case")
    entry = {"caseId": body.case_id, "by": user["name"], "role": user["role"],
             "justification": body.justification.strip(), "at": now_iso()}
    await db.vault_log.insert_one({**entry}); entry.pop("_id", None)
    await append_audit([{"action": "vault.access", "actor": user["name"], "actorId": user["id"], "role": user["role"],
                         "policyRefs": ["POL-GRV \u00a76.3"],
                         "summary": f"Identity vault accessed for {body.case_id} \u00b7 justification: {body.justification.strip()}"}],
                       body.case_id)
    return {"identity": identity, "log": entry}


@api_router.get("/vault/log")
async def vault_log_route(user: dict = Depends(get_current_user)):
    return await db.vault_log.find({}, {"_id": 0}).sort("at", 1).to_list(500)


# ---------- certificate artifact ----------
@api_router.get("/certificates/{cert_id}/pdf")
async def cert_pdf(cert_id: str, user: dict = Depends(get_current_user)):
    cert = await db.certificates.find_one({"id": cert_id}, {"_id": 0})
    if not cert or not cert.get("artifactPath") or not os.path.exists(cert["artifactPath"]):
        raise HTTPException(404, "Certificate artifact not found")
    return FileResponse(cert["artifactPath"], media_type="application/pdf", filename=f"{cert_id}.pdf")


# ---------- voice ----------
async def _dg_transcribe(data: bytes, content_type: Optional[str], lang: Optional[str] = None) -> dict:
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        raise HTTPException(503, "Voice provider not configured")
    params = {"model": "nova-2", "smart_format": "true"}
    if lang in ("hi", "en", "od"):
        params["language"] = lang
    else:
        params["detect_language"] = "true"
    async with httpx.AsyncClient(timeout=45) as hc:
        resp = await hc.post("https://api.deepgram.com/v1/listen", params=params, content=data,
                             headers={"Authorization": f"Token {key}", "Content-Type": content_type or "audio/webm"})
    if resp.status_code != 200:
        logger.error(f"Deepgram STT {resp.status_code}: {resp.text[:200]}")
        raise HTTPException(502, f"Voice provider error ({resp.status_code})")
    j = resp.json()
    alt = j["results"]["channels"][0]["alternatives"][0]
    detected = j["results"]["channels"][0].get("detected_language") or lang or "en"
    return {"transcript": alt.get("transcript", ""), "language": detected, "confidence": alt.get("confidence", 0)}


async def _dg_tts(text: str) -> bytes:
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        raise HTTPException(503, "Voice provider not configured")
    async with httpx.AsyncClient(timeout=45) as hc:
        resp = await hc.post("https://api.deepgram.com/v1/speak",
                             params={"model": "aura-2-thalia-en", "encoding": "linear16", "container": "wav"},
                             headers={"Authorization": f"Token {key}", "Content-Type": "application/json"},
                             json={"text": (text or "")[:1800]})
    if resp.status_code != 200:
        raise HTTPException(502, f"TTS provider error ({resp.status_code})")
    return resp.content


async def _tts_b64(text: str) -> Optional[str]:
    try:
        return base64.b64encode(await _dg_tts(text)).decode("ascii")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"TTS skipped: {e}")
        return None


@api_router.post("/voice/transcribe")
async def transcribe(audio: UploadFile = File(...), lang: Optional[str] = Form(None),
                     user: dict = Depends(get_current_user)):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty audio")
    return await _dg_transcribe(data, audio.content_type, lang)


# ---------- conversational assistant ----------
@api_router.post("/conversation/start")
async def conversation_start(body: ConvStartIn, user: dict = Depends(require_perm("conversation.use"))):
    sid = f"CONV-{uuid.uuid4().hex[:8].upper()}"
    greeting = ("Hi! I'm the SOA service assistant \u2014 you can type or talk to me. "
                + ("You're in anonymous mode, so I won't ask for any identifying details. " if body.anonymous else "")
                + "What do you need help with today \u2014 a certificate, a maintenance issue, a lab booking, or a grievance?")
    sess = {"id": sid, "anonymous": bool(body.anonymous), "requester": user["name"], "requesterId": user["id"],
            "soaId": user.get("soaId"), "status": "active", "capturedSoaId": None, "requestId": None,
            "messages": [{"role": "agent", "content": greeting, "ts": now_iso()}],
            "createdAt": now_iso(), "updatedAt": now_iso()}
    await db.conversations.insert_one({**sess}); sess.pop("_id", None)
    return {**sess, "audioBase64": await _tts_b64(greeting)}


@api_router.get("/conversation/{sid}")
async def conversation_get(sid: str, user: dict = Depends(get_current_user)):
    doc = await db.conversations.find_one({"id": sid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Conversation not found")
    return doc


@api_router.post("/conversation/turn")
async def conversation_turn(sessionId: str = Form(...), text: Optional[str] = Form(None),
                            speak: bool = Form(True), audio: Optional[UploadFile] = File(None),
                            user: dict = Depends(require_perm("conversation.use"))):
    sess = await db.conversations.find_one({"id": sessionId}, {"_id": 0})
    if not sess:
        raise HTTPException(404, "Conversation not found")
    if sess.get("status") == "completed":
        raise HTTPException(409, "Conversation already completed")
    user_text = (text or "").strip()
    lang = "en"
    if audio is not None:
        data = await audio.read()
        if data:
            tr = await _dg_transcribe(data, audio.content_type, None)
            user_text = (tr.get("transcript") or "").strip()
            lang = tr.get("language", "en")
    if not user_text:
        raise HTTPException(400, "No input detected")
    if lang == "en":
        lang = detect_lang(user_text)

    messages = sess.get("messages", [])
    messages.append({"role": "user", "content": user_text, "ts": now_iso(), "lang": lang})
    anonymous = bool(sess.get("anonymous"))
    soa_id = sess.get("capturedSoaId") or (None if anonymous else sess.get("soaId"))

    request_id = sess.get("requestId")
    status = "active"
    reply = None
    ready = False
    identity_ok = anonymous or bool(soa_id)
    joined = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")

    if identity_ok and not request_id:
        identity = {"name": user["name"], "email": user["email"], "soaId": user.get("soaId")} if anonymous else None
        opts = {"anonymous": anonymous, "via_voice": True, "requester": user["name"], "soa_id": soa_id, "actor": user}
        created = await engine.process_request(joined, opts, identity=identity)
        if created.get("status") == "needs_info":
            await db.service_requests.delete_one({"id": created["id"]})
        else:
            request_id = created["id"]
            status = "completed"
            lang = created.get("lang") or lang
            reply = _confirmation_line(created, soa_id, anonymous, lang)

    if status != "completed":
        decision = await converse(messages, anonymous, bool(soa_id), lang)
        if decision.get("soa_id") and not anonymous:
            soa_id = str(decision["soa_id"]).strip()
        ready = bool(decision.get("ready"))
        reply = decision.get("reply") or reply or "Could you tell me a little more?"
        if not anonymous and not soa_id:
            ready = False
            if lang == "hi":
                reply = "फाइल करने से पहले अपना SOA ID बताइए।"
            elif lang == "od":
                reply = "ଦାଖଲ କରିବା ପୂର୍ବରୁ ଆପଣଙ୍କ SOA ID କୁହନ୍ତୁ।"
            elif "soa" not in reply.lower():
                reply = "Before I can file this, could you please tell me your SOA ID?"
        if ready and not request_id:
            summary = decision.get("request_summary") or joined
            identity = {"name": user["name"], "email": user["email"], "soaId": user.get("soaId")} if anonymous else None
            opts = {"anonymous": anonymous, "via_voice": True, "requester": user["name"], "soa_id": soa_id, "actor": user}
            created = await engine.process_request(summary, opts, identity=identity)
            if created.get("status") == "needs_info":
                await db.service_requests.delete_one({"id": created["id"]})
                reply = {
                    "hi": "यह चार सेवाओं में साफ़ नहीं बैठा। मरम्मत, प्रमाणपत्र, लैब बुकिंग, या शिकायत?",
                    "od": "ଏହା ଚାରି ସେବା ମଧ୍ୟରୁ ସ୍ପଷ୍ଟ ନୁହେଁ। ମରାମତି, ପ୍ରମାଣପତ୍ର, ଲାବ୍ ବୁକିଂ, କିମ୍ବା ଅଭିଯୋଗ?",
                }.get(lang, "I couldn't confidently place this in one of our services. Is it maintenance, a certificate, a lab booking, or a grievance?")
            else:
                request_id = created["id"]
                status = "completed"
                reply = _confirmation_line(created, soa_id, anonymous, created.get("lang") or lang)

    messages.append({"role": "agent", "content": reply, "ts": now_iso()})
    await db.conversations.update_one({"id": sessionId}, {"$set": {
        "messages": messages, "capturedSoaId": soa_id, "status": status, "requestId": request_id, "updatedAt": now_iso()}})
    return {"sessionId": sessionId, "transcript": user_text, "reply": reply,
            "audioBase64": (await _tts_b64(reply) if speak else None), "status": status,
            "requestId": request_id, "done": status == "completed", "soaId": soa_id, "messages": messages}


def _confirmation_line(req, soa_id, anonymous, lang="en"):
    t = req["typeLabel"]; st = req["status"]; rec = req.get("recordId")
    approver = req.get("approver", "the approver")
    if lang == "hi":
        if st == "completed" and rec:
            return f"हो गया! आपका {t} अनुरोध {rec} पर दर्ज है। रिपोर्ट खोलें।"
        if st == "awaiting_approval":
            return f"धन्यवाद। आपका {t} अनुरोध {req['id']} दर्ज है और {approver} की मंज़ूरी का इंतज़ार है।"
        if st == "abstained":
            return f"मैंने आपका {t} अनुरोध {req['id']} दर्ज किया, लेकिन नीति में टकराव मिला — अनुमान की जगह इसे इंसान के पास भेजा है।"
        if st == "in_triage":
            extra = " आपकी पहचान सुरक्षित वॉल्ट में है।" if anonymous else ""
            return f"आपकी शिकायत {rec or req['id']} दर्ज है और जाँच के लिए भेज दी गई है।{extra}"
        return f"आपका {t} अनुरोध {req['id']} दर्ज हो गया है।"
    if lang == "od":
        if st == "completed" and rec:
            return f"ହୋଇଗଲା! ଆପଣଙ୍କ {t} ଅନୁରୋଧ {rec} ରେ ଦାଖଲ। ରିପୋର୍ଟ ଖୋଲନ୍ତୁ।"
        if st == "awaiting_approval":
            return f"ଧନ୍ୟବାଦ। ଆପଣଙ୍କ {t} ଅନୁରୋଧ {req['id']} ଦାଖଲ ଏବଂ {approver} ଙ୍କ ଅନୁମୋଦନ ଅପେକ୍ଷାରେ।"
        if st == "abstained":
            return f"ମୁଁ {t} ଅନୁରୋଧ {req['id']} ଦାଖଲ କଲି, କିନ୍ତୁ ନୀତି ଦ୍ୱନ୍ଦ ମିଳିଲା — ଅନୁମାନ ନକରି ମଣିଷ ପାଖକୁ ପଠାଇଛି।"
        if st == "in_triage":
            extra = " ଆପଣଙ୍କ ପରିଚୟ ସୁରକ୍ଷିତ ଭଲ୍ଟରେ ଅଛି।" if anonymous else ""
            return f"ଆପଣଙ୍କ ଅଭିଯୋଗ {rec or req['id']} ଦାଖଲ ଏବଂ ଯାଞ୍ଚ ପାଇଁ ପଠାଯାଇଛି।{extra}"
        return f"ଆପଣଙ୍କ {t} ଅନୁରୋଧ {req['id']} ଦାଖଲ ହୋଇଛି।"
    idtxt = f" I've noted your SOA ID {soa_id}." if soa_id and not anonymous else ""
    if st == "completed" and rec:
        return f"All set!{idtxt} Your {t} request is confirmed and filed as {rec}. Open the report for details."
    if st == "awaiting_approval":
        return f"Thank you.{idtxt} Your {t} request {req['id']} is filed and now awaiting approval from {approver}."
    if st == "abstained":
        return f"I logged your {t} request as {req['id']}, but found a policy conflict, so I routed it to a human instead of guessing."
    if st == "in_triage":
        return f"Your grievance is filed as {rec or req['id']} and routed for human triage." + (" Your identity is kept in a secure escrow vault." if anonymous else idtxt)
    return f"Your {t} request {req['id']} has been filed.{idtxt}"


# ---------- analytics ----------
@api_router.get("/stats")
async def stats(user: dict = Depends(get_current_user)):
    reqs = await db.service_requests.find({}, {"_id": 0, "status": 1, "risk": 1, "autonomy": 1, "createdAt": 1}).to_list(2000)
    total = len(reqs)

    def cnt(pred):
        return sum(1 for r in reqs if pred(r))

    def pct(n):
        return round(100 * n / total) if total else 0

    pending = cnt(lambda r: r["status"] == "awaiting_approval")
    triage = cnt(lambda r: r["status"] == "in_triage")
    auto = cnt(lambda r: r.get("autonomy") in ("AUTO-EXECUTED", "AUTO-DRAFT"))
    human_appr = cnt(lambda r: r.get("autonomy") == "HUMAN APPROVED")
    human = cnt(lambda r: r.get("autonomy") in ("HUMAN APPROVED", "AWAITING APPROVAL", "HUMAN TRIAGE"))
    abstained = cnt(lambda r: r["status"] in ("abstained", "needs_info"))
    from collections import Counter
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    autoc, humanc = Counter(), Counter()
    for r in reqs:
        try:
            mi = int(r["createdAt"][5:7]) - 1
        except Exception:
            mi = 6
        (autoc if r.get("autonomy") in ("AUTO-EXECUTED", "AUTO-DRAFT") else humanc)[mi] += 1
    return {
        "total": total, "pending": pending, "triage": triage,
        "completed": cnt(lambda r: r["status"] == "completed"), "abstained": abstained,
        "rejected": cnt(lambda r: r["status"] == "rejected"), "escalated": triage,
        "auditCount": await db.audit_events.count_documents({}),
        "autonomyMix": {"auto": pct(auto), "human": pct(human)},
        "progress": {"autoResolved": pct(auto), "humanApproved": pct(human_appr + pending),
                     "abstained": pct(abstained), "escalated": pct(triage)},
        "riskMix": {k: cnt(lambda r, k=k: r.get("risk") == k) for k in ("LOW", "MEDIUM", "HIGH", "CRITICAL")},
        "volume": {"months": months, "auto": [autoc.get(i, 0) for i in range(12)],
                   "human": [humanc.get(i, 0) for i in range(12)]},
    }


@api_router.post("/reset")
async def reset_demo(user: dict = Depends(get_current_user)):
    if not DEMO_MODE:
        raise HTTPException(403, "Reset only in demo mode")
    await seed_all(force=True)
    return {"ok": True, "message": "Demo data reseeded"}


@api_router.get("/")
async def root():
    return {"message": "SOA API", "status": "governed", "demoMode": DEMO_MODE, **llm_status()}


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o for o in os.environ.get('CORS_ORIGINS', '').split(',') if o] or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await seed_all()


@app.on_event("shutdown")
async def shutdown():
    from db import close_pool
    await close_pool()
