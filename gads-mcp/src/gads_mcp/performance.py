"""Reporting tools: get_performance and get_search_terms."""

from .client import get_client, resolve_customer_id, handle_errors, build_date_filter

ALLOWED_LEVELS = {"campaign", "ad_group", "ad"}


def _metrics_dict(metrics) -> dict:
    """Turn a Google Ads metrics row into clean, human-friendly numbers."""
    spend = metrics.cost_micros / 1_000_000
    impressions = metrics.impressions
    clicks = metrics.clicks
    conversions = metrics.conversions
    conv_value = metrics.conversions_value
    return {
        "impressions": int(impressions),
        "clicks": int(clicks),
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
    date_range: str = "LAST_30_DAYS",
    level: str = "campaign",
    customer_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    login_customer_id: str | None = None,
) -> list | dict:
    """Get Google Ads performance metrics (impressions, clicks, spend, conversions, ROAS, CPA).

    Works for ANY time period. Two ways to set the window — pick whichever matches
    what the user asked for:
      * start_date + end_date (YYYY-MM-DD) for an explicit custom range — a specific
        month or quarter, year-to-date, or anything OLDER than 30 days that the
        presets can't reach (e.g. "2026-03-01".."2026-03-31" for March 2026, or
        "2026-01-01".."2026-03-31" for Q1).
      * date_range preset literal for common rolling windows.
    Don't restrict yourself to the presets — if the user names a month, quarter, or
    arbitrary span, pass start_date/end_date.

    Args:
        date_range: Preset literal for rolling windows — TODAY, YESTERDAY, LAST_7_DAYS,
            LAST_14_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH (and a few other Google
            literals). Used only when start_date/end_date are omitted. Default LAST_30_DAYS.
        start_date: Custom-range start, "YYYY-MM-DD". Pair with end_date. Takes precedence
            over date_range when both ends are given. Ranges older than 30 days are fine.
        end_date: Custom-range end, "YYYY-MM-DD". Must be paired with start_date.
            Dates use the account's reporting time zone (no conversion).
        level: Aggregation level — "campaign", "ad_group", or "ad".
        customer_id: 10-digit account ID — a CLIENT account, not a manager/MCC account
            (managers have no metrics). Optional if GOOGLE_ADS_CUSTOMER_ID is set.
        login_customer_id: Manager (MCC) 10-digit ID to send as login-customer-id, for
            querying client accounts under a manager. Optional; falls back to the
            GOOGLE_ADS_LOGIN_CUSTOMER_ID env var.
    """
    date_filter = build_date_filter(date_range, start_date, end_date)
    if level not in ALLOWED_LEVELS:
        return {
            "error": "invalid_level",
            "message": f"'{level}' is not supported.",
            "allowed": sorted(ALLOWED_LEVELS),
        }

    client = get_client(login_customer_id)
    cid = resolve_customer_id(customer_id)
    ga_service = client.get_service("GoogleAdsService")

    metric_fields = (
        "metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "metrics.conversions, metrics.conversions_value"
    )

    if level == "campaign":
        query = f"""
            SELECT campaign.id, campaign.name, {metric_fields}
            FROM campaign
            WHERE {date_filter}
            ORDER BY metrics.cost_micros DESC
        """
    elif level == "ad_group":
        query = f"""
            SELECT campaign.name, ad_group.id, ad_group.name, {metric_fields}
            FROM ad_group
            WHERE {date_filter}
            ORDER BY metrics.cost_micros DESC
        """
    else:  # ad
        query = f"""
            SELECT campaign.name, ad_group.name, ad_group_ad.ad.id, {metric_fields}
            FROM ad_group_ad
            WHERE {date_filter}
            ORDER BY metrics.cost_micros DESC
        """

    results = []
    for row in ga_service.search(customer_id=cid, query=query):
        rec = _metrics_dict(row.metrics)
        if level == "campaign":
            rec = {"campaign_id": str(row.campaign.id), "campaign": row.campaign.name, **rec}
        elif level == "ad_group":
            rec = {
                "campaign": row.campaign.name,
                "ad_group_id": str(row.ad_group.id),
                "ad_group": row.ad_group.name,
                **rec,
            }
        else:
            rec = {
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "ad_id": str(row.ad_group_ad.ad.id),
                **rec,
            }
        results.append(rec)
    return results


@handle_errors
def get_search_terms(
    date_range: str = "LAST_30_DAYS",
    campaign_id: str | None = None,
    limit: int = 100,
    customer_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    login_customer_id: str | None = None,
) -> list | dict:
    """Get the search terms report — the actual searches that triggered your ads.

    Works for ANY time period: pass start_date + end_date (YYYY-MM-DD) for an explicit
    custom range — a specific month or quarter, or anything OLDER than 30 days — or a
    date_range preset for common rolling windows. If the user names a month/quarter or
    arbitrary span, use start_date/end_date rather than forcing a preset.

    Args:
        date_range: Preset literal (e.g. LAST_30_DAYS). Used only when start_date/end_date
            are omitted. Default LAST_30_DAYS.
        start_date: Custom-range start, "YYYY-MM-DD". Pair with end_date. Takes precedence
            over date_range when both ends are given. Ranges older than 30 days are fine.
        end_date: Custom-range end, "YYYY-MM-DD". Must be paired with start_date.
            Dates use the account's reporting time zone (no conversion).
        campaign_id: Optional — restrict to one campaign.
        limit: Max rows to return (default 100).
        customer_id: 10-digit account ID — a CLIENT account, not a manager/MCC account.
            Optional if GOOGLE_ADS_CUSTOMER_ID is set.
        login_customer_id: Manager (MCC) 10-digit ID to send as login-customer-id, for
            querying client accounts under a manager. Optional; falls back to the
            GOOGLE_ADS_LOGIN_CUSTOMER_ID env var.
    """
    date_filter = build_date_filter(date_range, start_date, end_date)

    client = get_client(login_customer_id)
    cid = resolve_customer_id(customer_id)
    ga_service = client.get_service("GoogleAdsService")

    where = [date_filter]
    if campaign_id:
        where.append(f"campaign.id = {int(campaign_id)}")
    where_clause = " AND ".join(where)

    query = f"""
        SELECT search_term_view.search_term, campaign.name, ad_group.name,
               segments.search_term_match_type,
               metrics.impressions, metrics.clicks, metrics.cost_micros,
               metrics.conversions
        FROM search_term_view
        WHERE {where_clause}
        ORDER BY metrics.impressions DESC
        LIMIT {int(limit)}
    """

    results = []
    for row in ga_service.search(customer_id=cid, query=query):
        results.append(
            {
                "search_term": row.search_term_view.search_term,
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "match_type": row.segments.search_term_match_type.name,
                "impressions": int(row.metrics.impressions),
                "clicks": int(row.metrics.clicks),
                "spend": round(row.metrics.cost_micros / 1_000_000, 2),
                "conversions": round(row.metrics.conversions, 2),
            }
        )
    return results
