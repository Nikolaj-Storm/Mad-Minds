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
