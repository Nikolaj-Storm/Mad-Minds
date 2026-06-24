"""Upstash Redis-backed AsyncKeyValue store for stateless (Vercel) deployments.

Replaces ``DiskStore`` when the server is hosted on a platform where the
filesystem is ephemeral (Vercel, any Lambda-style host).  The interface is
duck-typed to match ``key_value.aio.protocols.AsyncKeyValue`` — FastMCP's
``OAuthProxy`` (which the Google provider extends) only needs ``get``, ``put``,
and ``delete``.

Required env vars (set in Vercel project → Settings → Environment Variables):
  KV_REST_API_URL    — Vercel KV auto-injects this when you link a KV store, OR
  UPSTASH_REDIS_REST_URL   — set manually if you provision Upstash directly

  KV_REST_API_TOKEN  — Vercel KV auto-injected, OR
  UPSTASH_REDIS_REST_TOKEN — manual Upstash

Values are round-tripped with pickle+base64 so Pydantic models and arbitrary
Python objects survive the JSON-only Redis wire format unchanged — the same
behaviour as ``diskcache``-backed DiskStore.

This mirrors ``meta_ads_mcp/redis_store.py`` exactly so the two self-hosted MCPs
behave identically on Vercel.
"""

from __future__ import annotations

import base64
import pickle
from typing import Any


class RedisStore:
    """AsyncKeyValue backed by Upstash Redis (HTTP REST, no persistent TCP).

    HTTP-only transport (``upstash-redis``) works inside Vercel's short-lived
    function containers where a traditional Redis TCP connection would be
    killed between requests.
    """

    def __init__(self, url: str, token: str, prefix: str = "") -> None:
        from upstash_redis.asyncio import Redis  # type: ignore[import]

        self._r = Redis(url=url, token=token)
        self._prefix = prefix

    def _k(self, key: str, collection: str | None) -> str:
        parts = [p for p in (self._prefix, collection, key) if p]
        return ":".join(parts)

    async def get(self, *, key: str, collection: str | None = None) -> Any:
        raw = await self._r.get(self._k(key, collection))
        if raw is None:
            return None
        try:
            return pickle.loads(base64.b64decode(raw))
        except Exception:
            return None

    async def put(self, *, key: str, value: Any, collection: str | None = None, ttl: int | None = None) -> None:
        data = base64.b64encode(pickle.dumps(value)).decode()
        rkey = self._k(key, collection)
        if ttl:
            await self._r.setex(rkey, ttl, data)
        else:
            await self._r.set(rkey, data)

    async def delete(self, *, key: str, collection: str | None = None) -> None:
        await self._r.delete(self._k(key, collection))
