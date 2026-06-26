"""Shared helpers for all Meta Ads MCP tools.

Mirrors ``gads_mcp/client.py`` so the two servers feel identical to maintain.
This module centralizes:
  * the per-request Graph API client (built from the CURRENT marketer's own
    Facebook access token — see ``get_client``),
  * normalizing / resolving the ad-account ID (Meta uses an ``act_<id>`` form),
  * the date window builder shared by the insights tool,
  * the READONLY_MODE safety flag,
  * a single error handler that turns any failure into a readable dict so
    Claude can explain it to the user instead of crashing.

All network access goes through ``httpx`` against the Graph API. Imports of
``httpx`` are top-level (it is a light dependency and a transitive dep of
fastmcp), but the FastMCP request-context import in ``get_client`` is lazy so
this module stays importable in tests without a live server.

KEY DIFFERENCES vs the Google Ads version (intentional, see NOTICE.md):
  * Auth secret is a Facebook **App** (``META_APP_ID`` / ``META_APP_SECRET``),
    NOT a Google Ads developer token. There is no per-call developer-token
    header — the per-user OAuth access token carries all the authority.
  * Money fields (budgets, spend) are **minor currency units** (e.g. cents/øre),
    divide by 100 — not micros (1e6) like Google Ads.
  * Ad-account IDs are prefixed ``act_`` in API paths.
"""

import os
import re
import sys
import json
import functools
from datetime import datetime

import httpx


# --------------------------------------------------------------------------- #
# Graph API version — pin it; bump deliberately when Meta deprecates a version.
# --------------------------------------------------------------------------- #
DEFAULT_GRAPH_VERSION = "v25.0"  # newest live version as of 2026-06; bump deliberately


def graph_version() -> str:
    return os.environ.get("GRAPH_API_VERSION", DEFAULT_GRAPH_VERSION)


# Ad-account.account_status integer codes -> readable labels (Marketing API).
ACCOUNT_STATUS = {
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


def account_status_label(code) -> str:
    """Map an account_status int to a readable label (passes through unknowns)."""
    try:
        return ACCOUNT_STATUS.get(int(code), str(code))
    except (TypeError, ValueError):
        return str(code)


def graph_base() -> str:
    return f"https://graph.facebook.com/{graph_version()}"


# --------------------------------------------------------------------------- #
# Date window — shared by the insights tool (get_performance)
# --------------------------------------------------------------------------- #
# Presets the Graph Insights API understands as ``date_preset`` literals. We
# whitelist them so a value can be passed straight through without surprises.
ALLOWED_DATE_PRESETS = {
    "today",
    "yesterday",
    "last_3d",
    "last_7d",
    "last_14d",
    "last_28d",
    "last_30d",
    "last_90d",
    "this_week_mon_today",
    "last_week_mon_sun",
    "this_month",
    "last_month",
    "this_quarter",
    "last_quarter",
    "this_year",
    "last_year",
    "maximum",
}

# Strict YYYY-MM-DD, anchored. Meta's time_range JSON wants ISO calendar dates;
# this guard also stops anything weird being injected into the JSON blob.
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_iso_date(value: str, field: str) -> str:
    """Return ``value`` if it is a strict YYYY-MM-DD calendar date, else raise."""
    if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
        raise ValueError(
            f"{field} must be in YYYY-MM-DD format (e.g. 2026-03-01); got {value!r}."
        )
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"{field} {value!r} is not a real calendar date (use YYYY-MM-DD)."
        )
    return value


