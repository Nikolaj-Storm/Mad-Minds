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
    """OAuth-proxy provider with persistent storage (sign in once).

    Storage backend is selected automatically so the same code runs on Vercel
    and on a Docker/VPS host:
    - Vercel / stateless: set KV_REST_API_URL + KV_REST_API_TOKEN (Vercel KV) or
      UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN (manual Upstash).
    - Docker / VPS / Fly: set CLIENT_STORAGE_DIR to a mounted volume path.
    Without a client_id OR any storage backend, auth is disabled (so /health and
    server_status still answer for diagnosis).
    """
    client_id = os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID")
    redis_url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    redis_token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    storage_dir = os.environ.get("CLIENT_STORAGE_DIR")

    if not client_id or not ((redis_url and redis_token) or storage_dir):
        return None

    from fastmcp.server.auth.providers.google import GoogleProvider

    # Redis (Vercel KV / Upstash) takes priority; fall back to disk for Docker/Fly.
    if redis_url and redis_token:
        from gads_mcp.redis_store import RedisStore
        storage = RedisStore(
            url=redis_url,
            token=redis_token,
            prefix=os.environ.get("REDIS_KEY_PREFIX", ""),
        )
    else:
        from key_value.aio.stores.disk import DiskStore
        storage = DiskStore(directory=storage_dir)

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
        client_storage=storage,
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
    "ACCOUNTS: metrics are only available on client accounts. Manager (MCC) accounts "
    "return no metrics -- use list_accounts and query a client account ID."
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


@handle_errors
def list_accounts():
    """List every Google Ads account your Google sign-in can access."""
    client = get_client()
    svc = client.get_service("CustomerService")
    return [n.split("/")[-1] for n in svc.list_accessible_customers().resource_names]


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
