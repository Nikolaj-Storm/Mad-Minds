"""Meta (Facebook/Instagram) Ads MCP server — remote HTTP + per-user Facebook OAuth.

The Meta counterpart of ``gads_mcp/server.py``. Auth is a FastMCP OAuth proxy
to Facebook (see ``facebook_provider.py``): each marketer signs in with their
OWN Facebook account, so they only touch ad accounts they already manage. The
Facebook App ID/Secret are server-side secrets (one app for the whole org).
Writes respect READONLY_MODE and route through the ``/ad-actions`` spend-gate in
Mad Minds.
"""

import os

from fastmcp import FastMCP

from meta_ads_mcp.facebook_provider import DEFAULT_GRAPH_VERSION, DEFAULT_SCOPES


def _scopes_from_env() -> list[str]:
    raw = os.environ.get("META_SCOPES")
    if not raw:
        return list(DEFAULT_SCOPES)
    return [s.strip() for s in raw.split(",") if s.strip()]


def _build_auth():
    """Facebook OAuth-proxy provider with persistent disk storage (sign in once)."""
    storage_dir = os.environ.get("CLIENT_STORAGE_DIR")
    app_id = os.environ.get("META_APP_ID")
    app_secret = os.environ.get("META_APP_SECRET")
    base_url = os.environ.get("META_OAUTH_BASE_URL")
    if not (storage_dir and app_id and app_secret and base_url):
        # Missing config -> boot WITHOUT auth so /health and server_status still
        # answer for diagnosis. Tools that need a signed-in user will report it.
        return None

    from key_value.aio.stores.disk import DiskStore

    from meta_ads_mcp.facebook_provider import FacebookProvider

    return FacebookProvider(
        app_id=app_id,
        app_secret=app_secret,
        base_url=base_url,
        required_scopes=_scopes_from_env(),
        graph_version=os.environ.get("META_GRAPH_VERSION") or DEFAULT_GRAPH_VERSION,
        client_storage=DiskStore(directory=storage_dir),
        jwt_signing_key=os.environ.get("JWT_SIGNING_KEY"),
        require_authorization_consent=False,
        config_id=os.environ.get("META_CONFIG_ID") or None,
    )


SERVER_INSTRUCTIONS = (
    "Meta (Facebook + Instagram) Ads reporting and management via each "
    "marketer's own Facebook sign-in.\n\n"
    "DATE RANGES: the reporting tool (get_performance) accepts ANY time period. "
    "Pass start_date and end_date (YYYY-MM-DD) for an explicit custom range -- a "
    "specific month or quarter, year-to-date, or any older window -- or a "
    "date_preset (last_7d, last_14d, last_28d, last_30d, last_90d, this_month, "
    "last_month, this_quarter, ...) for common rolling windows. When both are "
    "given, the explicit dates win. Dates resolve in the ad account's time zone.\n\n"
    "HIERARCHY: ad account (act_<digits>) -> campaign -> ad set -> ad. Budgets "
    "live EITHER on the campaign (Advantage/CBO campaign budget) OR on each ad "
    "set, never both -- a null campaign budget means the budget is on the ad "
    "sets. Meta has no keywords or search-terms report.\n\n"
    "ACCOUNTS: use list_ad_accounts to discover the act_<digits> IDs the signed-in "
    "marketer can access; pass one as account_id. Amounts are in the account's "
    "currency (whole units, e.g. 500 = 500 DKK)."
)

_auth = _build_auth()
mcp = (
    FastMCP(name="Meta Ads", instructions=SERVER_INSTRUCTIONS, auth=_auth)
    if _auth
    else FastMCP(name="Meta Ads", instructions=SERVER_INSTRUCTIONS)
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "healthy", "service": "Meta Ads MCP"})


from meta_ads_mcp.client import get_api, handle_errors, is_readonly  # noqa: E402
from meta_ads_mcp.campaigns import (  # noqa: E402
    get_campaigns,
    pause_entity,
    enable_entity,
    update_budget,
)
from meta_ads_mcp.adsets import get_ad_sets  # noqa: E402
from meta_ads_mcp.ads import get_ads  # noqa: E402
from meta_ads_mcp.insights import get_performance  # noqa: E402


# Meta ad-account status codes -> human labels (the common ones).
_ACCOUNT_STATUS = {
    1: "ACTIVE",
    2: "DISABLED",
    3: "UNSETTLED",
    7: "PENDING_RISK_REVIEW",
    8: "PENDING_SETTLEMENT",
    9: "IN_GRACE_PERIOD",
    100: "PENDING_CLOSURE",
    101: "CLOSED",
    201: "ANY_ACTIVE",
    202: "ANY_CLOSED",
}


@handle_errors
def list_ad_accounts() -> list:
    """List every Meta ad account your Facebook sign-in can access.

    Returns each account's ``act_…`` ID, name, currency, and status. Use one of
    these IDs as ``account_id`` in the other tools.
    """
    from facebook_business.adobjects.user import User
    from facebook_business.adobjects.adaccount import AdAccount

    api = get_api()
    me = User(fbid="me", api=api)
    fields = [
        AdAccount.Field.id,
        AdAccount.Field.name,
        AdAccount.Field.account_status,
        AdAccount.Field.currency,
    ]
    out = []
    for acct in me.get_ad_accounts(fields=fields):
        status = acct.get(AdAccount.Field.account_status)
        out.append(
            {
                "id": acct.get(AdAccount.Field.id),
                "name": acct.get(AdAccount.Field.name),
                "currency": acct.get(AdAccount.Field.currency),
                "account_status": _ACCOUNT_STATUS.get(status, status),
            }
        )
    return out


@handle_errors
def server_status() -> dict:
    """Report config + a NON-SENSITIVE health check of the Facebook App secret.

    Shows whether the META_APP_ID / META_APP_SECRET secrets reached the server
    (and the secret's length) WITHOUT revealing their values, plus the readonly
    flag, default account, Graph version, and requested scopes.
    """
    app_id = os.environ.get("META_APP_ID", "") or ""
    secret = os.environ.get("META_APP_SECRET", "") or ""
    return {
        "readonly_mode": is_readonly(),
        "auth_configured": _auth is not None,
        "default_ad_account_id": os.environ.get("META_AD_ACCOUNT_ID") or None,
        "app_id_present": bool(app_id.strip()),
        "app_secret_present": bool(secret.strip()),
        "app_secret_length": len(secret),
        "app_secret_has_surrounding_whitespace": secret != secret.strip(),
        "graph_version": os.environ.get("META_GRAPH_VERSION") or DEFAULT_GRAPH_VERSION,
        "requested_scopes": _scopes_from_env(),
        "login_for_business_config_id_present": bool(os.environ.get("META_CONFIG_ID")),
    }


for _tool in (
    list_ad_accounts,
    server_status,
    get_campaigns,
    get_ad_sets,
    get_ads,
    get_performance,
    pause_entity,
    enable_entity,
    update_budget,
):
    mcp.tool()(_tool)