def build_insights_params(
    date_preset: str = "last_30d",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Build the Graph Insights date parameters shared by the reporting tool.

    Returns a dict of query params to merge into an ``/insights`` request:
      * ``start_date`` AND ``end_date`` (both YYYY-MM-DD) -> a custom range
        ``{"time_range": {"since": ..., "until": ...}}`` (JSON-encoded). Explicit
        dates WIN: any ``date_preset`` is ignored when both dates are supplied.
      * Neither given -> ``{"date_preset": <preset>}`` (default ``last_30d``).
      * Exactly one of ``start_date`` / ``end_date`` -> ValueError.

    Raises ValueError (surfaced by ``handle_errors`` as ``invalid_input``) on a
    bad date format, an impossible date, a reversed range, a lone date, or an
    unknown preset. Dates resolve in the ad account's reporting time zone.
    """
    has_start = start_date is not None and start_date != ""
    has_end = end_date is not None and end_date != ""

    if has_start ^ has_end:
        raise ValueError(
            "Provide BOTH start_date and end_date (YYYY-MM-DD), or neither. "
            f"Got start_date={start_date!r}, end_date={end_date!r}."
        )

    if has_start and has_end:
        start = _validate_iso_date(start_date, "start_date")
        end = _validate_iso_date(end_date, "end_date")
        if end < start:  # zero-padded ISO dates sort lexicographically
            raise ValueError(
                f"end_date ({end}) must not be before start_date ({start})."
            )
        return {"time_range": json.dumps({"since": start, "until": end})}

    preset = (date_preset or "last_30d").lower()
    if preset not in ALLOWED_DATE_PRESETS:
        raise ValueError(
            f"date_preset '{preset}' is not a supported Meta Insights preset. "
            f"Allowed: {', '.join(sorted(ALLOWED_DATE_PRESETS))}. "
            "Or pass explicit start_date and end_date (YYYY-MM-DD)."
        )
    return {"date_preset": preset}


# --------------------------------------------------------------------------- #
# Ad-account ID handling — Meta uses the "act_<digits>" form in API paths
# --------------------------------------------------------------------------- #
def normalize_account_id(account_id) -> str:
    """Return the bare numeric id, stripping any ``act_`` prefix and separators.

    'act_123456' -> '123456'; '123-456' -> '123456'.
    """
    return "".join(ch for ch in str(account_id) if ch.isdigit())


def act_path(account_id) -> str:
    """Return the ``act_<digits>`` path segment the Graph API expects."""
    return f"act_{normalize_account_id(account_id)}"


def resolve_account_id(account_id=None) -> str:
    """Use the supplied account ID, else fall back to ``META_AD_ACCOUNT_ID``.

    Lets a marketer set their default account once in ``.env`` and then talk to
    Claude without pasting the id every time. Returns the bare numeric id.
    """
    aid = account_id or os.environ.get("META_AD_ACCOUNT_ID")
    if not aid:
        raise ValueError(
            "No account_id was provided and META_AD_ACCOUNT_ID is not set. "
            "Provide the ad-account ID (the digits, with or without 'act_')."
        )
    return normalize_account_id(aid)


# --------------------------------------------------------------------------- #
# Per-user Graph API client
# --------------------------------------------------------------------------- #
class MetaApiError(Exception):
    """Raised when the Graph API returns an ``error`` object."""

    def __init__(self, error: dict):
        self.error = error or {}
        super().__init__(self.error.get("message", "Meta Graph API error"))


class GraphClient:
    """Thin synchronous Graph API client bound to one marketer's access token.

    Not cached: each request is a different signed-in user, exactly like the
    Google Ads client is rebuilt per request.
    """

    def __init__(self, access_token: str, version: str | None = None, timeout: float = 60.0):
        self.token = access_token
        self.base = f"https://graph.facebook.com/{version or graph_version()}"
        self.timeout = timeout

    def _json(self, resp: httpx.Response) -> dict:
        try:
            payload = resp.json()
        except Exception:
            resp.raise_for_status()
            raise
        if isinstance(payload, dict) and payload.get("error"):
            raise MetaApiError(payload["error"])
        return payload

    def get(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        params["access_token"] = self.token
        return self._json(httpx.get(f"{self.base}/{path}", params=params, timeout=self.timeout))

    def get_all(self, path: str, params: dict | None = None, max_pages: int = 25) -> list:
        """Follow cursor pagination and return the concatenated ``data`` rows."""
        params = dict(params or {})
        params["access_token"] = self.token
        url = f"{self.base}/{path}"
        rows: list = []
        for _ in range(max_pages):
            payload = self._json(httpx.get(url, params=params, timeout=self.timeout))
            rows.extend(payload.get("data", []))
            nxt = (payload.get("paging") or {}).get("next")
            if not nxt:
                break
            url, params = nxt, None  # the 'next' URL already carries token + cursor
        return rows

    def post(self, path: str, data: dict | None = None) -> dict:
        data = dict(data or {})
        data["access_token"] = self.token
        return self._json(httpx.post(f"{self.base}/{path}", data=data, timeout=self.timeout))


def get_token() -> str:
    """Return the CURRENT request's marketer Facebook access token (per-user OAuth)."""
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()
    access_token = getattr(token, "token", None)
    if not access_token:
        raise ValueError(
            "Not signed in. Connect Meta Ads (sign in with Facebook) and try again."
        )
    return access_token


def get_client() -> GraphClient:
    """Build a Graph API client for the CURRENT request's signed-in marketer.

    Per-user OAuth: the access token comes from the FastMCP OAuth proxy (the
    marketer's own Facebook sign-in), so they only touch ad accounts they
    already have. Unlike Google Ads there is NO server-side developer token to
    attach per call — the app credentials only matter during the OAuth handshake.
    """
    return GraphClient(get_token())


# --------------------------------------------------------------------------- #
# Money helpers — Meta amounts are MINOR currency units (e.g. cents), not micros
# --------------------------------------------------------------------------- #
def minor_to_major(amount) -> float:
    """'50000' (minor units) -> 500.00 in whole currency units."""
    try:
        return round(int(amount) / 100, 2)
    except (TypeError, ValueError):
        return 0.0


def major_to_minor(amount) -> int:
    """500 -> 50000 minor units for write requests."""
    return int(round(float(amount) * 100))


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
            "READONLY_MODE is ON — nothing was changed in Meta Ads. "
            "Set READONLY_MODE=false to let this run for real."
        ),
    }


