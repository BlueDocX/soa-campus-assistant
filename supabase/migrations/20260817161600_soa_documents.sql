-- SOA document store: one JSONB bag per former Mongo collection.
-- FastAPI is the auth boundary (demo JWT + RBAC). Backend connects as
-- the database owner, so RLS is intentionally not enabled.

create table if not exists public.documents (
  collection text not null,
  id text not null,
  doc jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (collection, id)
);

create index if not exists documents_collection_idx
  on public.documents (collection);

create index if not exists documents_doc_gin
  on public.documents using gin (doc jsonb_path_ops);

comment on table public.documents is
  'Motor-compatible JSONB bags for service_requests, audit_events, users, vault, policies, …';
