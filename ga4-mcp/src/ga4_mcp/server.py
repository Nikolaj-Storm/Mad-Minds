"""Google Analytics (GA4) — MARKETER MCP server (per-user Google sign-in).

The Analytics sibling of the marketer ``gads-mcp``. Humans use this through Claude
(Desktop or the Mad-Minds stack); auth is each marketer's OWN Google OAuth, scope
``analytics.readonly``. GA4 is reporting-only, so every tool is read-only — there
are no write/mutate tools.

Tools: list_properties, get_traffic, get_top_pages, get_conversions, get_report
(generic), get_realtime, server_status.
"""
import os

from fastmcp import FastMCP

from ga4_mcp.client import admin_client, handle_errors
from ga4_mcp.reports import (
    get_traffic, get_top_pages, get_conversions, get_report, get_realtime,
)

SERVER_INSTRUCTIONS = (
    "Google Analytics 4 reporting via your own Google sign-in (read-only).\n\n"
    "PROPERTIES — READ THIS FIRST: every tool needs a numeric GA4 property ID. Call "
    "list_properties to see the properties your Google account can read, then pass "
    "property_id (or set GA4_PROPERTY_ID for a single-property default).\n\n"
    "DATE RANGES: get_traffic / get_top_pages / get_conversions / get_report accept "
    "ANY window. Pass start_date and end_date as ISO YYYY-MM-DD for an explicit range, "
    "or a relative token ('today', 'yesterday', 'NdaysAgo' e.g. '28daysAgo'). Dates "
    "resolve in the property's reporting time zone.\n\n"
    "TOOLS: get_traffic (sessions/users by channel/source/etc), get_top_pages "
    "(most-viewed pages), get_conversions (key events), get_realtime (last ~30 min), "
    "get_report (arbitrary dimensions+metrics)."
)

mcp = FastMCP(name="Google Analytics", instructions=SERVER_INSTRUCTIONS)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "GA4 MCP"})


@handle_errors
def list_properties() -> dict:
    """List every GA4 property your Google account can read.

    Walks the account summaries you have access to and returns each property's
    numeric ID (pass as property_id to the other tools), display name and parent
    account.
    """
    client = admin_client()
    accounts = []
    properties = []
    for summary in client.list_account_summaries():
        accounts.append({"account": summary.account, "account_name": summary.display_name})
        for ps in summary.property_summaries:
            pid = ps.property.split("/")[-1]           # "properties/456" -> "456"
            properties.append({
                "property_id": pid,
                "display_name": ps.display_name,
                "property_type": getattr(ps, "property_type", None).name
                if getattr(ps, "property_type", None) else None,
                "account": summary.account,
                "account_name": summary.display_name,
            })
    return {"count": len(properties), "properties": properties, "accounts": accounts}


@handle_errors
def server_status() -> dict:
    """Non-sensitive config health check (no secrets revealed)."""
    return {
        "mode": "marketer-oauth",
        "oauth_client_present": bool(
            (os.environ.get("GA4_OAUTH_CLIENT_ID") or os.environ.get("GOOGLE_OAUTH_CLIENT_ID"))
        ),
        "refresh_token_present": bool(
            (os.environ.get("GA4_OAUTH_REFRESH_TOKEN") or os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN"))
        ),
        "default_property_id_set": bool(os.environ.get("GA4_PROPERTY_ID")),
    }


for _tool in (list_properties, get_traffic, get_top_pages, get_conversions,
              get_report, get_realtime, server_status):
    mcp.tool()(_tool)
