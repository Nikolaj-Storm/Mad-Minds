"""Rentumo Trials MCP server — remote SSE, shared server-side bearer.

Mirrors the Thribee connector's auth model: there is NO per-user OAuth. A single
shared admin bearer token (RENTUMO_BEARER_TOKEN) works across every market's admin
API and stays a server-side secret, so the connector is pre-wired in the plugin
(.mcp.json) and needs no marketer action — exactly like Thribee.

Each market is a Rentumo domain exposing `GET /api/admin/charts`. We read the full
`.totals` object (new_subscriptions and whatever else the endpoint returns) so the
connector stays useful for other Rentumo KPIs, while surfacing new_subscriptions —
the "new subscribers" / trials figure — as a first-class field.

Read-only: this server only ever issues GET requests. There is no write path and no
spend-gate surface here.
"""

import asyncio
import json
import os
import urllib.parse

import httpx
from fastmcp import FastMCP

# --- Config (server-side secrets / data) -------------------------------------

def _clean_secret(v: str) -> str:
    """Strip control chars and surrounding whitespace from a credential read from
    the environment. Pasting a token through nano/SSH can inject a trailing
    newline, a \\r, or stray spaces — which sail past a non-empty check but make
    the upstream API reject every request with 401. Mirrors meta-ads-mcp.
    """
    return "".join(ch for ch in (v or "") if ch >= " ").strip()


_RAW_BEARER_TOKEN = os.environ.get("RENTUMO_BEARER_TOKEN", "")
RENTUMO_BEARER_TOKEN = _clean_secret(_RAW_BEARER_TOKEN)

# Markets (code + public admin domain) ship bundled next to this module — they
# contain no secrets. To swap the list without rebuilding the image, mount an
# override file and point RENTUMO_MARKETS_FILE at it (e.g. /data/markets.json).
_DEFAULT_MARKETS_FILE = os.path.join(os.path.dirname(__file__), "markets.json")
MARKETS_FILE = os.environ.get("RENTUMO_MARKETS_FILE", _DEFAULT_MARKETS_FILE)

# Cap concurrent upstream calls so a portfolio-wide pull can't open 26+ sockets at
# once. The original batch job used many threads; async with a semaphore is plenty.
MAX_CONCURRENCY = int(os.environ.get("RENTUMO_MAX_CONCURRENCY", "12"))

REQUEST_TIMEOUT = float(os.environ.get("RENTUMO_REQUEST_TIMEOUT", "30"))


