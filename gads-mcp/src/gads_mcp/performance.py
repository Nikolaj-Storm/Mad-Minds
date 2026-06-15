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
) -> list | dict:
    """Get Google Ads performance metrics (impressions, clicks, spend, conversions, ROAS, CPA).

    Args:
        date_range: A Google date-range literal — one of TODAY, YESTERDAY,
            LAST_7_DAYS, LAST_14_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH (and a
            few other Google range literals). Used only when start_date/end_date
            are omitted.
        level: Aggregation level — "campaign", "ad_group", or "ad".
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
        start_date: Optional custom-range start, "YYYY-MM-DD". Must be paired with end_date.
        end_date: Optional custom-range end, "YYYY-MM-DD". Must be paired with start_date.
            When both are given they take precedence over date_range and let you
            pull any period — including older than 30 days — e.g.
            start_date="2026-03-01", end_date="2026-03-31" for March 2026.
            Interpreted in the account's reporting time zone (no conversion).
    """
    date_filter = build_date_filter(date_range, start_date, end_date)
    if level not in ALLOWED_LEVELS:
        return {
            "error": "invalid_level",
            "message": f"'{level}' is not supported.",
            "allowed": sorted(ALLOWED_LEVELS),
        }

    client = get_client()
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
) -> list | dict:
    """Get the search terms report — the actual searches that triggered your ads.

    Args:
        date_range: A Google date-range literal (e.g. LAST_30_DAYS). Used only
            when start_date/end_date are omitted.
        campaign_id: Optional — restrict to one campaign.
        limit: Max rows to return (default 100).
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
        start_date: Optional custom-range start, "YYYY-MM-DD". Must be paired with end_date.
        end_date: Optional custom-range end, "YYYY-MM-DD". Must be paired with start_date.
            When both are given they take precedence over date_range, e.g.
            start_date="2026-03-01", end_date="2026-03-31".
            Interpreted in the account's reporting time zone (no conversion).
    """
    date_filter = build_date_filter(date_range, start_date, end_date)

    client = get_client()
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
