"""Per-user Meta (Facebook) OAuth for the MCP server.

This is the ONE place where Meta diverges meaningfully from the Google Ads
server, so it lives in its own module instead of inline in ``server.py``.

WHY IT'S DIFFERENT FROM gads-mcp:
  * gads uses FastMCP's built-in ``GoogleProvider`` (Google is a first-class
    provider with OIDC discovery + JWT verification). FastMCP ships no
    first-class *Meta/Facebook* provider, so we wire the generic ``OAuthProxy``
    to Facebook's OAuth endpoints ourselves and supply a ``TokenVerifier`` that
    validates tokens online via Graph ``/debug_token``.
  * Facebook does NOT issue OIDC ID tokens or a JWKS we can verify offline, and
    it does NOT issue refresh tokens. Instead, a short-lived user token (~1–2h)
    is exchanged for a LONG-LIVED user token (~60 days). So verification is done
    ONLINE; there is no silent indefinite refresh — after ~60 days the marketer
    reconnects.
  * The org-level server secret is a Facebook **App** (``META_APP_ID`` /
    ``META_APP_SECRET``), not a developer token.

Scopes requested: ``ads_read`` (reporting) and ``ads_management`` (pause/enable,
budget changes). ``business_management`` is optional and only needed for some
Business-Manager-scoped reads.

Verified (sandbox): with dummy app creds present, ``build_auth()`` constructs a
real FastMCP ``OAuthProxy`` against Facebook's endpoints and the verifier
subclasses ``TokenVerifier`` correctly (see tests + NOTICE). The live Facebook
handshake + ``/debug_token`` round-trip still need a real app to exercise.
"""

import os

import httpx

from fastmcp.server.auth.auth import TokenVerifier
from mcp.server.auth.provider import AccessToken


def _required_scopes() -> list[str]:
    scopes = os.environ.get("META_REQUIRED_SCOPES", "ads_read,ads_management")
    return [s.strip() for s in scopes.split(",") if s.strip()]


def build_auth():
    """Return a FastMCP auth provider, or ``None`` when app creds are absent.

    Mirrors gads' ``_build_auth``: no creds -> ``None`` (server boots unauthed
    for /health and local tooling). Creds present -> build the Meta OAuth proxy.
    """
    storage_dir = os.environ.get("CLIENT_STORAGE_DIR")
    app_id = os.environ.get("META_APP_ID")
    app_secret = os.environ.get("META_APP_SECRET")
    if not storage_dir or not app_id or not app_secret:
        return None

    from fastmcp.server.auth.oauth_proxy import OAuthProxy
    from key_value.aio.stores.disk import DiskStore

    from meta_mcp.client import DEFAULT_GRAPH_VERSION

    version = os.environ.get("GRAPH_API_VERSION", DEFAULT_GRAPH_VERSION)
    base_url = os.environ.get("META_BASE_URL", "http://localhost:8000")

    verifier = MetaTokenVerifier(
        app_id=app_id,
        app_secret=app_secret,
        version=version,
        base_url=base_url,
        required_scopes=_required_scopes(),
    )

    kwargs = dict(
        # Upstream = Facebook: login dialog + token-exchange endpoints.
        upstream_authorization_endpoint=f"https://www.facebook.com/{version}/dialog/oauth",
        upstream_token_endpoint=f"https://graph.facebook.com/{version}/oauth/access_token",
        upstream_client_id=app_id,
        upstream_client_secret=app_secret,
        token_verifier=verifier,  # OAuthProxy derives valid_scopes from this
        base_url=base_url,
        # redirect_path defaults to "/auth/callback" (matches the runbook's
        # whitelisted Facebook OAuth redirect URI).
        client_storage=DiskStore(directory=storage_dir),
        require_authorization_consent=False,
        # No silent indefinite refresh from Facebook (no refresh tokens); the
        # long-lived user token is validated by the verifier until it expires.
    )
    jwt_key = os.environ.get("JWT_SIGNING_KEY")
    if jwt_key:
        kwargs["jwt_signing_key"] = jwt_key
    return OAuthProxy(**kwargs)


class MetaTokenVerifier(TokenVerifier):
    """Validate a Facebook access token online via Graph ``/debug_token``.

    Subclasses FastMCP's ``TokenVerifier`` so ``OAuthProxy`` can read
    ``required_scopes`` off it. ``verify_token`` is async (per the protocol). We
    call ``/debug_token`` with an APP access token (``app_id|app_secret``) to
    confirm the user token is valid, unexpired, minted for OUR app, and carries
    the scopes we require, then return an ``AccessToken``.
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        version: str,
        base_url: str | None = None,
        required_scopes: list[str] | None = None,
    ):
        super().__init__(base_url=base_url, required_scopes=required_scopes)
        self.app_token = f"{app_id}|{app_secret}"
        self.app_id = str(app_id)
        self.debug_url = f"https://graph.facebook.com/{version}/debug_token"

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(timeout=30) as cx:
                resp = await cx.get(
                    self.debug_url,
                    params={"input_token": token, "access_token": self.app_token},
                )
            data = (resp.json() or {}).get("data", {})
        except Exception:
            return None

        if not data.get("is_valid"):
            return None
        if str(data.get("app_id")) != self.app_id:
            return None
        granted = set(data.get("scopes", []))
        required = set(self.required_scopes or [])
        if required and not required.issubset(granted):
            return None
        return AccessToken(
            token=token,
            client_id=str(data.get("app_id")),
            scopes=list(granted),
            expires_at=data.get("expires_at") or None,
        )
