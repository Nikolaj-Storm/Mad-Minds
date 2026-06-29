"""Google Analytics (GA4) MCP Server — utility functions."""

import re
from datetime import datetime

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REL_DATE_RE = re.compile(r"^\d+daysAgo$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")  # GA4 metric/dimension API names


def normalize_property_id(property_id) -> str:
    """Strip everything but digits, so 'properties/123' or '123' -> '123'."""
    return "".join(ch for ch in str(property_id) if ch.isdigit())


def validate_ga4_date(value: str, field: str) -> str:
    """Return ``value`` if it is a GA4-valid date, else raise ValueError.

    Accepts a strict ISO ``YYYY-MM-DD`` calendar date, or a relative token the
    Data API understands: ``today``, ``yesterday`` or ``NdaysAgo`` (e.g. ``28daysAgo``).
    """
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string date; got {value!r}.")
    v = value.strip()
    if v in ("today", "yesterday") or _REL_DATE_RE.match(v):
        return v
    if _ISO_DATE_RE.match(v):
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


def coerce(value):
    """Best-effort numeric coercion of a GA4 string value (metrics come as strings)."""
    if value is None:
        return None
    try:
        if "." in value or "e" in value or "E" in value:
            return round(float(value), 4)
        return int(value)
    except (TypeError, ValueError):
        return value


def format_error_message(error: Exception) -> str:
    """Format an error for user-friendly display (mirrors the gsc-mcp helper)."""
    error_str = str(error)
    low = error_str.lower()
    if "403" in error_str or "permission" in low or "denied" in low:
        return ("Permission denied. Make sure your Google account has access to this GA4 "
                "property (Admin -> Property Access Management), then re-Connect if needed.")
    if "404" in error_str or "not found" in low:
        return "Not found. Check the property_id — use list_properties to find the numeric ID."
    if "401" in error_str or "invalid_grant" in low:
        return "Authentication failed. Please re-authenticate with Google (re-Connect)."
    if "429" in error_str or "quota" in low or "exhausted" in low:
        return "Rate limit / quota exceeded on the Analytics API. Please try again later."
    if "400" in error_str:
        return f"Invalid request: {error_str}"
    return f"An error occurred: {error_str}"
