"""Real per-case identity escrow. Sensitive complainant identity is encrypted (Fernet) and
stored in a SEPARATE collection keyed by an opaque vault ref. Operational grievance records
hold only the pseudonym + vault_ref. Never returns one static identity.
"""
import os
import json
import uuid
import logging
from typing import Optional

from cryptography.fernet import Fernet
from db import db
from audit import now_iso

logger = logging.getLogger("soa.escrow")
_key = os.environ.get("ESCROW_KEY")
_fernet = Fernet(_key.encode() if isinstance(_key, str) else _key) if _key else None


async def store_identity(case_id: str, identity: dict) -> str:
    vault_ref = f"vault_{uuid.uuid4().hex[:12]}"
    blob = json.dumps(identity).encode()
    enc = _fernet.encrypt(blob).decode() if _fernet else blob.decode()
    await db.identity_vault.insert_one({
        "vault_ref": vault_ref, "caseId": case_id, "ciphertext": enc,
        "encrypted": bool(_fernet), "createdAt": now_iso(),
    })
    return vault_ref


async def reveal_identity(case_id: str, accessor: dict, justification: str) -> Optional[dict]:
    doc = await db.identity_vault.find_one({"caseId": case_id}, {"_id": 0})
    if not doc:
        return None
    raw = doc["ciphertext"]
    try:
        data = json.loads(_fernet.decrypt(raw.encode()).decode()) if _fernet else json.loads(raw)
    except Exception as e:  # noqa: BLE001
        logger.error(f"escrow decrypt failed: {e}")
        return None
    return data