def _load_markets():
    """Return [{code, domain, name?}, ...] from MARKETS_FILE (empty list if absent)."""
    try:
        with open(MARKETS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    # Accept either a bare list or {"markets": [...]}.
    markets = data.get("markets", data) if isinstance(data, dict) else data
    out = []
    for m in markets or []:
        if isinstance(m, dict) and m.get("code") and m.get("domain"):
            out.append(
                {
                    "code": str(m["code"]).upper(),
                    "domain": str(m["domain"]).strip().rstrip("/"),
                    "name": m.get("name") or str(m["code"]).upper(),
                }
            )
    return out


MARKETS = _load_markets()
_MARKETS_BY_CODE = {m["code"]: m for m in MARKETS}


# --- Date handling -----------------------------------------------------------

def _to_rentumo_date(iso_date: str) -> str:
    """Convert an ISO `YYYY-MM-DD` to the admin API's `D. M. YYYY` (no zero-pad).

    e.g. "2026-06-25" -> "25. 6. 2026". The model always passes ISO; the quirky
    format and its URL-encoding stay here so callers never deal with it.
    """
    parts = iso_date.strip().split("-")
    if len(parts) != 3:
        raise ValueError(f"start_date/end_date must be ISO YYYY-MM-DD, got {iso_date!r}")
    year, month, day = (int(p) for p in parts)
    return f"{day}. {month}. {year}"


SERVER_INSTRUCTIONS = (
    "Rentumo new-subscriber (trial) data across all markets, read-only.\n\n"
    "WHAT IT RETURNS: each market's admin `/api/admin/charts` totals for a date "
    "range. `new_subscriptions` is the new-subscribers / trials figure surfaced as a "
    "first-class field; the full `totals` object is also returned for any other KPIs "
    "the endpoint exposes.\n\n"
    "DATE RANGES: pass start_date and end_date as ISO YYYY-MM-DD. The range is "
    "inclusive. Dates resolve in each market's admin timezone.\n\n"
    "TOOLS: call rentumo_list_markets first to see the market codes. "
    "rentumo_get_trials(market, start, end) pulls one market; "
    "rentumo_get_all_trials(start, end) pulls every market in parallel and returns "
    "the per-market breakdown plus the portfolio total new_subscriptions. There is no "
    "write path — this connector is reporting only."
)

mcp = FastMCP(name="Rentumo Trials", instructions=SERVER_INSTRUCTIONS)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse

    return JSONResponse(
        {
            "status": "healthy",
            "service": "Rentumo Trials MCP",
            "markets_loaded": len(MARKETS),
            "token_present": bool(RENTUMO_BEARER_TOKEN),
            # Diagnostics — never the secret itself. token_was_dirty=true means the
            # env value had whitespace/control chars we stripped (a likely 401 cause).
            "token_len": len(RENTUMO_BEARER_TOKEN),
            "token_was_dirty": _RAW_BEARER_TOKEN != RENTUMO_BEARER_TOKEN,
        }
    )


# --- Upstream fetch -----------------------------------------------------------

async def _fetch_market_totals(client: httpx.AsyncClient, market: dict,
                               start_iso: str, end_iso: str) -> dict:
    """Fetch one market's `.totals`. Returns a result dict (never raises)."""
    domain = market["domain"]
    start = urllib.parse.quote(_to_rentumo_date(start_iso))
    end = urllib.parse.quote(_to_rentumo_date(end_iso))
    url = (
        f"https://{domain}/api/admin/charts"
        f"?start_date={start}&end_date={end}"
    )
    try:
        resp = await client.get(
            url, headers={"Authorization": f"Bearer {RENTUMO_BEARER_TOKEN}"}
        )
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPStatusError as exc:
        return {"code": market["code"], "domain": domain,
                "error": f"HTTP {exc.response.status_code}"}
    except (httpx.HTTPError, ValueError) as exc:
        return {"code": market["code"], "domain": domain,
                "error": f"{type(exc).__name__}: {exc}"}

    totals = payload.get("totals", {}) if isinstance(payload, dict) else {}
    return {
        "code": market["code"],
        "name": market["name"],
        "domain": domain,
        "new_subscriptions": totals.get("new_subscriptions"),
        "totals": totals,
    }


def _require_config():
    """Return an error string if the server isn't configured, else None."""
    if not RENTUMO_BEARER_TOKEN:
        return "RENTUMO_BEARER_TOKEN is not set on the server — cannot query the admin API."
    if not MARKETS:
        return (f"No markets loaded (looked in {MARKETS_FILE}). The maintainer must "
                f"provide markets.json — see markets.example.json for the schema.")
    return None


# --- Tools -------------------------------------------------------------------

@mcp.tool
def rentumo_list_markets() -> dict:
    """List the Rentumo markets this connector can pull new-subscriber data for.

    Returns each market's code, display name, and admin domain. Call this first to
    learn the valid `market` codes for rentumo_get_trials.
    """
    return {"count": len(MARKETS), "markets": MARKETS}


@mcp.tool
async def rentumo_get_trials(market: str, start_date: str, end_date: str) -> dict:
    """Get new subscribers (trials) for ONE market over a date range.

    Args:
        market: Market code from rentumo_list_markets (e.g. "NL"). Case-insensitive.
        start_date: Inclusive start, ISO YYYY-MM-DD.
        end_date: Inclusive end, ISO YYYY-MM-DD.

    Returns the market's new_subscriptions and the full admin `totals` object.
    """
    err = _require_config()
    if err:
        return {"error": err}
    m = _MARKETS_BY_CODE.get(market.strip().upper())
    if not m:
        return {"error": f"Unknown market {market!r}. Call rentumo_list_markets for valid codes."}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        result = await _fetch_market_totals(client, m, start_date, end_date)
    result["start_date"] = start_date
    result["end_date"] = end_date
    return result


@mcp.tool
async def rentumo_get_all_trials(start_date: str, end_date: str) -> dict:
    """Get new subscribers (trials) for EVERY market over a date range, in parallel.

    Args:
        start_date: Inclusive start, ISO YYYY-MM-DD.
        end_date: Inclusive end, ISO YYYY-MM-DD.

    Returns a per-market breakdown, the portfolio total new_subscriptions (summing
    markets that returned a number), and any per-market errors.
    """
    err = _require_config()
    if err:
        return {"error": err}

    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def _bounded(client, m):
        async with sem:
            return await _fetch_market_totals(client, m, start_date, end_date)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        results = await asyncio.gather(*[_bounded(client, m) for m in MARKETS])

    ok = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]
    total_new = sum(
        r["new_subscriptions"] for r in ok
        if isinstance(r.get("new_subscriptions"), (int, float))
    )
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_new_subscriptions": total_new,
        "markets_ok": len(ok),
        "markets_failed": len(errors),
        "markets": ok,
        "errors": errors,
    }
