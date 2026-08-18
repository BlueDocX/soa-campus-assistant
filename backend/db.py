"""Supabase/Postgres document store with a Motor-shaped API.

Demo-scale collections are filtered/sorted in Python after a collection
read. Atomic counters use INSERT … ON CONFLICT so hash-chain seq stays
safe under concurrent writes.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from typing import Any, Optional

import asyncpg

_pool: Optional[asyncpg.Pool] = None
_lock = asyncio.Lock()


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (Supabase Postgres pooler URI)")
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool
    async with _lock:
        if _pool is not None:
            return _pool
        _pool = await asyncpg.create_pool(
            _database_url(),
            min_size=1,
            max_size=8,
            statement_cache_size=0,  # pgbouncer transaction mode
        )
        return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


class _Client:
    def close(self) -> None:
        return


client = _Client()


def _doc_id(doc: dict) -> str:
    for key in ("id", "_id", "vault_ref"):
        val = doc.get(key)
        if val not in (None, ""):
            return str(val)
    return uuid.uuid4().hex


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return json.loads(value)


def _dump(doc: dict) -> str:
    return json.dumps(doc, default=str)


def match(doc: dict, filt: Optional[dict]) -> bool:
    if not filt:
        return True
    if "$and" in filt:
        if not all(match(doc, part) for part in filt["$and"]):
            return False
        rest = {k: v for k, v in filt.items() if k != "$and"}
        return match(doc, rest) if rest else True
    if "$or" in filt:
        if not any(match(doc, part) for part in filt["$or"]):
            return False
        rest = {k: v for k, v in filt.items() if k != "$or"}
        return match(doc, rest) if rest else True
    for key, expected in filt.items():
        if key in ("$and", "$or"):
            continue
        actual = doc.get(key)
        if isinstance(expected, dict) and any(str(k).startswith("$") for k in expected):
            if not _match_ops(actual, expected, key in doc):
                return False
        elif actual != expected:
            return False
    return True


def _match_ops(actual: Any, ops: dict, present: bool) -> bool:
    if "$exists" in ops and bool(present) != bool(ops["$exists"]):
        return False
    if "$in" in ops and actual not in ops["$in"]:
        return False
    if "$ne" in ops and actual == ops["$ne"]:
        return False
    if "$lt" in ops and not (actual is not None and actual < ops["$lt"]):
        return False
    if "$lte" in ops and not (actual is not None and actual <= ops["$lte"]):
        return False
    if "$gt" in ops and not (actual is not None and actual > ops["$gt"]):
        return False
    if "$gte" in ops and not (actual is not None and actual >= ops["$gte"]):
        return False
    if "$regex" in ops:
        flags = re.I if "i" in str(ops.get("$options", "")) else 0
        if actual is None or re.search(str(ops["$regex"]), str(actual), flags) is None:
            return False
    return True


def project(doc: dict, projection: Optional[dict]) -> dict:
    if not projection:
        return dict(doc)
    include = [k for k, v in projection.items() if k != "_id" and v]
    exclude = [k for k, v in projection.items() if k != "_id" and not v]
    if include:
        out = {k: doc[k] for k in include if k in doc}
        if "id" in doc and "id" not in out and projection.get("id", 1):
            pass
    else:
        out = {k: v for k, v in doc.items() if k not in exclude}
    if projection.get("_id", 0) == 0:
        out.pop("_id", None)
    elif projection.get("_id") == 1 and "_id" in doc:
        out["_id"] = doc["_id"]
    return out


def sort_docs(docs: list[dict], spec: Any) -> list[dict]:
    if not spec:
        return docs
    if isinstance(spec, str):
        pairs = [(spec, 1)]
    elif isinstance(spec, tuple) and spec and isinstance(spec[0], str):
        pairs = [spec]
    else:
        pairs = list(spec)
    out = list(docs)
    for key, direction in reversed(pairs):
        rev = int(direction) < 0
        out.sort(key=lambda d, k=key: (d.get(k) is None, d.get(k)), reverse=rev)
    return out


class Cursor:
    def __init__(self, collection: "Collection", filt: Optional[dict], projection: Optional[dict]):
        self._collection = collection
        self._filt = filt or {}
        self._projection = projection
        self._sort = None
        self._limit = None

    def sort(self, *args):
        if len(args) == 1:
            self._sort = args[0]
        elif len(args) >= 2:
            self._sort = [(args[0], args[1])]
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    async def to_list(self, n: Optional[int] = None) -> list[dict]:
        docs = await self._collection._load(self._filt)
        docs = sort_docs(docs, self._sort)
        cap = n if n is not None else self._limit
        if cap is not None:
            docs = docs[:cap]
        return [project(d, self._projection) for d in docs]

    def __aiter__(self):
        self._iter = None
        return self

    async def __anext__(self):
        if self._iter is None:
            self._iter = iter(await self.to_list(self._limit))
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class Collection:
    def __init__(self, name: str):
        self.name = name

    async def _load(self, filt: Optional[dict] = None) -> list[dict]:
        pool = await get_pool()
        rows = await pool.fetch(
            "select doc from documents where collection = $1",
            self.name,
        )
        docs = [_as_dict(r["doc"]) for r in rows]
        if filt:
            docs = [d for d in docs if match(d, filt)]
        return docs

    async def _write(self, doc: dict) -> str:
        pool = await get_pool()
        doc_id = _doc_id(doc)
        payload = dict(doc)
        await pool.execute(
            """
            insert into documents (collection, id, doc)
            values ($1, $2, $3::jsonb)
            on conflict (collection, id) do update
            set doc = excluded.doc, updated_at = now()
            """,
            self.name,
            doc_id,
            _dump(payload),
        )
        return doc_id

    async def find_one(self, filt: Optional[dict] = None, projection: Optional[dict] = None, sort=None):
        docs = await self._load(filt)
        docs = sort_docs(docs, sort)
        if not docs:
            return None
        return project(docs[0], projection)

    def find(self, filt: Optional[dict] = None, projection: Optional[dict] = None) -> Cursor:
        return Cursor(self, filt, projection)

    async def insert_one(self, doc: dict):
        await self._write(doc)
        return type("InsertOne", (), {"inserted_id": _doc_id(doc)})()

    async def insert_many(self, docs: list[dict]):
        for doc in docs:
            await self._write(doc)

    async def replace_one(self, filt: dict, doc: dict, upsert: bool = False):
        existing = await self.find_one(filt, projection=None)
        if existing is None and not upsert:
            return
        merged = dict(doc)
        if existing and "id" in existing and "id" not in merged:
            merged["id"] = existing["id"]
        if existing:
            pool = await get_pool()
            old_id = _doc_id(existing)
            new_id = _doc_id(merged)
            if old_id != new_id:
                await pool.execute(
                    "delete from documents where collection = $1 and id = $2",
                    self.name,
                    old_id,
                )
        await self._write(merged)

    async def update_one(self, filt: dict, update: dict):
        doc = await self.find_one(filt, projection=None)
        if not doc:
            return
        if "$set" in update:
            doc.update(update["$set"])
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = int(doc.get(k) or 0) + int(v)
        await self._write(doc)

    async def update_many(self, filt: dict, update: dict):
        docs = await self._load(filt)
        for doc in docs:
            if "$set" in update:
                doc.update(update["$set"])
            await self._write(doc)

    async def delete_one(self, filt: dict):
        doc = await self.find_one(filt, projection=None)
        if not doc:
            return
        pool = await get_pool()
        await pool.execute(
            "delete from documents where collection = $1 and id = $2",
            self.name,
            _doc_id(doc),
        )

    async def delete_many(self, filt: Optional[dict] = None):
        pool = await get_pool()
        if not filt:
            await pool.execute("delete from documents where collection = $1", self.name)
            return
        docs = await self._load(filt)
        for doc in docs:
            await pool.execute(
                "delete from documents where collection = $1 and id = $2",
                self.name,
                _doc_id(doc),
            )

    async def count_documents(self, filt: Optional[dict] = None) -> int:
        return len(await self._load(filt))

    async def find_one_and_update(self, filt: dict, update: dict, upsert: bool = False, return_document: bool = True):
        doc = await self.find_one(filt, projection=None)
        if doc is None:
            if not upsert:
                return None
            doc = dict(filt)
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = int(doc.get(k) or 0) + int(v)
        if "$set" in update:
            doc.update(update["$set"])
        await self._write(doc)
        return doc if return_document else None


class _DB:
    def __getattr__(self, name: str) -> Collection:
        if name.startswith("_"):
            raise AttributeError(name)
        return Collection(name)

    def __getitem__(self, name: str) -> Collection:
        return Collection(name)


db = _DB()


async def next_counter(name: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        insert into documents (collection, id, doc)
        values ('counters', $1, jsonb_build_object('_id', $1::text, 'value', 1))
        on conflict (collection, id) do update
        set doc = jsonb_set(
            documents.doc,
            '{value}',
            to_jsonb(coalesce((documents.doc->>'value')::int, 0) + 1)
        ),
        updated_at = now()
        returning (doc->>'value')::int as value
        """,
        name,
    )
    return int(row["value"])
