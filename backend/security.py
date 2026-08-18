"""Real JWT auth + server-side RBAC. Identity/role derive ONLY from the verified token."""
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db import db

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-insecure-secret-change-me")
JWT_ALG = "HS256"
TOKEN_TTL_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)

# Role -> permission set (coarse RBAC; structured so ABAC can layer on later)
PERMISSIONS = {
    "student":  {"request.create", "request.read_own", "grievance.create", "conversation.use"},
    "approver": {"request.read_all", "approval.decide", "conversation.use"},
    "operator": {"request.read_all", "ticket.work", "grievance.work", "conversation.use"},
    "auditor":  {"request.read_all", "audit.read", "audit.verify", "vault.access", "conversation.use"},
    "admin":    {"request.read_all", "policy.manage", "admin.reset", "audit.verify", "audit.tamper",
                 "approval.decide", "vault.access", "conversation.use"},
}


def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return pwd_context.verify(p, h)
    except Exception:
        return False


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["id"], "role": user["role"], "name": user["name"],
        "email": user["email"], "iat": now, "exp": now + timedelta(hours=TOKEN_TTL_HOURS),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


async def get_current_user(cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> dict:
    if cred is None or not cred.credentials:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except Exception:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User no longer exists")
    user["perms"] = sorted(PERMISSIONS.get(user["role"], set()))
    return user


def require_perm(perm: str):
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if perm not in PERMISSIONS.get(user["role"], set()):
            raise HTTPException(403, f"Role '{user['role']}' lacks permission '{perm}'")
        return user
    return _dep


def require_role(*roles: str):
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, f"Requires role in {roles}")
        return user
    return _dep
