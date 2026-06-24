"""Google Ads MCP server — remote HTTP + per-user Google OAuth proxy.

Adapted from the OnlineMinds local Google Ads MCP (tool logic unchanged). Auth
is the FastMCP Google OAuth-proxy: each marketer signs in with their OWN Google
account, so they only touch accounts they already have. The Google Ads developer
token is a server-side secret (one for the whole org). Writes respect
READONLY_MODE and route through the /ad-actions spend-gate in Mad Minds.
"""

import os

from fastmcp import FastMCP


def _build_auth():
    """OAuth-proxy provider with persistent disk storage (sign in once)."""
    storage_dir = os.environ.get("CLIENT_STORAGE_DIR")
    client_id = os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID")
    if not storage_dir or not client_id:
        return None
    from fastmcp.server.auth.providers.google import GoogleProvider
    from key_value.aio.stores.disk import DiskStore

    scopes = os.environ.get(
        "FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES",
        "openid,https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/adwords",
    )
    kwargs = dict(
        client_id=client_id,
        client_secret=os.environ["FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET"],
        base_url=os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL", "http://localhost:8000"),
        required_scopes=[s.strip() for s in scopes.split(",") if s.strip()],
        client_storage=DiskStore(directory=storage_dir),
        require_authorization_consent=False,
    )
    jwt_key = os.environ.get("JWT_SIGNING_KEY")
    if jwt_key:
        kwargs["jwt_signing_key"] = jwt_key
    return GoogleProvider(**kwargs)


SERVER_INSTRUCTIONS = (
    "Google Ads reporting and management via each marketer's own Google sign-in.\n\n"
    "DATE RANGES: the reporting tools (get_performance, get_search_terms) accept ANY "
    "time period. Pass start_date and end_date (YYYY-MM-DD) for an explicit custom "
    "range -- a specific month or quarter, year-to-date, or any window older than 30 "
    "days -- or a date_range preset (LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH, "
    "...) for common rolling windows. When both are given, the explicit dates win. "
    "Pull whatever window the user actually asked for; do NOT limit yourself to the "
    "presets. Dates resolve in the account's reporting time zone.\n\n"
    "ACCOUNTS — READ THIS FIRST: the real data lives on the CLIENT accounts, not the "
    "manager. Most OnlineMinds brands sit as client accounts UNDER a manager (MCC) "
    "account. Manager accounts return NO metrics. Always call list_accounts first: it "
    "now walks each accessible manager and returns the client (leaf) accounts you can "
    "actually pull data from. Each row gives a `customer_id` and the `login_customer_id` "
    "(the manager to send as the login-customer-id header) — pass BOTH to the other "
    "tools. Never report 'no data' from a manager ID without first expanding to its "
    "client accounts."
)

_auth = _build_auth()
mcp = (
    FastMCP(name="Google Ads", instructions=SERVER_INSTRUCTIONS, auth=_auth)
    if _auth
    else FastMCP(name="Google Ads", instructions=SERVER_INSTRUCTIONS)
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "Google Ads MCP"})


from gads_mcp.client import get_client, handle_errors, is_readonly  # noqa: E402
from gads_mcp.campaigns import get_campaigns, pause_entity, enable_entity, update_budget  # noqa: E402
from gads_mcp.performance import get_performance, get_search_terms  # noqa: E402
from gads_mcp.ads import get_ad_groups, create_text_ad  # noqa: E402
from gads_mcp.keywords import get_keywords, update_keyword_bid  # noqa: E402


# Fields available on customer_client. Used to walk a manager's whole subtree.
_CUSTOMER_CLIENT_QUERY = """
    SELECT customer_client.id,
           customer_client.descriptive_name,
           customer_client.manager,
           customer_client.level,
           customer_client.currency_code,
           customer_client.time_zone,
           customer_client.status
    FROM customer_client
    WHERE customer_client.status = 'ENABLED'
"""


@handle_errors
def list_accounts() -> list:
    """List every Google Ads CLIENT account you can pull data from.

    Google's list_accessible_customers only returns the accounts your login is
    DIRECTLY linked to — for an agency/MCC setup that's the manager account(s)
    plus any standalone accounts, NOT the brand client accounts under a manager.
    Metrics only exist on the client accounts, so this tool walks each accessible
    account's tree (via customer_client) and returns the client (leaf) accounts.

    Each row is a dict:
      * customer_id        — the 10-digit ID to pass as customer_id to other tools
      * descriptive_name   — the account name (e.g. "Printumo", "Rentumo.dk")
      * login_customer_id  — the manager ID to pass as login_customer_id when
                             querying this client (null for standalone accounts)
      * currency_code, time_zone — account settings
      * manager            — always False here (manager nodes are excluded; they
                             carry no metrics)

    Pass each row's customer_id together with its login_customer_id to
    get_performance / get_campaigns / get_search_terms etc.
    """
    client = get_client()
    svc = client.get_service("CustomerService")
    accessible = [
        n.split("/")[-1] for n in svc.list_accessible_customers().resource_names
    ]

    seen: dict[str, dict] = {}
    for top in accessible:
        try:
            # Log in *through* this account so we can read its whole subtree.
            tree_client = get_client(login_customer_id=top)
            ga = tree_client.get_service("GoogleAdsService")
            rows = list(ga.search(customer_id=top, query=_CUSTOMER_CLIENT_QUERY))
        except Exception:  # noqa: BLE001 — one bad root shouldn't kill the list
            # Couldn't read it as a tree root — surface it bare so it's not lost.
            seen.setdefault(
                top,
                {
                    "customer_id": top,
                    "descriptive_name": None,
                    "login_customer_id": None,
                    "currency_code": None,
                    "time_zone": None,
                    "manager": None,
                },
            )
            continue

        for row in rows:
            cc = row.customer_client
            cid = str(cc.id)
            if cc.manager:
                # Manager nodes (incl. the root itself) have no metrics — skip.
                continue
            seen.setdefault(
                cid,
                {
                    "customer_id": cid,
                    "descriptive_name": cc.descriptive_name or None,
                    # The account you authenticate THROUGH to query this client.
                    # None when the client is itself directly accessible.
                    "login_customer_id": None if cid == top else top,
                    "currency_code": cc.currency_code or None,
                    "time_zone": cc.time_zone or None,
                    "manager": False,
                },
            )

    return list(seen.values())


@handle_errors
def server_status() -> dict:
    """Report config + a NON-SENSITIVE health check of the developer token.

    Helps diagnose setup: shows whether the GOOGLE_ADS_DEVELOPER_TOKEN secret
    actually reached the server, its length, and whether it still looks like a
    placeholder or has stray whitespace -- WITHOUT revealing the token value.
    """
    dt = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "") or ""
    looks_placeholder = any(
        x in dt.upper() for x in ("YOUR", "PLACEHOLDER", "DEV_TOKEN_OR", "REAL_", "PASTE")
    )
    return {
        "readonly_mode": is_readonly(),
        "default_customer_id": os.environ.get("GOOGLE_ADS_CUSTOMER_ID") or None,
        "login_customer_id_set": bool(os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")),
        "developer_token_present": bool(dt.strip()),
        "developer_token_length": len(dt),
        "developer_token_has_surrounding_whitespace": dt != dt.strip(),
        "developer_token_looks_like_placeholder": looks_placeholder,
    }


for _tool in (
    list_accounts, server_status,
    get_campaigns, get_ad_groups, get_keywords,
    get_performance, get_search_terms,
    pause_entity, enable_entity, update_budget,
    create_text_ad, update_keyword_bid,
):
    mcp.tool()(_tool)
