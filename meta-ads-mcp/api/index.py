"""Vercel entry point — exposes the Meta Ads FastMCP ASGI app.

Vercel's Python runtime picks up the module-level ``app`` variable and wraps it
as a serverless handler.  All routes (``/mcp``, ``/health``, ``/auth/callback``,
``/.well-known/…``) are rewritten here by ``vercel.json``; FastMCP's Starlette
router handles them internally.

Storage: set ``KV_REST_API_URL`` + ``KV_REST_API_TOKEN`` (Vercel KV, auto-injected
when you link a KV store to the project) — or the ``UPSTASH_REDIS_*`` equivalents
for a manually provisioned Upstash database.  No ``CLIENT_STORAGE_DIR`` needed.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from meta_ads_mcp.server import mcp  # noqa: E402


class _DCRGrantTypeFix:
    """ASGI wrapper that adds 'refresh_token' to DCR grant_types when missing.

    FastMCP >= 2.12 requires clients to register with BOTH 'authorization_code'
    AND 'refresh_token' in grant_types, but Claude's MCP client only sends
    'authorization_code'. This causes every Connect attempt to fail with
    'grant_types must be authorization_code and refresh_token'. The wrapper
    normalises the /register request body before FastMCP's own handler sees it.
    """

    def __init__(self, asgi_app):
        self._app = asgi_app

    async def __call__(self, scope, receive, send):
        if (
            scope.get("type") == "http"
            and scope.get("path") == "/register"
            and scope.get("method") == "POST"
        ):
            # Buffer the full request body (DCR payloads are always small).
            body = b""
            more = True
            while more:
                msg = await receive()
                body += msg.get("body", b"")
                more = msg.get("more_body", False)

            try:
                data = json.loads(body)
                grant_types = data.get("grant_types") or ["authorization_code"]
                if isinstance(grant_types, list) and "refresh_token" not in grant_types:
                    data["grant_types"] = grant_types + ["refresh_token"]
                body = json.dumps(data).encode()
            except Exception:
                pass

            async def _replay_receive():
                return {"type": "http.request", "body": body, "more_body": False}

            await self._app(scope, _replay_receive, send)
        else:
            await self._app(scope, receive, send)


app = _DCRGrantTypeFix(mcp.http_app())
