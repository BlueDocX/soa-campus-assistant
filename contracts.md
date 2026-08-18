# SOA — Backend Integration Contracts

## Storage: Supabase (PostgreSQL)
Tables (JSONB-heavy for MVP):
- `service_requests`: id(text pk REQ-####), type, type_label, lang, lang_label, original, normalized, requester, anonymous, pseudonym, via_voice, intent, risk, autonomy, status, unit, record_id, record_label, approver, urgency, fields(jsonb), evidence(jsonb), conflict(jsonb), diff(jsonb), follow_up, plan(jsonb), decision(jsonb), created_at
- `audit_events`: id(text pk EVT-####), request_id, ts, actor, role, action, summary, policy_refs(jsonb), approval, prev_hash, hash (SHA-256 chain)
- `vault_access_log`: id serial, case_id, accessed_by, role, justification, at
- `counters`: name pk, value (REQ/MT/CERT/LAB/GRV/EVT sequences)
Policies stay static server-side (seeded synthetic corpus, mirrors frontend mock).

## AI layer (Qwen Cloud OpenAI-compatible, default `deepseek-v4-flash-0731`):
POST pipeline inside `/api/requests` and `/api/conversation/turn`: LLM classifies intent + extracts fields + proposes plan as STRUCTURED JSON. Conversation auto-files a clear request to the matching desk. Deterministic orchestrator validates: allowlisted tools only, risk matrix (maintenance=LOW auto, certificate=HIGH approval, lab in-hours=MEDIUM auto-draft, lab after-hours/exam=CONFLICT abstain, grievance critical=HIGH triage), evidence from seeded corpus only. Keyword fallback if LLM fails. Replies follow the student's language (en/hi/od).

## Voice: Deepgram prerecorded REST (nova-2, detect_language) via backend proxy. Odia falls back to Demo Voice (labeled).

## API (all /api prefixed)
- POST /api/requests {text, anonymous, via_voice, requester_role} → full request obj (runs pipeline, persists, writes audit)
- GET /api/requests | GET /api/requests/{id}
- POST /api/requests/{id}/decision {decision: approve|reject, reason, approver} → updated request + audit
- GET /api/audit | POST /api/audit/verify → {ok, broken_at?, event?}
- POST /api/audit/tamper {index} (demo) | POST /api/audit/rollback {event_id, actor, role}
- GET /api/policies
- POST /api/vault/access {case_id, justification, actor, role} → identity (auditor only) + log + audit
- GET /api/vault/log
- POST /api/voice/transcribe (multipart audio, lang hint) → {transcript, language}
- POST /api/reset → wipe + reseed demo data
- GET /api/stats → dashboard aggregates

## Frontend replacement plan (mock.js removal)
- AppContext: replace localStorage state with axios calls to above endpoints; keep pipeline animation during POST /api/requests await
- Intake mic: MediaRecorder → POST /api/voice/transcribe for EN/HI; Odia stays simulated (labeled)
- Reset button → POST /api/reset then refetch
- Policies page reads GET /api/policies; Judge Mode static
