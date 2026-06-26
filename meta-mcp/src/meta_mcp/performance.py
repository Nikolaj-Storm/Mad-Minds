"""Reporting tool: get_performance (Meta Insights).

Meta's Insights edge replaces Google's GAQL. Conversions are not a single metric;
they arrive as an ``actions`` array (and ``action_values`` for revenue), so we
sum the action types that represent conversions. Spend/CTR/CPC come back directly.
"""

from .client import (
    get_client,
    resolve_account_id,
    act_path,
    handle_errors,
    build_insights_params,
)

ALLOWED_LEVELS = {"account", "campaign", "adset", "ad"}

# Action types that count as a "conversion" for headline ROAS/CPA. Covers the
# common pixel + standard events; extend as the brands' events require.
_CONVERSION_ACTIONS = {
    "purchase",
    "omni_purchase",
    "offsite_conversion.fb_pixel_purchase",
    "lead",
    "offsite_conversion.fb_pixel_lead",
    "onsite_conversion.lead_grouped",
    "complete_registration",
    "offsite_conversion.fb_pixel_complete_registration",
}


def _sum_actions(actions, wanted) -> float:
    total = 0.0
    for a in actions or []:
        if a.get("action_type") in wanted:
            try:
                total += float(a.get("value", 0) or 0)
            except (TypeError, ValueError):
                pass
    return total


def _insights_row(r: dict) -> dict:
    """Turn one Insights row into clean, human-friendly numbers."""
    spend = float(r.get("spend", 0) or 0)
    impressions = int(float(r.get("impressions", 0) or 0))
    clicks = int(float(r.get("clicks", 0) or 0))
    conversions = _sum_actions(r.get("actions"), _CONVERSION_ACTIONS)
    conv_value = _sum_actions(r.get("action_values"), _CONVERSION_ACTIONS)
    return {
        "impressions": impressions,
        "clicks": clicks,
        "spend": round(spend, 2),
        "conversions": round(conversions, 2),
        "conversions_value": round(conv_value, 2),
        "ctr": round(clicks / impressions, 4) if impressions else 0.0,
        "avg_cpc": round(spend / clicks, 2) if clicks else 0.0,
        "cpa": round(spend / conversions, 2) if conversions else None,
        "roas": round(conv_value / spend, 2) if spend else 0.0,
    }


@handle_errors
def get_performance(
    date_preset: str = "last_30d",
    level: str = "campaign",
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list | dict:
    """Get Meta Ads performance (impressions, clicks, spend, conversions, ROAS, CPA).

    Works for ANY time period. Two ways to set the window — pick whichever matches
    what the user asked for:
      * start_date + end_date (YYYY-MM-DD) for an explicit custom range — a specific
        month or quarter, year-to-date, or anything OLDER than 30 days the presets
        can't reach (e.g. "2026-03-01".."2026-03-31" for March 2026).
      * date_preset for common rolling windows.
    Don't restrict yourself to the presets — if the user names a month, quarter, or
    arbitrary span, pass start_date/end_date.

    Args:
        date_preset: Preset for rolling windows — today, yesterday, last_7d,
            last_14d, last_30d, last_90d, this_month, last_month, this_quarter,
            maximum (and others). Used only when start_date/end_date are omitted.
            Default last_30d.
        start_date: Custom-range start, "YYYY-MM-DD". Pair with end_date. Takes
            precedence over date_preset when both ends are given. Older than 30 days OK.
        end_date: Custom-range end, "YYYY-MM-DD". Must be paired with start_date.
            Dates use the ad account's reporting time zone (no conversion).
        level: Aggregation level — "account", "campaign", "adset", or "ad".
        account_id: Ad-account id (digits or 'act_' form). Optional if
            META_AD_ACCOUNT_ID is set.
    """
    if level not in ALLOWED_LEVELS:
        return {
            "error": "invalid_level",
            "message": f"'{level}' is not supported.",
            "allowed": sorted(ALLOWED_LEVELS),
        }
    date_params = build_insights_params(date_preset, start_date, end_date)

    client = get_client()
    aid = act_path(resolve_account_id(account_id))

    id_fields = {
        "account": "account_id,account_name",
        "campaign": "campaign_id,campaign_name",
        "adset": "campaign_name,adset_id,adset_name",
        "ad": "campaign_name,adset_name,ad_id,ad_name",
    }[level]
    params = {
        "level": level,
        "fields": f"{id_fields},impressions,clicks,spend,actions,action_values",
        "limit": 500,
        **date_params,
    }
    rows = client.get_all(f"{aid}/insights", params)

    results = []
    for r in rows:
        rec = _insights_row(r)
        if level == "account":
            rec = {"account_id": r.get("account_id"), "account": r.get("account_name"), **rec}
        elif level == "campaign":
            rec = {"campaign_id": r.get("campaign_id"), "campaign": r.get("campaign_name"), **rec}
        elif level == "adset":
            rec = {
                "campaign": r.get("campaign_name"),
                "adset_id": r.get("adset_id"),
                "adset": r.get("adset_name"),
                **rec,
            }
        else:
            rec = {
                "campaign": r.get("campaign_name"),
                "adset": r.get("adset_name"),
                "ad_id": r.get("ad_id"),
                "ad": r.get("ad_name"),
                **rec,
            }
        results.append(rec)
    # Insights doesn't guarantee spend-desc ordering across pages; sort for parity
    # with the Google Ads tool, which ORDER BYs cost desc.
    results.sort(key=lambda x: x.get("spend", 0), reverse=True)
    return results
