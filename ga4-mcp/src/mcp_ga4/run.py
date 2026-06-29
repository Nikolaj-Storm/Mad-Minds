"""ASGI entrypoint — streamable-HTTP MCP at /mcp, plus the GoogleProvider OAuth
routes (added automatically by FastMCP from the FASTMCP_SERVER_AUTH_* env).

    uvicorn mcp_ga4.run:app --host 0.0.0.0 --port 8000

Reached via the Tailscale Funnel at https://ga4.<tailnet>.ts.net/mcp ; the OAuth
callback is https://ga4.<tailnet>.ts.net/auth/callback (must match the OAuth client
redirect URI and FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL).
"""
from mcp_ga4.server import mcp

app = mcp.http_app(path="/mcp")
