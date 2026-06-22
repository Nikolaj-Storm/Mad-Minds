"""Shared helpers for all Meta (Facebook/Instagram) Ads MCP tools.

This is the Meta counterpart of ``gads_mcp/client.py``. It centralizes:
  * building a per-request Meta Marketing API client from the signed-in
    marketer's own Facebook access token (NEVER the SDK global singleton —
    that would leak one user's token into another user's concurrent request),
  * normalizing / resolving the ad-account ID (``act_<digits>``),
  * minor-unit (cents/øre) <-> whole-currency conversion for budgets,
  * the READONLY_MODE safety flag,
  * a date/time-range builder shared by the insights tools,
  * a single error handler that turns any failure into a readable dict so
    Claude can explain it to the user instead of crashing.

All ``facebook_business`` imports are done lazily inside functions so this
module (and the tool modules that import from it) stay importable even when
the ``facebook-business`` package is not installed — handy for the unit tests,
which exercise the pure query/param building without the SDK or a network.
"""

import os
import re
import sys
import functools
from datetime import datetime


# --------------------------------------------------------------------------- #
# Date ranges — shared by the insights tools (get_performance)
# --------------------------------------------------------------------------- #
# The exact ``date_preset`` literals the Meta Marketing API accepts (mirrored
# from facebook_business.adobjects.adsinsights.AdsInsights.DatePreset). We
# whitelist them so an arbitrary string can never be passed through as a preset.
ALLOWED_DATE_PRESETS = {
    "today",
    "yesterday",
    "this_week_mon_today",
    "this_week_sun_today",
    "last_week_mon_sun",
    "last_week_sun_sat",
    "last_3d",
    "last_7d",
    "last_14d",
    "last_28d",
    "last_30d",
    "last_90d",
    "this_month",
    "last_month",
    "this_quarter",
    "last_quarter",
    "this_year",
    "last_year",
    "maximum",
    "data_maximum",
}

# Strict YYYY-MM-DD. Anchored so the WHOLE string must be a plain ISO date.
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_iso_date(value: str, field: str) -> str:
    """Return ``value`` if it is a strict YYYY-MM-DD calendar date, else raise.

    Two stages: the regex rejects anything that isn't exactly ``YYYY-MM-DD``,
    and ``strptime`` rejects impossible dates such as ``2026-02-31``.
    """
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


