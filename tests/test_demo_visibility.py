#!/usr/bin/env python3
"""Reproduction: student must see seeded demo cases; auditor must unlock REQ-1045 vault."""
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
env_path = ROOT / "frontend" / ".env"
BACKEND = "http://127.0.0.1:8001"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BACKEND = line.split("=", 1)[1].strip()
            break
API = f"{BACKEND}/api"

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  OK  {name}")
    else:
        failed += 1
        print(f"  FAIL {name}{': ' + detail if detail else ''}")


def login(role):
    r = requests.post(f"{API}/auth/demo-login", json={"role": role}, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["token"], data["user"]


def auth_get(path, token):
    return requests.get(f"{API}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10)


def auth_post(path, token, payload):
    return requests.post(f"{API}{path}", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=10)


def main():
    print(f"Testing {API}")

    st, student = login("student")
    check("student role is student", student.get("role") == "student", json.dumps(student))
    sr = auth_get("/requests", st)
    check("student GET /requests 200", sr.status_code == 200, sr.text[:200])
    sreqs = sr.json() if sr.ok else []
    sids = {r.get("id") for r in sreqs}
    check("student sees seeded REQ-1042", "REQ-1042" in sids, f"got {sorted(sids)}")
    check("student sees own anonymous grievance REQ-1045", "REQ-1045" in sids, f"got {sorted(sids)}")
    check("student sees at least 5 demo requests", len(sreqs) >= 5, f"count={len(sreqs)}")

    at, auditor = login("auditor")
    check("auditor role is auditor", auditor.get("role") == "auditor", json.dumps(auditor))
    ar = auth_get("/requests", at)
    check("auditor GET /requests 200", ar.status_code == 200, ar.text[:200])
    areqs = ar.json() if ar.ok else []
    g = next((r for r in areqs if r.get("id") == "REQ-1045"), None)
    check("auditor sees REQ-1045", g is not None, f"ids={[r.get('id') for r in areqs]}")
    check("REQ-1045 is anonymous", bool(g and g.get("anonymous")), str(g))

    vault = auth_post("/vault/access", at, {"case_id": "REQ-1045", "justification": "Judge-mode identity check"})
    check("auditor vault unlock 200", vault.status_code == 200, f"{vault.status_code} {vault.text[:240]}")
    ident = (vault.json() or {}).get("identity") if vault.ok else None
    check("vault returns escrowed name", bool(ident and ident.get("name")), str(ident))

    denied = auth_post("/vault/access", st, {"case_id": "REQ-1045", "justification": "should fail"})
    check("student vault unlock 403", denied.status_code == 403, f"{denied.status_code} {denied.text[:160]}")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
