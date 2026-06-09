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


_auth = _build_auth()
mcp = FastMCP(name="Google Ads", auth=_auth) if _auth else FastMCP(name="Google Ads")


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
