"""Rentumo Conversions MCP server — remote SSE, read-only, NO auth.

RENTUMO ONLY. This connector reports conversion / UTM-attribution data for the
**Rentumo** brand exclusively. It does NOT cover Adsumo, Printumo, Bidumo,
Monetumo, Photumo, or Jacob Lund Art (JLA). Do not present its numbers as
portfolio-wide — every figure here is Rentumo, per market.

WHAT IT WRAPS — two public S3 feeds per market on the `kuhamia` bucket:

  1. utm-feed-rentumo-<feed>.json
     A first-touch / last-touch ATTRIBUTION feed. One record per Rentumo
     conversion, each carrying the UTM parameters (+ gclid / msclkid) of the
     FIRST touchpoint that started the journey and the LAST touchpoint before
     converting. No PII. Answers "which channel/campaign drove this conversion,
     by first vs last touch?". This is where channels like `Lifull-connect`,
     `google`, `fb`, `search_agent_mailer` etc. show up as `utm_source`.

  2. google-ads-offline-conversions-feed-rentumo-<feed>.csv
     A Google Ads "Offline Conversion Import"-formatted feed: one row per
     subscription / renewal conversion with Google Click ID, Conversion Name
     ("Subscription renewal" / "RevenueCat Subscription"), Conversion Value +
     Currency, consent flags, a SHA-256-HASHED email, utm_source and last login.
     This is the file that gets uploaded to Google Ads to import real
     subscription revenue back against ad clicks. Carries MONEY (per-market
     currency) so you can see conversion VALUE per channel, not just counts.

AUTH MODEL — none. The feeds are public objects on S3, so there is no bearer and
no per-user OAuth. The connector is pre-wired in the plugin (.mcp.json) and needs
no marketer Connect step (like Thribee / Rentumo Trials, but with no secret at
all).

PRIVACY — the CSV's `Email` column is a SHA-256 hash, and the tools here NEVER
return raw rows or any email (hashed or not). Everything is aggregated: counts,
summed value, and breakdowns by a UTM dimension. There is no way to pull an
individual person's record through this server.

CURRENCY — the offline-conversion feed's value is in each market's own currency
(EUR for the euro markets, etc.); the currency is read from the feed's own
`Conversion Currency` column and echoed back. Never sum value across markets
without converting.

Read-only: this server only ever issues GET requests against public URLs. There
is no write path and no spend-gate surface here.
"""

import asyncio
import csv
import io
import json
import os
import time

import httpx
from fastmcp import FastMCP

# --- Config ------------------------------------------------------------------

# Public S3 bucket that hosts the Rentumo feeds. Overridable for testing.
FEED_BASE_URL = os.environ.get(
    "RENTUMO_CONV_FEED_BASE_URL",
    "https://kuhamia.s3.eu-central-1.amazonaws.com",
).rstrip("/")

# Filename templates — `{feed}` is the per-market slug from markets.json.
UTM_FEED_TEMPLATE = os.environ.get(
    "RENTUMO_CONV_UTM_TEMPLATE", "utm-feed-rentumo-{feed}.json"
)
OFFLINE_FEED_TEMPLATE = os.environ.get(
    "RENTUMO_CONV_OFFLINE_TEMPLATE",
    "google-ads-offline-conversions-feed-rentumo-{feed}.csv",
)

# Markets (code + feed slug) ship bundled next to this module — no secrets.
# Override without rebuilding by mounting a file and setting RENTUMO_CONV_MARKETS_FILE.
_DEFAULT_MARKETS_FILE = os.path.join(os.path.dirname(__file__), "markets.json")
MARKETS_FILE = os.environ.get("RENTUMO_CONV_MARKETS_FILE", _DEFAULT_MARKETS_FILE)

REQUEST_TIMEOUT = float(os.environ.get("RENTUMO_CONV_REQUEST_TIMEOUT", "60"))

# The feeds are multi-MB and change at most daily, so cache parsed feeds in
# memory for a while to keep repeated tool calls (e.g. several date ranges or
# group_by views of the same market) snappy. TTL in seconds; 0 disables.
CACHE_TTL = float(os.environ.get("RENTUMO_CONV_CACHE_TTL", "900"))

