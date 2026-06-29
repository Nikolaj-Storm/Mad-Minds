"""Per-user Google OAuth credentials + helpers for the GA4 (Analytics) connector.

MARKETER variant — the sibling of the marketer ``gads-mcp``. Auth is the signed-in
marketer's OWN Google OAuth (an access/refresh token from their Google sign-in),
NOT a shared service account. The connector talks to two Analytics APIs on the
user's behalf:
  * Analytics **Data** API (``google-analytics-data``) — runs reports.
  * Analytics **Admin** API (``google-analytics-admin``) — lists the properties the
    user can read (so they can discover property IDs).

GA4 is reporting-only for marketers, so the scope is read-only and there are no
write/mutate tools — there is nothing meaningful to write in Analytics.

----------------------------------------------------------------------------
WIRING NOTE for the Mad-Minds repo:
This module builds OAuth ``Credentials`` from environment variables so it runs
standalone out of the box (Claude Desktop: set them in the MCP server's env). If
Mad-Minds already injects each marketer's Google token through a shared OAuth
helper (the way ``gads-mcp`` / the Google connector do), replace the body of
``get_credentials`` with a call into that helper and keep the rest unchanged.
----------------------------------------------------------------------------
"""
import functools
import os
import re
import sys

# Read-only Analytics scope.
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REL_DATE_RE = re.compile(r"^\d+daysAgo$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")  # GA4 metric/dimension API names


def get_credentials():
    """Build the marketer's Google OAuth credentials.

    Default implementation reads a per-user refresh token + OAuth client from env:
      GA4_OAUTH_CLIENT_ID, GA4_OAUTH_CLIENT_SECRET, GA4_OAUTH_REFRESH_TOKEN.
    The google-auth library refreshes the access token automatically. Swap this for
    the repo's shared OAuth helper if one exists (see module docstring).
    """
    from google.oauth2.credentials import Credentials

    client_id = os.environ.get("GA4_OAUTH_CLIENT_ID") or os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = (
        os.environ.get("GA4_OAUTH_CLIENT_SECRET") or os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    )
    refresh_token = (
        os.environ.get("GA4_OAUTH_REFRESH_TOKEN") or os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN")
    )
    if not (client_id and client_secret and refresh_token):
        raise ValueError(
            "Missing Google OAuth credentials. Set GA4_OAUTH_CLIENT_ID, "
            "GA4_OAUTH_CLIENT_SECRET and GA4_OAUTH_REFRESH_TOKEN (the marketer's own "
            "Google sign-in), or wire get_credentials() into the repo's OAuth helper."
        )
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def data_client():
    """Analytics Data API client (run_report / run_realtime_report)."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient(credentials=get_credentials())


def admin_client():
    """Analytics Admin API client (list account summaries / properties)."""
    from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
    return AnalyticsAdminServiceClient(credentials=get_credentials())


# --------------------------------------------------------------------------- #
# Property id + name validation
# --------------------------------------------------------------------------- #
def normalize_property_id(property_id) -> str:
    """Strip everything but digits, so 'properties/123', '123' -> '123'."""
    return "".join(ch for ch in str(property_id) if ch.isdigit())


def resolve_property_id(property_id=None) -> str:
    """Use the supplied property ID, else fall back to GA4_PROPERTY_ID env."""
    pid = property_id if (property_id not in (None, "")) else os.environ.get("GA4_PROPERTY_ID")
    pid = normalize_property_id(pid) if pid else ""
    if not pid:
        raise ValueError(
            "No property_id was provided and GA4_PROPERTY_ID is not set. "
            "Provide the numeric GA4 property ID (see list_properties)."
        )
    return pid


def validate_ga4_date(value: str, field: str) -> str:
    """Return ``value`` if it is a GA4-valid date, else raise ValueError.

    Accepts a strict ISO ``YYYY-MM-DD`` calendar date, or one of the relative
    tokens the Data API understands: ``today``, ``yesterday`` or ``NdaysAgo``.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string date; got {value!r}.")
    v = value.strip()
    if v in ("today", "yesterday") or _REL_DATE_RE.match(v):
        return v
    if _ISO_DATE_RE.match(v):
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"{field} {value!r} is not a real calendar date (use YYYY-MM-DD).")
        return v
    raise ValueError(
        f"{field} must be YYYY-MM-DD, 'today', 'yesterday' or 'NdaysAgo' "
        f"(e.g. '28daysAgo'); got {value!r}."
    )


def validate_names(values, field: str) -> list:
    """Validate a list of GA4 metric/dimension API names (alphanumeric + underscore)."""
    out = []
    for v in values:
        name = str(v).strip()
        if not _NAME_RE.match(name):
            raise ValueError(
                f"{field} {v!r} is not a valid GA4 API name "
                "(letters, digits and underscores only, e.g. 'sessionDefaultChannelGroup')."
            )
        out.append(name)
    if not out:
        raise ValueError(f"{field} must contain at least one name.")
    return out


def coerce(value: str):
    """Best-effort numeric coercion of a GA4 string value (metrics come as strings)."""
    if value is None:
        return None
    try:
        if "." in value or "e" in value or "E" in value:
            return round(float(value), 4)
        return int(value)
    except (TypeError, ValueError):
        return value


# --------------------------------------------------------------------------- #
# Error handling — every tool returns a readable dict instead of raising
# --------------------------------------------------------------------------- #
def handle_errors(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as ex:
            return {"error": "invalid_input", "message": str(ex)}
        except Exception as ex:  # noqa: BLE001 — surface everything as a dict
            print(f"[ga4-mcp] error in {fn.__name__}: {ex!r}", file=sys.stderr)
            msg = str(ex)
            low = msg.lower()
            hint = None
            if "permission" in low or "denied" in low or "403" in low:
                hint = (
                    "Your Google account may not have access to this property. Check "
                    "GA4 Admin -> Property Access Management, or re-authorize the sign-in."
                )
            elif "invalid_grant" in low or "token" in low or "credential" in low:
                hint = "Your Google sign-in may have expired — reconnect the account."
            elif "not found" in low or ("invalid" in low and "property" in low):
                hint = "Check the property_id — use list_properties to find the numeric ID."
            elif "quota" in low or "exhausted" in low or "rate" in low:
                hint = "You may have hit the Analytics Data API quota. Try again later."
            out = {"error": type(ex).__name__, "message": msg}
            if hint:
                out["hint"] = hint
            return out
    return wrapper
