"""Facebook (Meta) OAuth provider for FastMCP.

FastMCP ships first-class providers for Google, GitHub, Azure, etc. but NOT
Facebook, so this module builds one the same way ``GoogleProvider`` is built:
a thin subclass of ``OAuthProxy`` wired to Facebook's OAuth endpoints, plus a
``TokenVerifier`` that validates the opaque user token via Meta's Graph
``debug_token`` endpoint.

Two Facebook-specific things this handles that Google doesn't need:

1. **Long-lived tokens.** Facebook's authorization-code exchange returns a
   SHORT-lived (~1-2 h) user token and issues NO refresh token. Left as-is, a
   marketer would be logged out roughly every hour. We override
   ``exchange_authorization_code`` to swap the short-lived token for a
   long-lived (~60-day) one via ``grant_type=fb_exchange_token`` BEFORE the
   proxy stores it. The swap is idempotent (exchanging an already-long-lived
   token just returns another long-lived one), so it is always safe to run.

2. **Token validation.** Facebook user tokens are opaque, not JWTs, so the
   verifier calls ``GET /debug_token`` (authenticated with an app access token)
   to confirm validity, read granted scopes, and read the expiry.
"""

from __future__ import annotations

import time

import httpx
from key_value.aio.protocols import AsyncKeyValue

from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)

DEFAULT_GRAPH_VERSION = "v21.0"
DEFAULT_SCOPES = ["ads_read", "ads_management"]


class FacebookTokenVerifier(TokenVerifier):
    """Validate a Facebook user access token via Meta's Graph ``debug_token``.

    Facebook tokens are opaque, so we cannot decode them locally. We call
    ``debug_token`` with an app access token (``APP_ID|APP_SECRET``) to learn
    whether the token is valid, which scopes were granted, when it expires, and
    which Facebook user it belongs to.
    """

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        required_scopes: list[str] | None = None,
        graph_version: str = DEFAULT_GRAPH_VERSION,
        timeout_seconds: int = 10,
    ):
        super().__init__(required_scopes=required_scopes)
        self._app_id = app_id
        self._app_secret = app_secret
        self._graph_version = graph_version
        self.timeout_seconds = timeout_seconds

    async def verify_token(self, token: str) -> AccessToken | None:
        app_access_token = f"{self._app_id}|{self._app_secret}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                # debug_token is intentionally called WITHOUT a version path —
                # it is version-agnostic and this avoids breaking when a Graph
                # version is retired.
                resp = await client.get(
                    "https://graph.facebook.com/debug_token",
                    params={"input_token": token, "access_token": app_access_token},
                    headers={"User-Agent": "Mad-Minds-Meta-MCP"},
                )
            if resp.status_code != 200:
                logger.debug("Facebook debug_token HTTP %d", resp.status_code)
                return None

            data = (resp.json() or {}).get("data") or {}
            if not data.get("is_valid"):
                logger.debug("Facebook token reported not valid by debug_token")
                return None

            token_scopes = list(data.get("scopes") or [])
            if self.required_scopes:
                if not set(self.required_scopes).issubset(set(token_scopes)):
                    logger.debug(
                        "Facebook token missing required scopes. Has %s, needs %s",
                        token_scopes,
                        self.required_scopes,
                    )
                    return None

            # expires_at == 0 means a non-expiring token (e.g. a System User
            # token). Treat that as "no expiry".
            raw_exp = int(data.get("expires_at") or 0)
            expires_at = raw_exp if raw_exp > 0 else None
            if expires_at is not None and expires_at <= int(time.time()):
                logger.debug("Facebook token has expired")
                return None

            return AccessToken(
                token=token,
                client_id=str(data.get("app_id") or self._app_id),
                scopes=token_scopes,
                expires_at=expires_at,
                claims={
                    "sub": str(data.get("user_id") or "unknown"),
                    "fb_user_id": data.get("user_id"),
                    "data_access_expires_at": data.get("data_access_expires_at"),
                    "fb_token_info": data,
                },
            )
        except httpx.RequestError as e:
            logger.debug("Failed to reach Facebook debug_token: %s", e)
            return None
        except Exception as e:  # noqa: BLE001
            logger.debug("Facebook token verification error: %s", e)
            return None