def build_time_params(
    date_preset: str = "last_30d",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Build the time portion of a Meta Insights ``params`` dict.

    Returns a dict to merge into the insights request params:
      * ``{"time_range": {"since": ..., "until": ...}}`` for an explicit custom
        range, or
      * ``{"date_preset": "<preset>"}`` for a rolling window.

    Rules (identical shape to the Google Ads ``build_date_filter``):
      * ``start_date`` AND ``end_date`` (both YYYY-MM-DD) -> a custom
        ``time_range``. Explicit dates WIN: any ``date_preset`` is ignored when
        both dates are supplied.
      * Neither given -> ``date_preset`` (default ``last_30d``).
      * Exactly one of ``start_date`` / ``end_date`` -> ValueError.

    Dates are matched against the ad account's reporting time zone by Meta; they
    are passed through verbatim with no timezone conversion.
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
        # Zero-padded ISO dates sort lexicographically, so a string compare is a
        # correct ordering check.
        if end < start:
            raise ValueError(
                f"end_date ({end}) must not be before start_date ({start})."
            )
        return {"time_range": {"since": start, "until": end}}

    preset = (date_preset or "last_30d").lower()
    if preset not in ALLOWED_DATE_PRESETS:
        raise ValueError(
            f"date_preset '{preset}' is not a supported Meta literal. "
            f"Allowed: {', '.join(sorted(ALLOWED_DATE_PRESETS))}. "
            "Or pass explicit start_date and end_date (YYYY-MM-DD)."
        )
    return {"date_preset": preset}


# --------------------------------------------------------------------------- #
# Configuration / credentials
# --------------------------------------------------------------------------- #
def get_api():
    """Build a Meta Marketing API client for the CURRENT request's marketer.

    Per-user OAuth: the access token comes from the FastMCP Facebook OAuth proxy
    (the marketer's own Facebook sign-in), so they can only touch ad accounts
    they already have access to. The Facebook App ID/Secret are server-side env
    secrets (one app for the whole org), used by the SDK to sign API calls.

    A FRESH ``FacebookAdsApi`` instance is built per request and handed to each
    ad object via ``api=`` — we never call ``FacebookAdsApi.init()`` (which sets
    a process-wide default and would let concurrent users' tokens collide).
    """
    from facebook_business.api import FacebookAdsApi
    from facebook_business.session import FacebookSession
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()
    access_token = getattr(token, "token", None)
    if not access_token:
        raise ValueError(
            "Not signed in. Connect Meta Ads (sign in with Facebook) and try again."
        )

    app_id = os.environ.get("META_APP_ID") or None
    app_secret = os.environ.get("META_APP_SECRET") or None
    api_version = os.environ.get("META_GRAPH_VERSION") or None  # None -> SDK default

    session = FacebookSession(
        app_id=app_id,
        app_secret=app_secret,
        access_token=access_token,
    )
    return FacebookAdsApi(session, api_version=api_version)


def normalize_account_id(account_id) -> str:
    """Return a Meta ad-account ID in canonical ``act_<digits>`` form.

    Accepts ``123456``, ``act_123456`` or ``act_123-456`` and returns
    ``act_123456``.
    """
    digits = "".join(ch for ch in str(account_id) if ch.isdigit())
    if not digits:
        raise ValueError(
            f"{account_id!r} is not a valid Meta ad-account ID "
            "(expected digits, optionally prefixed with 'act_')."
        )
    return f"act_{digits}"


def resolve_account_id(account_id=None) -> str:
    """Use the supplied account ID, else fall back to META_AD_ACCOUNT_ID.

    Lets a marketer set their default account once and then talk to Claude
    without pasting the ``act_…`` ID every time.
    """
    acct = account_id or os.environ.get("META_AD_ACCOUNT_ID")
    if not acct:
        raise ValueError(
            "No account_id was provided and META_AD_ACCOUNT_ID is not set. "
            "Provide the Meta ad-account ID (the 'act_…' value, or just its digits)."
        )
    return normalize_account_id(acct)


# --------------------------------------------------------------------------- #
# Money — Meta amounts are integer minor units (cents/øre) of the account currency
# --------------------------------------------------------------------------- #
# Most currencies OnlineMinds uses (DKK, EUR, USD, GBP) have 2 minor digits, so
# whole units <-> minor units is * / 100. Zero-decimal currencies (e.g. JPY,
# HUF) do NOT divide; those accounts would need special handling — flagged in
# the runbook. The reporting currency is fixed per ad account.
MINOR_UNITS_PER_UNIT = 100


def minor_to_units(amount) -> float | None:
    """Convert an integer minor-unit string/number (e.g. '50000') to whole units.

    Returns ``None`` when the field is absent (e.g. a campaign with no
    campaign-level budget because the budget lives on its ad sets).
    """
    if amount is None or amount == "":
        return None
    try:
        return round(int(amount) / MINOR_UNITS_PER_UNIT, 2)
    except (TypeError, ValueError):
        return None


def units_to_minor(amount) -> int:
    """Convert a whole-currency amount (e.g. 500.0) to integer minor units."""
    return int(round(float(amount) * MINOR_UNITS_PER_UNIT))


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
            "Set READONLY_MODE=false on the server to let this run for real."
        ),
    }


# --------------------------------------------------------------------------- #
# Error handling — every tool returns a readable dict instead of raising
# --------------------------------------------------------------------------- #
def handle_errors(fn):
    """Wrap a tool so any exception becomes a clear, Claude-readable dict.

    Also logs the full error to stderr so it can be surfaced in server logs.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as ex:
            return {"error": "invalid_input", "message": str(ex)}
        except Exception as ex:  # noqa: BLE001 — we want to catch everything
            print(f"[meta-ads-mcp] error in {fn.__name__}: {ex!r}", file=sys.stderr)

            # Recognize Meta Marketing API errors specifically, if the lib is present.
            try:
                from facebook_business.exceptions import FacebookRequestError
            except Exception:  # pragma: no cover - lib not installed
                FacebookRequestError = None

            if FacebookRequestError is not None and isinstance(ex, FacebookRequestError):
                code = ex.api_error_code()
                subcode = None
                try:
                    body = ex.body() or {}
                    subcode = (body.get("error") or {}).get("error_subcode")
                except Exception:  # pragma: no cover
                    body = {}
                message = ex.api_error_message()
                low = f"{message}".lower()
                hint = None
                # 17 = user request limit, 4 = app rate limit, 80004 = ads rate limit.
                if code in (17, 4, 80000, 80004) or "rate" in low or "limit" in low:
                    hint = (
                        "You may have hit a Meta Marketing API rate limit. Wait a few "
                        "minutes and retry, or narrow the date range / number of rows."
                    )
                # 190 = access token expired/invalid.
                elif code == 190 or "token" in low or "session" in low:
                    hint = (
                        "Your Facebook sign-in may have expired (Meta tokens last ~60 "
                        "days). Re-connect Meta Ads in Claude's Connectors to refresh it."
                    )
                # 200/10/803 = permission problems.
                elif code in (200, 10, 803) or "permission" in low or "(#200)" in low:
                    hint = (
                        "Your Facebook user can't perform this on that ad account. "
                        "Check you have the right role in the Business Manager."
                    )
                return {
                    "error": "meta_api_error",
                    "code": code,
                    "subcode": subcode,
                    "message": message,
                    "type": ex.api_error_type(),
                    "hint": hint,
                }

            return {"error": type(ex).__name__, "message": str(ex)}

    return wrapper
