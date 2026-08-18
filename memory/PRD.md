# SOA (formerly SEVA-OS) — PRD

## Original Problem Statement
Full hackathon demo: voice/text intake (real Deepgram for English/Hindi, simulated Odia), Plan Canvas, risk-based approvals, evidence & conflict engine, SHA-256 hash-chained audit ledger, anonymous grievance, operations dashboard + Judge Mode. Demo JWT role switcher. AI layer via Qwen Cloud (`LLM_API_KEY`). DB: Supabase Postgres.

## Implemented (as of 2026-06)
- Dashboard, Intake (voice via Deepgram + text via Qwen Cloud LLM), Plan Canvas, Approvals, Grievances, Audit Ledger (SHA-256 chain), Judge Mode, Policies page
- Role switcher with localStorage persistence (key: `soa_role`)
- Case chat thread + AI reclassification (`POST /api/requests/{id}/messages`)
- Demo reset endpoint (`POST /api/reset`)
- 2026-06-16: Full rebrand SEVA-OS → SOA across frontend/backend; SOA university logo (`/frontend/public/soa-logo.webp`) in header + case report; removed leftover "Demo corpus" text from CaseReport.jsx; page title set to "SOA"; demo data reseeded

## Backlog
- Done: Printable Case Report (`/requests/:id/report` + `@media print` + Print report on RequestDetail)
- Done: Live ledger notifications in the header bell (latest audit events, refetch on open)
- Done: Auditor vault-open after role switch (seed requesterId + escrow identity + Switch to K. Das CTA)
- Done: Supabase migration (JSONB `documents` table, FastAPI via asyncpg)
- Done: Deepgram key wired locally (STT nova-2 + TTS aura-2)
- P2: One-tap Hindi language mode

## Notes
- Odia voice is MOCKED (simulated demo voice)
- Auth is demo JWT + RBAC in FastAPI, not Supabase Auth
- Rotate the Deepgram key if it was pasted into a chat log
