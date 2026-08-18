# Tech Decisions (ADRs)

> One entry per significant decision. Newest on top. Never delete — supersede.

## ADR-004: OpenAI-compatible LLM client
- **Date**: 2026-08-19
- **Status**: accepted
- **Context**: Previous private LLM wheel blocked a clean install and was not agentic without a hosted key. Gemini prepaid credits were empty.
- **Decision**: Tiny `backend/llm.py` OpenAI-compatible client. Default model `deepseek-v4-flash-0731`, `enable_thinking=false`, JSON object mode. Override with `LLM_MODEL` / `LLM_BASE_URL`.
- **Alternatives**: Gemini (credits empty); Groq; keep the private wheel.
- **Trade-off accepted**: Thinking models need `enable_thinking=false` or JSON extraction breaks.

## ADR-003: Deepgram stays behind FastAPI
- **Date**: 2026-08-17
- **Status**: accepted
- **Context**: Need live EN/HI voice without exposing the key to the browser.
- **Decision**: Keep existing `/api/voice/transcribe` + conversation TTS proxy. Key lives only in gitignored `backend/.env`.
- **Alternatives**: Browser-direct Deepgram (leaks key). Swap to nova-3 now (unneeded if nova-2 still 200s).
- **Trade-off accepted**: Conversation start is slow (Mumbai TTS round-trip + WAV base64).

## ADR-002: No RLS / no Supabase Auth
- **Date**: 2026-08-17
- **Status**: accepted
- **Context**: Demo already has JWT + RBAC. Migrating identity to Supabase Auth would rewrite login and the role switcher.
- **Decision**: Backend uses the database owner role. RLS stays off. Authz stays in `security.py`.
- **Alternatives**: Enable RLS + service_role only; map demo users into `auth.users`.
- **Trade-off accepted**: Anyone with `DATABASE_URL` can read everything. URL stays local-only.

## ADR-001: JSONB document bag instead of normalized tables
- **Date**: 2026-08-17
- **Status**: accepted
- **Context**: Whole backend is Motor `find`/`update`/`$inc`/`$regex`. A full SQL rewrite was out of scope.
- **Decision**: `public.documents(collection, id, doc jsonb)` + Motor-shaped adapter in `db.py`. `asyncpg` on the transaction pooler.
- **Alternatives**: supabase-py/PostgREST (awkward for atomic counters); SQLAlchemy models; keep Mongo.
- **Trade-off accepted**: Filter/sort in Python is O(collection). Fine for demo scale. Not a production data model.