# Valid UTM dimensions to group / break down by (present on each touchpoint).
GROUPABLE_FIELDS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
)

NONE_LABEL = "(none)"
OTHER_LABEL = "(other)"


def _load_markets():
    """Return [{code, feed, name}, ...] from MARKETS_FILE (empty list if absent)."""
    try:
        with open(MARKETS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    markets = data.get("markets", data) if isinstance(data, dict) else data
    out = []
    for m in markets or []:
        if isinstance(m, dict) and m.get("code") and m.get("feed"):
            out.append(
                {
                    "code": str(m["code"]).upper(),
                    "feed": str(m["feed"]).strip().lower(),
                    "name": m.get("name") or str(m["code"]).upper(),
                }
            )
    return out


MARKETS = _load_markets()
_MARKETS_BY_CODE = {m["code"]: m for m in MARKETS}

# Simple in-process feed cache: url -> (expires_at_epoch, parsed_value).
_CACHE: dict[str, tuple[float, object]] = {}


SERVER_INSTRUCTIONS = (
    "Rentumo conversion & UTM-attribution data, read-only. RENTUMO BRAND ONLY — "
    "these numbers do NOT cover Adsumo, Printumo, Bidumo, Monetumo, Photumo or JLA, "
    "and are per market (never a portfolio total).\n\n"
    "TWO DATA VIEWS, both per market:\n"
    "  * ATTRIBUTION (utm-feed JSON): one record per conversion with the FIRST-touch "
    "and LAST-touch UTM parameters. Use conversions_get_attribution to see which "
    "utm_source / utm_medium / utm_campaign / utm_content / utm_term drove conversions, "
    "by first vs last touch. No money, no PII.\n"
    "  * OFFLINE CONVERSIONS (Google Ads offline-import CSV): one row per subscription / "
    "renewal with Conversion Value (MONEY) + Currency, Conversion Name, gclid and a "
    "hashed email. Use conversions_get_offline_summary for counts AND value per channel. "
    "Emails are never returned — output is always aggregated.\n\n"
    "FOCUS HELPER: conversions_get_source(market, source, start, end) pulls one channel "
    "(e.g. 'Lifull-connect') across BOTH feeds at once.\n\n"
    "DATES: pass start_date and end_date as ISO YYYY-MM-DD; the range is inclusive and "
    "filters on each record's conversion timestamp (in the feed's local +0200-style offset).\n\n"
    "CURRENCY: offline-conversion value is in each market's own currency (read from the "
    "feed). Do NOT sum value across markets without converting.\n\n"
    "Call conversions_list_markets first for the valid market codes. There is no write path."
)

mcp = FastMCP(name="Rentumo Conversions", instructions=SERVER_INSTRUCTIONS)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse

    return JSONResponse(
        {
            "status": "healthy",
            "service": "Rentumo Conversions MCP",
            "brand": "Rentumo (only)",
            "markets_loaded": len(MARKETS),
            "feed_base_url": FEED_BASE_URL,
        }
    )


# --- Fetch + cache -----------------------------------------------------------

async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.text


async def _get_utm_records(client: httpx.AsyncClient, market: dict) -> list:
    """Fetch + parse a market's UTM attribution JSON feed (cached)."""
    url = f"{FEED_BASE_URL}/{UTM_FEED_TEMPLATE.format(feed=market['feed'])}"
    now = time.monotonic()
    hit = _CACHE.get(url)
    if hit and hit[0] > now:
        return hit[1]
    text = await _fetch_text(client, url)
    data = json.loads(text)
    records = data if isinstance(data, list) else data.get("data", [])
    if CACHE_TTL > 0:
        _CACHE[url] = (now + CACHE_TTL, records)
    return records


async def _get_offline_rows(client: httpx.AsyncClient, market: dict) -> list:
    """Fetch + parse a market's offline-conversion CSV feed (cached)."""
    url = f"{FEED_BASE_URL}/{OFFLINE_FEED_TEMPLATE.format(feed=market['feed'])}"
    now = time.monotonic()
    hit = _CACHE.get(url)
    if hit and hit[0] > now:
        return hit[1]
    text = await _fetch_text(client, url)
    rows = list(csv.DictReader(io.StringIO(text)))
    if CACHE_TTL > 0:
        _CACHE[url] = (now + CACHE_TTL, rows)
    return rows


# --- Helpers -----------------------------------------------------------------

def _market_or_error(market: str):
    if not MARKETS:
        return None, (
            f"No markets loaded (looked in {MARKETS_FILE}). The maintainer must "
            f"provide markets.json."
        )
    m = _MARKETS_BY_CODE.get(market.strip().upper())
    if not m:
        return None, (
            f"Unknown market {market!r}. Call conversions_list_markets for valid codes."
        )
    return m, None


def _valid_date(d: str) -> str:
    parts = d.strip().split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"date must be ISO YYYY-MM-DD, got {d!r}")
    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"


