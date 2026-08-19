# SOA — Campus Service Assistant

Human-in-the-loop agent for campus services. A student talks or types; the model classifies the request and assigns the desk. A deterministic engine runs only allowlisted tools. A human signs anything consequential.

Built for **SOAIDEATHON-S1**: *Human-in-the-Loop Agentic AI for Autonomous Institutional Service Delivery*.

### Live demo

- App: https://soa-campus.vercel.app (public — no Vercel login)
- API: https://soa-api-209886947078.asia-south1.run.app/api/

Anyone can open the app. You do not need to grant Vercel access. Use the in-app **role switcher** — demo mode logs you in by role.

### What it does

| Workflow | Autonomy |
|---|---|
| Maintenance (leak, AC, plumber) | Auto-files a ticket |
| Bonafide / certificate | Files, then waits for Dr. R. Mishra |
| Lab booking | Books in hours; **abstains** on exam-week / after-hours conflict |
| Anonymous grievance | Triage + identity vault (auditor unlock only) |

Also: policy RAG from a seeded corpus, SHA-256 hash-chained audit ledger, Deepgram EN/HI voice, replies in English / Hindi / Odia. UI stays English.

Judge map and 5-minute script: [`docs/project/artifacts/PS_MAPPING.md`](docs/project/artifacts/PS_MAPPING.md) · [`docs/project/artifacts/DEMO_SCRIPT.md`](docs/project/artifacts/DEMO_SCRIPT.md)

### Stack

- Frontend: React 19 + CRA/CRACO + Tailwind
- Backend: FastAPI (`:8001`)
- DB: Supabase Postgres (JSONB `documents` table)
- LLM: OpenAI-compatible client in `backend/llm.py` (default `deepseek-v4-flash-0731`)
- Voice: Deepgram `nova-2` STT + Aura TTS, proxied by FastAPI

The model never executes approval-required tools. Certificates and vault unlocks stay human-gated.

### Quickstart

Needs Python 3.11+, Node 20, and a Postgres URL (Supabase transaction pooler works).

```bash
git clone https://github.com/BlueDocX/soa-campus-assistant.git
cd soa-campus-assistant
```

**Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-runtime.txt
cp .env.example .env          # fill in secrets — never commit .env
uvicorn server:app --host 127.0.0.1 --port 8001
```

Apply schema once (from repo root, after `supabase link` to your project):

```bash
supabase db push
```

**Frontend** (second terminal)

```bash
cd frontend
cp .env.example .env
yarn install                  # or: npm install
BROWSER=none PORT=3000 yarn start
```

- App: http://localhost:3000
- API: http://localhost:8001/api/

### Environment (names only)

`backend/.env`

| Name | Purpose |
|---|---|
| `DATABASE_URL` | Postgres URI (transaction pooler, `sslmode=require`) |
| `JWT_SECRET` | Long random string for demo JWTs |
| `ESCROW_KEY` | Fernet key for anonymous-identity vault |
| `LLM_API_KEY` | OpenAI-compatible key. Empty = keyword fallback |
| `LLM_BASE_URL` | Optional. Default is the Qwen Cloud Token Plan host |
| `LLM_MODEL` | Optional. Default `deepseek-v4-flash-0731` |
| `DEEPGRAM_API_KEY` | Optional. Empty = Demo Voice / voice 503 |
| `CORS_ORIGINS` | Comma-separated origins (`http://localhost:3000`, …) |
| `DEMO_MODE` | `true` for role switcher, reset, tamper demo |

`frontend/.env`

| Name | Purpose |
|---|---|
| `REACT_APP_BACKEND_URL` | Local: `http://localhost:8001`. Production: public API origin |

Copy from `backend/.env.example` and `frontend/.env.example`. Do not commit real values.

### Demo accounts

Role switcher (`POST /api/auth/demo-login`) is the judge path. Email login also works:

| Role | Email | Password | Who |
|---|---|---|---|
| student | student@soa.edu | Student@123 | Ananya Sahoo (`2214-CSE-031`) |
| approver | approver@soa.edu | Approver@123 | Dr. R. Mishra |
| operator | operator@soa.edu | Operator@123 | S. Behera |
| auditor | auditor@soa.edu | Auditor@123 | K. Das |
| admin | admin@soa.edu | Admin@123 | System Admin |

These are seeded demo credentials, not production users.

### 5-minute walk

1. Student: “AC leaking in Lab 201” → maintenance ticket, auto-executed.
2. Student: “I need a bonafide for my visa” → blocks → switch to Mishra → approve.
3. “Book Physics Lab 3 tonight, exam week” → abstain, two policy cites, no fake booking.
4. Anonymous grievance → switch to K. Das → vault unlock with justification.
5. Audit page → verify the SHA-256 chain.

### Repo layout

```
backend/          FastAPI, orchestrator, planner, audit, vault
frontend/         React UI
supabase/         Postgres migration (JSONB documents)
docs/project/     Architecture, ADRs, judge artifacts
tests/            Demo visibility, LLM client, Postgres adapter
```

### Tests

```bash
cd backend
source .venv/bin/activate
python ../tests/test_llm.py
python ../tests/test_pg_query.py
python ../tests/test_demo_visibility.py
```

Needs a live `DATABASE_URL` for the Postgres and demo-visibility suites.

### Deploy notes

- Frontend is a static CRA build. Set `REACT_APP_BACKEND_URL` **at build time**.
- Backend is FastAPI. Ship `backend/` with `requirements-runtime.txt` and the env table above.
- CORS must list the exact frontend origin. `*` will not work with credentialed calls.
- Frontend never talks to Postgres. Keys stay on the API.

### What this is not

- Not a free tool-loop agent. Classify → assign → allowlisted execute.
- Not Supabase Auth / RLS. Authz is FastAPI JWT + RBAC.
- Odia voice is labeled demo. Odia/Hindi **replies** are real.

### License

[MIT](LICENSE) © 2026 BlueDocX
