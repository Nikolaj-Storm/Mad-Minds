"""Google Analytics (GA4) MCP server — per-user Google OAuth (FastMCP GoogleProvider).

The Analytics sibling of gads-mcp / gsc-mcp. Auth is configured entirely through
environment (FASTMCP_SERVER_AUTH=...google.GoogleProvider + client id/secret/scopes/
base url), exactly like the other Google connectors — FastMCP loads it automatically
and serves the OAuth routes. Marketers sign in once; tokens persist in /data.

Reporting-only: every tool is read-only.
"""
from fastmcp import FastMCP

from mcp_ga4 import tools

INSTRUCTIONS = (
    "Google Analytics 4 reporting via your own Google sign-in (read-only).\n\n"
    "PROPERTIES FIRST: every tool needs a numeric GA4 property ID — call "
    "list_properties to see the properties your account can read, then pass property_id.\n\n"
    "DATES: get_traffic / get_top_pages / get_conversions / get_report accept ISO "
    "YYYY-MM-DD or a relative token ('today', 'yesterday', 'NdaysAgo' e.g. '28daysAgo'). "
    "Dates resolve in the property's reporting time zone.\n\n"
    "TOOLS: get_traffic (sessions/users by channel/source/etc), get_top_pages, "
    "get_conversions (key events), get_realtime (last ~30 min), get_report (arbitrary "
    "dimensions+metrics)."
)

mcp = FastMCP(name="Google Analytics", instructions=INSTRUCTIONS)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "GA4 MCP"})


for _tool in (
    tools.list_properties,
    tools.get_traffic,
    tools.get_top_pages,
    tools.get_conversions,
    tools.get_report,
    tools.get_realtime,
):
    mcp.tool()(_tool)