# --------------------------------------------------------------------------- #
# Error handling — every tool returns a readable dict instead of raising
# --------------------------------------------------------------------------- #
def handle_errors(fn):
    """Wrap a tool so any exception becomes a clear, Claude-readable dict.

    Also logs the full error to stderr so it can be surfaced.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as ex:
            return {"error": "invalid_input", "message": str(ex)}
        except MetaApiError as ex:
            err = ex.error
            code = err.get("code")
            subcode = err.get("error_subcode")
            message = err.get("message", "")
            low = message.lower()
            hint = None
            if code in (4, 17, 32, 613) or "rate" in low or "limit" in low:
                hint = (
                    "You may have hit a Meta Marketing API rate limit (per-app or "
                    "per-ad-account). Wait and retry, or narrow the request."
                )
            elif code == 190 or "access token" in low or "session" in low:
                hint = (
                    "Your Facebook sign-in may have expired. Reconnect the Meta Ads "
                    "connector (Meta user tokens are long-lived ~60 days, not refreshed "
                    "indefinitely like Google)."
                )
            elif code in (10, 200, 803) or "permission" in low:
                hint = (
                    "Missing permission/role. The signed-in user needs a role on this "
                    "ad account, and the app needs ads_read (and ads_management for "
                    "writes), with App Review/Advanced Access granted for non-admins."
                )
            print(f"[meta-ads-mcp] error in {fn.__name__}: {message!r}", file=sys.stderr)
            return {
                "error": "meta_api_error",
                "message": message,
                "code": code,
                "error_subcode": subcode,
                "fbtrace_id": err.get("fbtrace_id"),
                "hint": hint,
            }
        except httpx.HTTPError as ex:
            print(f"[meta-ads-mcp] http error in {fn.__name__}: {ex!r}", file=sys.stderr)
            return {"error": "http_error", "message": str(ex)}
        except Exception as ex:  # noqa: BLE001 — catch everything, return readable
            print(f"[meta-ads-mcp] error in {fn.__name__}: {ex!r}", file=sys.stderr)
            return {"error": type(ex).__name__, "message": str(ex)}

    return wrapper
