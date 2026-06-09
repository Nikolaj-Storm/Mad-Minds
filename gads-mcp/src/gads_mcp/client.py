"""Shared helpers for all Google Ads MCP tools.

This module centralizes:
  * loading the Google Ads API client from ``google-ads.yaml`` (lazily, so the
    package can be imported without credentials present — handy for tests),
  * normalizing / resolving the customer ID,
  * the READONLY_MODE safety flag,
  * a single error handler that turns any failure into a readable dict so
    Claude can explain it to the user instead of crashing.

All ``google.ads`` imports are done lazily inside functions so this module
(and the tool modules that import from it) stay importable even when the
``google-ads`` package or credentials are not installed.
"""

import os
import sys
import functools
from functools import lru_cache


# --------------------------------------------------------------------------- #
# Configuration / credentials
# --------------------------------------------------------------------------- #
def get_yaml_path() -> str:
    """Path to the google-ads.yaml credentials file.

    Defaults to a ``google-ads.yaml`` next to this project. Override with the
    ``GOOGLE_ADS_YAML_PATH`` environment variable.
    """
    env = os.environ.get("GOOGLE_ADS_YAML_PATH")
    if env:
        return env
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "google-ads.yaml")


def get_client():
    """Build a Google Ads client for the CURRENT request's signed-in marketer.

    Per-user OAuth: the access token comes from the FastMCP Google OAuth proxy
    (the marketer's own Google sign-in). The developer token and optional
    login-customer-id are server-side env secrets (set once, org-wide). NOT
    cached -- each request is a different user/token.
    """
    from google.ads.googleads.client import GoogleAdsClient
    from google.oauth2.credentials import Credentials
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()
    access_token = getattr(token, "token", None)
    if not access_token:
        raise ValueError(
            "Not signed in. Connect Google Ads (sign in with Google) and try again."
        )

    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if not dev_token:
        raise ValueError("Server is missing GOOGLE_ADS_DEVELOPER_TOKEN.")

    login_cid = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or None
    if login_cid:
        login_cid = normalize_customer_id(login_cid)

    return GoogleAdsClient(
        credentials=Credentials(token=access_token),
        developer_token=dev_token,
        login_customer_id=login_cid,
        use_proto_plus=True,
    )


def normalize_customer_id(customer_id) -> str:
    """Strip dashes / spaces so '123-456-7890' becomes '1234567890'."""
    return "".join(ch for ch in str(customer_id) if ch.isdigit())


def resolve_customer_id(customer_id=None) -> str:
    """Use the supplied customer ID, else fall back to GOOGLE_ADS_CUSTOMER_ID.

    Lets marketing users set their account once in ``.env`` and then talk to
    Claude without pasting the 10-digit ID every time.
    """
    cid = customer_id or os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
    if not cid:
        raise ValueError(
            "No customer_id was provided and GOOGLE_ADS_CUSTOMER_ID is not set "
            "in your .env file. Provide the 10-digit Google Ads account ID."
        )
    return normalize_customer_id(cid)


# --------------------------------------------------------------------------- #
# READONLY_MODE — write tools simulate instead of executing when enabled
# --------------------------------------------------------------------------- #
def is_readonly() -> bool:
    """True when READONLY_MODE is enabled (no changes are actually made)."""
    return os.environ.get("READONLY_MODE", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def readonly_response(action: str, **details) -> dict:
    """Standard 'I would have done X' payload returned by write tools in READONLY_MODE."""
    return {
        "readonly_mode": True,
        "simulated": True,
        "action": action,
        "would_have_changed": details,
        "note": (
            "READONLY_MODE is ON — nothing was changed in Google Ads. "
            "Set READONLY_MODE=false in your .env to let this run for real."
        ),
    }


# --------------------------------------------------------------------------- #
# Error handling — every tool returns a readable dict instead of raising
# --------------------------------------------------------------------------- #
def handle_errors(fn):
    """Wrap a tool so any exception becomes a clear, Claude-readable dict.

    Also logs the full error to stderr (per the spec) so it can be surfaced.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError:
            return {
                "error": "credentials_not_found",
                "message": f"Could not find the credentials file at {get_yaml_path()}.",
                "hint": (
                    "Copy google-ads.yaml.example to google-ads.yaml and fill in your "
                    "tokens, or set GOOGLE_ADS_YAML_PATH to point at it."
                ),
            }
        except ValueError as ex:
            return {"error": "invalid_input", "message": str(ex)}
        except Exception as ex:  # noqa: BLE001 — we want to catch everything
            print(f"[google-ads-mcp] error in {fn.__name__}: {ex!r}", file=sys.stderr)

            # Recognize Google Ads API errors specifically, if the lib is present.
            try:
                from google.ads.googleads.errors import GoogleAdsException
            except Exception:  # pragma: no cover - lib not installed
                GoogleAdsException = None

            if GoogleAdsException is not None and isinstance(ex, GoogleAdsException):
                messages = []
                for err in ex.failure.errors:
                    messages.append(err.message)
                joined = " | ".join(messages).lower()
                hint = None
                if "rate" in joined or "quota" in joined or "limit" in joined:
                    hint = (
                        "You may have hit the Google Ads API daily quota "
                        "(10,000 requests/day on basic access). Try again later."
                    )
                elif "customer" in joined and ("not found" in joined or "invalid" in joined):
                    hint = "Check the customer_id — it must be the 10-digit account ID."
                elif "authentication" in joined or "token" in joined or "credential" in joined:
                    hint = (
                        "Your credentials may have expired. Re-generate the refresh_token "
                        "(Google invalidates tokens unused for 6 months)."
                    )
                return {
                    "error": "google_ads_api_error",
                    "messages": messages,
                    "request_id": getattr(ex, "request_id", None),
                    "hint": hint,
                }

            return {"error": type(ex).__name__, "message": str(ex)}

    return wrapper
