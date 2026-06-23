"""Vercel entry point — exposes the Meta Ads FastMCP ASGI app.

Vercel's Python runtime picks up the module-level ``app`` variable and wraps it
as a serverless handler.  All routes (``/mcp``, ``/health``, ``/auth/callback``,
``/.well-known/…``) are rewritten here by ``vercel.json``; FastMCP's Starlette
router handles them internally.

Storage: set ``KV_REST_API_URL`` + ``KV_REST_API_TOKEN`` (Vercel KV, auto-injected
when you link a KV store to the project) — or the ``UPSTASH_REDIS_*`` equivalents
for a manually provisioned Upstash database.  No ``CLIENT_STORAGE_DIR`` needed.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from meta_ads_mcp.server import mcp  # noqa: E402

app = mcp.http_app()