def _conv_date(ts: str) -> str:
    """Pull the YYYY-MM-DD date out of a feed timestamp.

    Both feeds stamp local time with a +0200-style offset; the JSON uses a space
    before the offset, the CSV does not. We only need the date for range
    filtering, and that is the first 10 chars in both formats.
    """
    return (ts or "")[:10]


def _in_range(ts: str, start: str, end: str) -> bool:
    d = _conv_date(ts)
    return bool(d) and start <= d <= end


def _explain_fetch_error(market: dict, exc: Exception) -> dict:
    """Map a fetch failure to a friendly per-market error (never raises)."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (403, 404):
            return {
                "error": (
                    f"Feed not available for market {market['code']} "
                    f"(HTTP {status}). This Rentumo market's feed may not be "
                    f"generated upstream yet."
                )
            }
        return {"error": f"HTTP {status} fetching feed for {market['code']}."}
    return {"error": f"{type(exc).__name__}: {exc}"}


def _breakdown(counts: dict, values: dict | None, top: int) -> dict:
    """Sort a {label: count} dict desc, keep top N, fold the rest into (other)."""
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    head = items[:top]
    tail = items[top:]
    out = []
    for label, cnt in head:
        entry = {"value": label, "conversions": cnt}
        if values is not None:
            entry["conversion_value"] = round(values.get(label, 0.0), 2)
        out.append(entry)
    if tail:
        other_cnt = sum(c for _, c in tail)
        entry = {"value": OTHER_LABEL, "conversions": other_cnt,
                 "distinct_collapsed": len(tail)}
        if values is not None:
            entry["conversion_value"] = round(
                sum(values.get(lbl, 0.0) for lbl, _ in tail), 2
            )
        out.append(entry)
    return {"distinct_values": len(items), "breakdown": out}


# --- Tools -------------------------------------------------------------------

@mcp.tool
def conversions_list_markets() -> dict:
    """List the Rentumo markets this connector can pull conversion data for.

    RENTUMO BRAND ONLY. Returns each market's code, display name, and feed slug.
    Call this first to learn the valid `market` codes for the other tools.
    """
    return {
        "brand": "Rentumo (only)",
        "count": len(MARKETS),
        "markets": MARKETS,
    }


@mcp.tool
async def conversions_get_attribution(
    market: str,
    start_date: str,
    end_date: str,
    group_by: str = "utm_source",
    touchpoint: str = "first",
    top: int = 50,
) -> dict:
    """Rentumo conversions broken down by a UTM dimension (first/last-touch attribution).

    Reads the market's utm-feed (one record per Rentumo conversion, no PII, no
    money) and groups conversions in the date range by the chosen UTM field of the
    chosen touchpoint. Use this to answer "which source / campaign drove how many
    conversions, by first vs last touch?".

    Args:
        market: Market code from conversions_list_markets (e.g. "FR"). Case-insensitive.
        start_date: Inclusive start, ISO YYYY-MM-DD (filters on conversion time).
        end_date: Inclusive end, ISO YYYY-MM-DD.
        group_by: One of utm_source, utm_medium, utm_campaign, utm_content, utm_term.
        touchpoint: "first" (the journey's first touch) or "last" (last touch before
            converting). First-touch is more complete in this data.
        top: Keep the top N values; the rest are folded into an "(other)" bucket.

    Returns the total conversions in range, the count whose chosen field was blank,
    and the breakdown sorted by conversions descending. Counts only — no value.
    """
    m, err = _market_or_error(market)
    if err:
        return {"error": err}
    if group_by not in GROUPABLE_FIELDS:
        return {"error": f"group_by must be one of {', '.join(GROUPABLE_FIELDS)}."}
    tp_key = {"first": "first_touchpoint", "last": "last_touchpoint"}.get(
        touchpoint.strip().lower()
    )
    if not tp_key:
        return {"error": "touchpoint must be 'first' or 'last'."}
    try:
        start = _valid_date(start_date)
        end = _valid_date(end_date)
    except ValueError as exc:
        return {"error": str(exc)}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            records = await _get_utm_records(client, m)
        except Exception as exc:  # noqa: BLE001 — surfaced as a friendly per-market error
            return {"market": m["code"], **_explain_fetch_error(m, exc)}

    counts: dict[str, int] = {}
    total = 0
    blank = 0
    for rec in records:
        if not _in_range(rec.get("conversion_time", ""), start, end):
            continue
        total += 1
        tp = rec.get(tp_key) or {}
        raw = tp.get(group_by)
        label = raw if (raw not in (None, "")) else NONE_LABEL
        if label == NONE_LABEL:
            blank += 1
        counts[label] = counts.get(label, 0) + 1

    bd = _breakdown(counts, None, top)
    return {
        "brand": "Rentumo",
        "market": m["code"],
        "market_name": m["name"],
        "feed": "utm-attribution",
        "touchpoint": touchpoint.strip().lower(),
        "group_by": group_by,
        "start_date": start,
        "end_date": end,
        "total_conversions": total,
        "blank_value_conversions": blank,
        **bd,
    }


@mcp.tool
async def conversions_get_offline_summary(
    market: str,
    start_date: str,
    end_date: str,
    group_by: str = "utm_source",
    top: int = 50,
) -> dict:
    """Rentumo offline conversions: counts AND value, broken down by source.

    Reads the market's Google-Ads offline-conversion CSV (one row per subscription
    / renewal, carrying Conversion Value + Currency). Aggregates the date range:
    totals, a split by Conversion Name (e.g. "Subscription renewal" vs
    "RevenueCat Subscription"), and a per-`group_by` breakdown with both
    conversions and summed value. Emails are hashed in the feed and are NEVER
    returned — output is aggregate only.

    Args:
        market: Market code from conversions_list_markets. Case-insensitive.
        start_date: Inclusive start, ISO YYYY-MM-DD (filters on Conversion Time).
        end_date: Inclusive end, ISO YYYY-MM-DD.
        group_by: "utm_source" (default) or "conversion_name".
        top: Keep the top N values; the rest fold into "(other)".

    Returns total conversions, total value, the currency (read from the feed),
    the share with a Google Click ID, the by-name split, and the breakdown.
    """
    m, err = _market_or_error(market)
    if err:
        return {"error": err}
    gb = group_by.strip().lower()
    if gb not in ("utm_source", "conversion_name"):
        return {"error": "group_by must be 'utm_source' or 'conversion_name'."}
    try:
        start = _valid_date(start_date)
        end = _valid_date(end_date)
    except ValueError as exc:
        return {"error": str(exc)}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            rows = await _get_offline_rows(client, m)
        except Exception as exc:  # noqa: BLE001
            return {"market": m["code"], **_explain_fetch_error(m, exc)}

    col = "utm_source" if gb == "utm_source" else "Conversion Name"
    counts: dict[str, int] = {}
    values: dict[str, float] = {}
    by_name: dict[str, dict] = {}
    total = 0
    total_value = 0.0
    gclid_present = 0
    currencies: set[str] = set()

    for r in rows:
        if not _in_range(r.get("Conversion Time", ""), start, end):
            continue
        total += 1
        try:
            val = float(r.get("Conversion Value") or 0)
        except ValueError:
            val = 0.0
        total_value += val
        if (r.get("Google Click ID") or "").strip():
            gclid_present += 1
        cur = (r.get("Conversion Currency") or "").strip()
        if cur:
            currencies.add(cur)

        raw = (r.get(col) or "").strip()
        label = raw if raw else NONE_LABEL
        counts[label] = counts.get(label, 0) + 1
        values[label] = values.get(label, 0.0) + val

        name = (r.get("Conversion Name") or NONE_LABEL).strip() or NONE_LABEL
        slot = by_name.setdefault(name, {"conversions": 0, "conversion_value": 0.0})
        slot["conversions"] += 1
        slot["conversion_value"] += val

    bd = _breakdown(counts, values, top)
    for slot in by_name.values():
        slot["conversion_value"] = round(slot["conversion_value"], 2)
    return {
        "brand": "Rentumo",
        "market": m["code"],
        "market_name": m["name"],
        "feed": "google-ads-offline-conversions",
        "group_by": gb,
        "start_date": start,
        "end_date": end,
        "total_conversions": total,
        "total_conversion_value": round(total_value, 2),
        "currency": sorted(currencies)[0] if len(currencies) == 1 else sorted(currencies),
        "currency_note": "Value is in the market's own currency — do not sum across markets without converting.",
        "with_google_click_id": gclid_present,
        "by_conversion_name": by_name,
        **bd,
    }


@mcp.tool
async def conversions_get_source(
    market: str,
    source: str,
    start_date: str,
    end_date: str,
) -> dict:
    """One channel (utm_source) across BOTH feeds — e.g. Lifull-connect.

    Convenience focus tool. For the given `source`, returns: first-touch and
    last-touch conversion counts from the attribution feed, and the offline
    conversion count + summed value from the offline-conversion feed. Matching on
    utm_source is case-insensitive. Use this to answer "how many conversions /
    how much value did <channel> drive for Rentumo <market> in this range?".

    Args:
        market: Market code from conversions_list_markets. Case-insensitive.
        source: utm_source value, e.g. "Lifull-connect", "google", "fb".
        start_date: Inclusive start, ISO YYYY-MM-DD.
        end_date: Inclusive end, ISO YYYY-MM-DD.
    """
    m, err = _market_or_error(market)
    if err:
        return {"error": err}
    try:
        start = _valid_date(start_date)
        end = _valid_date(end_date)
    except ValueError as exc:
        return {"error": str(exc)}
    want = source.strip().lower()

    out = {
        "brand": "Rentumo",
        "market": m["code"],
        "market_name": m["name"],
        "source": source,
        "start_date": start,
        "end_date": end,
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Attribution feed (first + last touch counts).
        try:
            records = await _get_utm_records(client, m)
            first_n = last_n = total_conv = 0
            for rec in records:
                if not _in_range(rec.get("conversion_time", ""), start, end):
                    continue
                total_conv += 1
                ft = (rec.get("first_touchpoint") or {}).get("utm_source") or ""
                lt = (rec.get("last_touchpoint") or {}).get("utm_source") or ""
                if ft.strip().lower() == want:
                    first_n += 1
                if lt.strip().lower() == want:
                    last_n += 1
            out["attribution"] = {
                "first_touch_conversions": first_n,
                "last_touch_conversions": last_n,
                "all_conversions_in_range": total_conv,
            }
        except Exception as exc:  # noqa: BLE001
            out["attribution"] = _explain_fetch_error(m, exc)

        # Offline-conversion feed (count + value).
        try:
            rows = await _get_offline_rows(client, m)
            off_n = 0
            off_val = 0.0
            currencies: set[str] = set()
            for r in rows:
                if not _in_range(r.get("Conversion Time", ""), start, end):
                    continue
                if (r.get("utm_source") or "").strip().lower() != want:
                    continue
                off_n += 1
                try:
                    off_val += float(r.get("Conversion Value") or 0)
                except ValueError:
                    pass
                cur = (r.get("Conversion Currency") or "").strip()
                if cur:
                    currencies.add(cur)
            out["offline_conversions"] = {
                "conversions": off_n,
                "conversion_value": round(off_val, 2),
                "currency": sorted(currencies)[0] if len(currencies) == 1
                else sorted(currencies),
            }
        except Exception as exc:  # noqa: BLE001
            out["offline_conversions"] = _explain_fetch_error(m, exc)

    return out
