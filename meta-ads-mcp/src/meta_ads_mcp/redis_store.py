"""Upstash Redis-backed AsyncKeyValue store for stateless (Vercel) deployments.

Replaces ``DiskStore`` when the server is hosted on a platform where the
filesystem is ephemeral (Vercel, any Lambda-style host).  The interface is
duck-typed to match ``key_value.aio.protocols.AsyncKeyValue`` — FastMCP's
``OAuthProxy`` only needs ``get``, ``put``, and ``delete``.

Required env vars (set in Vercel project → Settings → Environment Variables):
  KV_REST_API_URL    — Vercel KV auto-injects this when you link a KV store, OR
  UPSTASH_REDIS_REST_URL   — set manually if you provision Upstash directly

  KV_REST_API_TOKEN  — Vercel KV auto-injected, OR
  UPSTASH_REDIS_REST_TOKEN — manual Upstash

Values are round-tripped with pickle+base64 so Pydantic models and arbitrary
Python objects survive the JSON-only Redis wire format unchanged — the same
behaviour as ``diskcache``-backed DiskStore.
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

    def __init__(self, url: str, token: str) -> None:
        from upstash_redis.asyncio import Redis  # type: ignore[import]

        self._r = Redis(url=url, token=token)

    async def get(self, *, key: str) -> Any:
        raw = await self._r.get(key)
        if raw is None:
            return None
        try:
            return pickle.loads(base64.b64decode(raw))
        except Exception:
            return None

    async def put(self, *, key: str, value: Any, ttl: int | None = None) -> None:
        data = base64.b64encode(pickle.dumps(value)).decode()
        if ttl:
            await self._r.setex(key, ttl, data)
        else:
            await self._r.set(key, data)

    async def delete(self, *, key: str) -> None:
        await self._r.delete(key)
