"""Policy corpus: ingestion (text / markdown / JSON), chunking, embeddings, semantic
retrieval, and GENERALIZED conflict detection (deterministic precedence + constrained LLM
contradiction evaluator). Adding two new contradictory active policies is enough to trigger
conflict detection — no workflow-specific Python edits required.
"""
import os
import re
import json
import uuid
import hashlib
import logging
from typing import List, Dict, Optional

from db import db
from audit import now_iso
import embeddings as emb

logger = logging.getLogger("soa.policy")


def _doc_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _chunk_text(text: str, size: int = 480) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= size:
        return [text] if text else []
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if len(cur) + len(sent) > size and cur:
            parts.append(cur.strip()); cur = ""
        cur += sent + " "
    if cur.strip():
        parts.append(cur.strip())
    return parts


async def ingest_policy(policy: dict) -> dict:
    """policy: {id,title,version,unit,effective,expiry?,accessClass,status,supersedes?,
    conflictsWith?,source?, sections:[{ref,text}] OR text:str}. Idempotent by id+version."""
    pid = policy["id"]
    sections = policy.get("sections")
    if not sections and policy.get("text"):
        sections = [{"ref": f"§{i+1}", "text": t} for i, t in enumerate(_chunk_text(policy["text"]))]
    sections = sections or []
    full_text = " ".join(s["text"] for s in sections)
    meta = {
        "id": pid, "title": policy["title"], "version": policy.get("version", "v1.0"),
        "unit": policy.get("unit", ""), "effective": policy.get("effective", ""),
        "expiry": policy.get("expiry"), "accessClass": policy.get("accessClass", "Internal"),
        "status": policy.get("status", "active"), "supersedes": policy.get("supersedes"),
        "conflictsWith": policy.get("conflictsWith"), "newer": policy.get("newer", False),
        "source": policy.get("source", "seed"), "sections": sections,
        "hash": policy.get("hash") or _doc_hash(full_text), "ingestedAt": now_iso(),
    }
    await db.policies.replace_one({"id": pid}, meta, upsert=True)
    await db.policy_chunks.delete_many({"policyId": pid})
    chunks = []
    for i, s in enumerate(sections):
        for j, piece in enumerate(_chunk_text(s["text"])):
            vec = emb.embed(f"{policy['title']} {s.get('ref','')}: {piece}")
            chunks.append({
                "id": f"{pid}::{i}:{j}", "policyId": pid, "policyTitle": policy["title"],
                "ref": s.get("ref", f"§{i+1}"), "text": piece, "version": meta["version"],
                "effective": meta["effective"], "status": meta["status"],
                "embedding": vec, "embModel": emb.get_provider().name,
            })
    if chunks:
        await db.policy_chunks.insert_many(chunks)
    return {"policyId": pid, "chunks": len(chunks), "embModel": emb.get_provider().name}


async def retrieve(query: str, k: int = 4, active_only: bool = True) -> List[Dict]:
    q = emb.embed(query)
    filt = {"status": "active"} if active_only else {}
    cursor = db.policy_chunks.find(filt, {"_id": 0})
    scored = []
    async for c in cursor:
        score = emb.cosine(q, c.get("embedding", []))
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, c in scored[:k]:
        c = {kk: vv for kk, vv in c.items() if kk != "embedding"}
        c["score"] = round(float(score), 4)
        out.append(c)
    return out


CONFLICT_SYSTEM = """You are a policy contradiction evaluator. You are given a requested action and two
policy passages that a semantic search returned as both relevant. Decide ONLY whether, for THIS request,
the two passages give directly contradictory instructions (one permits / one prohibits the same action in the
same circumstances). Do not pick a side. Return STRICT JSON only:
{"conflict": true|false, "confidence": 0.0-1.0, "reason": "one sentence"}"""


async def _llm_contradiction(action: str, a: Dict, b: Dict) -> Dict:
    try:
        from llm import complete_json
        prompt = (f"Requested action: {action}\n\nPassage A ({a['policyId']} {a['ref']}): {a['text']}\n\n"
                  f"Passage B ({b['policyId']} {b['ref']}): {b['text']}\n\nReturn the JSON now.")
        data = await complete_json(CONFLICT_SYSTEM, prompt)
        return {"conflict": bool(data.get("conflict")), "confidence": float(data.get("confidence", 0.5)),
                "reason": str(data.get("reason", ""))[:300], "evaluator": "llm"}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM contradiction eval failed: {e}")
        # deterministic fallback: explicit conflictsWith metadata
        return {"conflict": False, "confidence": 0.0, "reason": "evaluator unavailable", "evaluator": "fallback"}


async def detect_conflict(action: str, evidence: List[Dict]) -> Dict:
    """Generalized: examine retrieved evidence spanning >=2 policies; resolve by precedence where
    possible (explicit supersedes), else run the constrained LLM contradiction evaluator."""
    by_policy = {}
    for c in evidence:
        by_policy.setdefault(c["policyId"], c)  # keep top-scoring chunk per policy
    if len(by_policy) < 2:
        return {"conflict": False}
    top = list(by_policy.values())[:2]
    a, b = top[0], top[1]
    pa = await db.policies.find_one({"id": a["policyId"]}, {"_id": 0})
    pb = await db.policies.find_one({"id": b["policyId"]}, {"_id": 0})

    # Deterministic precedence: explicit supersession resolves the conflict (no abstain)
    if pa and pb:
        if pa.get("supersedes") == pb["id"] or pb.get("supersedes") == pa["id"]:
            return {"conflict": False, "resolved_by": "supersession"}
        if pa.get("status") != "active" or pb.get("status") != "active":
            return {"conflict": False, "resolved_by": "inactive_policy"}

    verdict = await _llm_contradiction(action, a, b)
    # explicit metadata reinforces a genuine conflict
    explicit = bool(pa and (pa.get("conflictsWith") or {}).get("policy") == b["policyId"]) or \
               bool(pb and (pb.get("conflictsWith") or {}).get("policy") == a["policyId"])
    if explicit and not verdict["conflict"]:
        verdict = {"conflict": True, "confidence": max(verdict["confidence"], 0.85),
                   "reason": verdict["reason"] or "Explicit policy conflict metadata present.",
                   "evaluator": verdict["evaluator"] + "+metadata"}
    if verdict["conflict"] and verdict["confidence"] >= 0.6:
        return {"conflict": True, "confidence": round(verdict["confidence"], 2),
                "policy_a": a["policyId"], "section_a": a["ref"], "stance_a": a["text"][:180],
                "policy_b": b["policyId"], "section_b": b["ref"], "stance_b": b["text"][:180],
                "reason": verdict["reason"], "evaluator": verdict["evaluator"]}
    return {"conflict": False}


async def list_policies() -> List[Dict]:
    return await db.policies.find({}, {"_id": 0, "sections": 1, "id": 1, "title": 1, "version": 1,
                                      "unit": 1, "effective": 1, "accessClass": 1, "status": 1,
                                      "supersedes": 1, "conflictsWith": 1, "newer": 1, "hash": 1}
                                   ).to_list(200)
