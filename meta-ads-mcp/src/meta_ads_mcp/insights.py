"""Reporting tool: get_performance (Meta Insights).

Meta returns conversions inside an ``actions`` array (one row per action type:
purchase, lead, complete_registration, offsite_conversion.fb_pixel_purchase, …)
rather than a single "conversions" number, because the right conversion differs
per brand (signup vs purchase vs lead). So we surface impressions/clicks/spend/
CTR/CPC/CPM directly and hand back ``actions`` / ``action_values`` as
{action_type: number} maps plus Meta's own ``purchase_roas`` — letting each
brand's conversion definition pick the right line.
"""

from .client import get_api, resolve_account_id, handle_errors, build_time_params

ALLOWED_LEVELS = {"account", "campaign", "adset", "ad"}


def _num(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return v


def _metrics(row) -> dict:
    spend = float(row.get("spend") or 0)
    impressions = int(row.get("impressions") or 0)
    clicks = int(row.get("clicks") or 0)
    out = {
        "impressions": impressions,
        "clicks": clicks,
        "spend": round(spend, 2),
        "ctr": round(float(row.get("ctr") or 0), 4),
        "cpc": round(float(row.get("cpc") or 0), 2),
        "cpm": round(float(row.get("cpm") or 0), 2),
    }
    actions = {
        a["action_type"]: _num(a.get("value"))
        for a in (row.get("actions") or [])
        if a.get("action_type") is not None
    }
    values = {
        a["action_type"]: _num(a.get("value"))
        for a in (row.get("action_values") or [])
        if a.get("action_type") is not None
    }
    if actions:
        out["actions"] = actions
    if values:
        out["action_values"] = values
    roas = row.get("purchase_roas")
    if roas:
        try:
            out["purchase_roas"] = round(float(roas[0]["value"]), 2)
        except (TypeError, ValueError, KeyError, IndexError):
            pass
    return out


# Which id/name fields to request and surface, per aggregation level.
_LEVEL_DIMENSIONS = {
    "account": [],
    "campaign": ["campaign_id", "campaign_name"],
    "adset": ["campaign_name", "adset_id", "adset_name"],
    "ad": ["campaign_name", "adset_name", "ad_id", "ad_name"],
}


@handle_errors
def get_performance(
    date_preset: str = "last_30d",
    level: str = "campaign",
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
) -> list | dict:
    """Get Meta performance metrics (impressions, clicks, spend, CTR, CPC, CPM, conversions, ROAS).

    Works for ANY time period. Two ways to set the window — pick whichever matches
    what the user asked for:
      * start_date + end_date (YYYY-MM-DD) for an explicit custom range — a specific
        month or quarter, year-to-date, or anything the presets can't reach.
      * date_preset for common rolling windows.
    Don't restrict yourself to the presets — if the user names a month, quarter, or
    arbitrary span, pass start_date/end_date.

    Args:
        date_preset: Preset literal for rolling windows — today, yesterday, last_7d,
            last_14d, last_28d, last_30d, last_90d, this_month, last_month, this_quarter,
            last_quarter, this_year, last_year, maximum. Used only when start_date/end_date
            are omitted. Default last_30d.
        level: Aggregation level — "account", "campaign", "adset", or "ad".
        account_id: The ad account ID ("act_…" or its digits). Optional if META_AD_ACCOUNT_ID is set.
        start_date: Custom-range start, "YYYY-MM-DD". Pair with end_date. Takes precedence
            over date_preset when both ends are given.
        end_date: Custom-range end, "YYYY-MM-DD". Must be paired with start_date.
        limit: Max rows to return (default 200).
    """
    time_params = build_time_params(date_preset, start_date, end_date)
    if level not in ALLOWED_LEVELS:
        return {
            "error": "invalid_level",
            "message": f"'{level}' is not supported.",
            "allowed": sorted(ALLOWED_LEVELS),
        }

    from facebook_business.adobjects.adaccount import AdAccount

    api = get_api()
    acct = AdAccount(resolve_account_id(account_id), api=api)

    dimensions = _LEVEL_DIMENSIONS[level]
    metric_fields = [
        "impressions",
        "clicks",
        "spend",
        "ctr",
        "cpc",
        "cpm",
        "actions",
        "action_values",
        "purchase_roas",
    ]
    fields = dimensions + metric_fields
    params = {"level": level, "limit": int(limit), **time_params}

    results = []
    for row in acct.get_insights(fields=fields, params=params):
        rec = {dim: row.get(dim) for dim in dimensions}
        rec.update(_metrics(row))
        results.append(rec)
        if len(results) >= int(limit):
            break
    return results
# Attribution windows Meta actually supports on action_attribution_windows.
_ALLOWED_LAG_WINDOWS = {"1d_click", "7d_click", "28d_click", "1d_view", "7d_view", "28d_view"}
_LAG_WINDOW_DAYS = {"1d_click": 1, "7d_click": 7, "28d_click": 28,
                     "1d_view": 1, "7d_view": 7, "28d_view": 28}
DEFAULT_LAG_WINDOWS = ["1d_click", "7d_click", "28d_click"]


@handle_errors
def get_conversion_lag(
    action_type: str = "complete_registration",
    date_preset: str = "last_30d",
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    windows: list[str] | None = None,
) -> dict:
    """Approximate "days to conversion" for Meta via attribution-window comparison.

    THIS IS NOT THE SAME KIND OF MEASUREMENT AS GOOGLE ADS' get_conversion_lag.
    Meta's Insights API has no per-click lag-bucket histogram (no
    segments.conversion_lag_bucket equivalent) -- the only lever Meta exposes is
    action_attribution_windows, which changes WHICH actions get counted for a
    given click-through window, not a true elapsed-time-since-click distribution.

    This tool pulls the SAME date range once per attribution window (1d_click,
    7d_click, 28d_click by default) and diffs the counts for one action_type, to
    approximate how much of the eventual count has "landed" by each window.

    READ BEFORE TRUSTING THIS NUMBER:
      - Coarse resolution: only 1d/7d/28d click (or view) windows exist -- nowhere
        near Google's day-by-day buckets out to day 240.
      - Not a strict lag distribution: a wider window can credit a DIFFERENT click
        entirely (a user who clicked two different ads on two different days), not
        just the same population converting later. Attribution-window growth and
        pure lag growth are correlated but not identical.
      - "28d_click" is the practical ceiling this tool can query. It is NOT a
        settled/eventual total the way the house model's day-240 curve is --
        treat it as "best available Meta-native estimate", not "final".
      - Same date-window caveat as the Google tool: this filters by CLICK date
        (time_range / date_preset). A very recent window under-reports every
        milestone simply because time hasn't passed yet.

    Args:
        action_type: Which Meta action_type to measure (e.g. "complete_registration",
            "offsite_conversion.custom.<pixel_event_id>"). Meta has no single
            universal "conversions" field the way Google Ads does, so this must be
            explicit. Defaults to "complete_registration" (Rentumo's trial-signup
            action, matching the existing META REP. column convention).
        date_preset / start_date / end_date: same as get_performance.
        account_id: Meta ad-account ID. Optional if META_AD_ACCOUNT_ID is set.
        windows: attribution windows to compare. Defaults to
            ["1d_click", "7d_click", "28d_click"]. Must be valid Meta literals
            (1d_click, 7d_click, 28d_click, 1d_view, 7d_view, 28d_view).

    Returns a dict with:
        action_type, windows_requested, counts: {window: raw action count},
        widest_window: the largest window queried (used as the denominator),
        pct_of_widest: {window: round(100 * count / count[widest_window], 1)} --
            NOT the same quantity as Google's same_day_pct / within_N_days_pct;
            treat as a rough proxy only.
        note: the caveat text above, repeated here so it survives even if a
            downstream consumer only logs/stores the dict.
    """
    from facebook_business.adobjects.adaccount import AdAccount

    win_list = windows or list(DEFAULT_LAG_WINDOWS)
    bad = [w for w in win_list if w not in _ALLOWED_LAG_WINDOWS]
    if bad:
        return {
            "error": "invalid_windows",
            "message": f"Unsupported attribution window(s): {bad}.",
            "allowed": sorted(_ALLOWED_LAG_WINDOWS),
        }

    time_params = build_time_params(date_preset, start_date, end_date)
    api = get_api()
    acct = AdAccount(resolve_account_id(account_id), api=api)

    counts: dict[str, float] = {}
    for window in win_list:
        params = {"level": "account", "action_attribution_windows": [window], **time_params}
        total = 0.0
        for row in acct.get_insights(fields=["actions"], params=params):
            for a in (row.get("actions") or []):
                if a.get("action_type") == action_type:
                    try:
                        total += float(a.get("value") or 0)
                    except (TypeError, ValueError):
                        pass
        counts[window] = round(total, 2)

    widest = max(win_list, key=lambda w: _LAG_WINDOW_DAYS.get(w, 0))
    denom = counts.get(widest) or 0
    pct_of_widest = {
        w: (round(100 * c / denom, 1) if denom else None)
        for w, c in counts.items()
    }

    return {
        "action_type": action_type,
        "windows_requested": win_list,
        "counts": counts,
        "widest_window": widest,
        "pct_of_widest": pct_of_widest,
        "note": (
            "Meta has no per-click lag histogram like Google Ads. This compares "
            "action counts across attribution windows for the same date range as "
            "a coarse proxy -- NOT a true elapsed-time-since-click distribution. "
            f"'{widest}' is the widest window queried, used as the denominator; "
            "it is Meta's best-available count, not a settled/eventual total the "
            "way Google's 240-day house model is."
        ),
    }
