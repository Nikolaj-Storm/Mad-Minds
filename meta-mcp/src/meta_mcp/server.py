"""Meta Ads MCP server — remote HTTP + per-user Facebook OAuth proxy.

Sibling of ``gads_mcp/server.py``; same shape, Meta-specific guts. Each marketer
signs in with their OWN Facebook account, so they only touch ad accounts they
already have. The Facebook App (id/secret) is the org-level server secret used
during the OAuth handshake. Writes respect READONLY_MODE and route through the
/ad-actions spend-gate in Mad Minds.
"""

import os

from fastmcp import FastMCP

from meta_mcp.auth import build_auth


SERVER_INSTRUCTIONS = (
    "Meta (Facebook + Instagram) Ads reporting and management via each marketer's "
    "own Facebook sign-in.\n\n"
    "DATE RANGES: the reporting tool (get_performance) accepts ANY time period. "
    "Pass start_date and end_date (YYYY-MM-DD) for an explicit custom range -- a "
    "specific month or quarter, year-to-date, or any window older than 30 days -- "
    "or a date_preset (last_7d, last_30d, this_month, last_month, ...) for common "
    "rolling windows. When both are given, the explicit dates win. Pull whatever "
    "window the user actually asked for; do NOT limit yourself to the presets. "
    "Dates resolve in the ad account's reporting time zone.\n\n"
    "ACCOUNTS: use list_accounts to discover the ad accounts the signed-in user "
    "can access; pass an account_id (with or without the 'act_' prefix) to the "
    "other tools, or set META_AD_ACCOUNT_ID as the default.\n\n"
    "HIERARCHY: Campaign > Ad Set > Ad. Budgets live on the campaign (CBO) OR the "
    "ad set; update_budget targets whichever level holds the budget. Money values "
    "are in the account currency's whole units in tool output."
)

_auth = build_auth()
mcp = FastMCP(name="Meta Ads", instructions=SERVER_INSTRUCTIONS, auth=_auth)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "healthy", "service": "Meta Ads MCP"})


from meta_mcp.client import (  # noqa: E402
    get_client,
    handle_errors,
    is_readonly,
    graph_version,
    account_status_label,
)
from meta_mcp.campaigns import (  # noqa: E402
    get_campaigns,
    pause_entity,
    enable_entity,
    update_budget,
)
from meta_mcp.adsets import get_ad_sets  # noqa: E402
from meta_mcp.ads import get_ads  # noqa: E402
from meta_mcp.performance import get_performance  # noqa: E402


@handle_errors
def list_accounts():
    """List every Meta ad account your Facebook sign-in can access.

    Returns each account's id, name, currency and status. Use the id (digits, or
    the 'act_' form) with the other tools.
    """
    client = get_client()
    fields = "account_id,name,currency,account_status,timezone_name"
    rows = client.get_all("me/adaccounts", {"fields": fields, "limit": 200})
    out = []
    for r in rows:
        out.append(
            {
                "account_id": r.get("account_id"),
                "name": r.get("name"),
                "currency": r.get("currency"),
                "status": account_status_label(r.get("account_status")),
                "timezone": r.get("timezone_name"),
            }
        )
    return out


@handle_errors
def server_status() -> dict:
    """Report config + a NON-SENSITIVE health check of the Facebook app secret.

    Shows whether the app credentials reached the server and whether they still
    look like placeholders -- WITHOUT revealing any secret value.
    """
    app_id = os.environ.get("META_APP_ID", "") or ""
    app_secret = os.environ.get("META_APP_SECRET", "") or ""
    looks_placeholder = any(
        x in (app_id + app_secret).upper()
        for x in ("YOUR", "PLACEHOLDER", "PASTE", "CHANGEME", "REAL_")
    )
    return {
        "readonly_mode": is_readonly(),
        "graph_api_version": graph_version(),
        "default_ad_account_id_set": bool(os.environ.get("META_AD_ACCOUNT_ID")),
        "app_id_present": bool(app_id.strip()),
        "app_secret_present": bool(app_secret.strip()),
        "app_secret_length": len(app_secret),
        "credentials_look_like_placeholder": looks_placeholder,
        "required_scopes": os.environ.get("META_REQUIRED_SCOPES", "ads_read,ads_management"),
    }


for _tool in (
    list_accounts, server_status,
    get_campaigns, get_ad_sets, get_ads,
    get_performance,
    pause_entity, enable_entity, update_budget,
):
    mcp.tool()(_tool)