class FacebookProvider(OAuthProxy):
    """Complete Facebook/Meta OAuth provider for FastMCP.

    Provide a Facebook App's ID + secret and the server's public base URL and
    every marketer can sign in with their own Facebook account, touching only
    the ad accounts they already manage.
    """

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        base_url: str,
        required_scopes: list[str] | None = None,
        graph_version: str = DEFAULT_GRAPH_VERSION,
        redirect_path: str = "/auth/callback",
        client_storage: AsyncKeyValue | None = None,
        jwt_signing_key: str | bytes | None = None,
        require_authorization_consent: bool = False,
        timeout_seconds: int = 10,
    ):
        if not app_id or not app_secret:
            raise ValueError(
                "FacebookProvider requires app_id and app_secret "
                "(set META_APP_ID / META_APP_SECRET)."
            )

        scopes = required_scopes or list(DEFAULT_SCOPES)
        self._fb_app_id = app_id
        self._fb_app_secret = app_secret
        self._graph_version = graph_version
        self._graph_base = f"https://graph.facebook.com/{graph_version}"

        # The verifier only GATES on what is strictly needed to do anything
        # (ads_read). ads_management may legitimately be absent for a read-only
        # marketer; those tokens should still authenticate, and a write attempt
        # then fails naturally with a clear Meta permission error.
        token_verifier = FacebookTokenVerifier(
            app_id=app_id,
            app_secret=app_secret,
            required_scopes=["ads_read"],
            graph_version=graph_version,
            timeout_seconds=timeout_seconds,
        )

        super().__init__(
            upstream_authorization_endpoint=(
                f"https://www.facebook.com/{graph_version}/dialog/oauth"
            ),
            upstream_token_endpoint=f"{self._graph_base}/oauth/access_token",
            upstream_client_id=app_id,
            upstream_client_secret=app_secret,
            token_verifier=token_verifier,
            base_url=base_url,
            redirect_path=redirect_path,
            # Facebook expects client_id/secret in the request body, not Basic auth.
            token_endpoint_auth_method="client_secret_post",
            valid_scopes=scopes,
            client_storage=client_storage,
            jwt_signing_key=jwt_signing_key,
            require_authorization_consent=require_authorization_consent,
        )
        logger.debug(
            "Initialized Facebook OAuth provider (app %s, scopes %s, graph %s)",
            app_id,
            scopes,
            graph_version,
        )

    async def _exchange_for_long_lived(self, short_token: str) -> dict | None:
        """Exchange a short-lived user token for a ~60-day long-lived one."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._graph_base}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": self._fb_app_id,
                        "client_secret": self._fb_app_secret,
                        "fb_exchange_token": short_token,
                    },
                )
            if resp.status_code != 200:
                logger.warning(
                    "fb_exchange_token returned HTTP %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
            return resp.json()
        except Exception as e:  # noqa: BLE001
            logger.warning("fb_exchange_token request failed: %s", e)
            return None

    async def exchange_authorization_code(self, client, authorization_code):
        """Swap the freshly-minted short-lived token for a long-lived one.

        Runs while the short-lived token is still valid (seconds after the IdP
        callback), mutating the stored upstream token in place before the parent
        persists it. Any failure degrades gracefully to the short-lived token
        rather than breaking sign-in.
        """
        try:
            code_model = await self._code_store.get(key=authorization_code.code)
            idp = getattr(code_model, "idp_tokens", None) if code_model else None
            short = idp.get("access_token") if isinstance(idp, dict) else None
            if short:
                long_lived = await self._exchange_for_long_lived(short)
                if long_lived and long_lived.get("access_token"):
                    idp["access_token"] = long_lived["access_token"]
                    if long_lived.get("expires_in"):
                        idp["expires_in"] = int(long_lived["expires_in"])
                    idp.pop("refresh_token", None)  # Facebook never issues one
                    await self._code_store.put(
                        key=authorization_code.code, value=code_model, ttl=300
                    )
                    logger.debug("Upgraded Facebook token to long-lived.")
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Long-lived token swap skipped (%s); using short-lived token.", e
            )
        return await super().exchange_authorization_code(client, authorization_code)
