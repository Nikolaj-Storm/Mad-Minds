"""Reporting tools: get_performance, get_search_terms, get_conversion_lag."""

from .client import get_client, resolve_customer_id, handle_errors, build_date_filter

ALLOWED_LEVELS = {"campaign", "ad_group", "ad"}

# --------------------------------------------------------------------------- #
# Conversion lag buckets -- mirrors Google Ads UI's Segment > Conversions >
# "Days to conversion" view. Each bucket's value is the upper bound (in days,
# from ad interaction to conversion) of that bucket, used to build cumulative
# "landed within N days" milestones. UNKNOWN has no day bound (rare -- e.g.
# conversions without a resolvable click timestamp) and is excluded from the
# milestone math, but still counted in the grand total.
# --------------------------------------------------------------------------- #
CONVERSION_LAG_BUCKET_UPPER_DAYS: dict[str, int] = {
    "LESS_THAN_ONE_DAY": 1,
    "ONE_TO_TWO_DAYS": 2,
    "TWO_TO_THREE_DAYS": 3,
    "THREE_TO_FOUR_DAYS": 4,
    "FOUR_TO_FIVE_DAYS": 5,
    "FIVE_TO_SIX_DAYS": 6,
    "SIX_TO_SEVEN_DAYS": 7,
    "SEVEN_TO_EIGHT_DAYS": 8,
    "EIGHT_TO_NINE_DAYS": 9,
    "NINE_TO_TEN_DAYS": 10,
    "TEN_TO_ELEVEN_DAYS": 11,
    "ELEVEN_TO_TWELVE_DAYS": 12,
    "TWELVE_TO_THIRTEEN_DAYS": 13,
    "THIRTEEN_TO_FOURTEEN_DAYS": 14,
    "FOURTEEN_TO_TWENTY_ONE_DAYS": 21,
    "TWENTY_ONE_TO_THIRTY_DAYS": 30,
    "THIRTY_TO_FORTY_FIVE_DAYS": 45,
    "FORTY_FIVE_TO_SIXTY_DAYS": 60,
    "SIXTY_TO_NINETY_DAYS": 90,
    "NINETY_TO_ONE_HUNDRED_AND_TWENTY_DAYS": 120,
    "ONE_HUNDRED_AND_TWENTY_TO_ONE_HUNDRED_AND_FIFTY_DAYS": 150,
    "ONE_HUNDRED_FIFTY_TO_ONE_HUNDRED_AND_EIGHTY_DAYS": 180,
    "ONE_HUNDRED_AND_EIGHTY_TO_ONE_YEAR": 365,
}

# The milestones surfaced by default -- 0 means "same day" (the
# LESS_THAN_ONE_DAY bucket alone), the rest are "landed within N days".
DEFAULT_MILESTONE_DAYS = (0, 7, 14, 21, 30)


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


@handle_errors
def get_conversion_lag(
    date_range: str = "LAST_30_DAYS",
    customer_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    login_customer_id: str | None = None,
    campaign_id: str | None = None,
    milestone_days: list[int] | None = None,
) -> dict:
    """"Days to conversion" report -- how many days pass between the ad click and
    the conversion. Replicates the Google Ads UI's Segment > Conversions >
    "Days to conversion" view, which is NOT available through get_performance
    (that tool has no segment breakdown). Use this whenever someone asks how
    fast conversions land, wants a cumulative "% converted within N days"
    curve, or wants to know how "mature" a recent week's numbers are before
    judging them.

    Works for ANY time period, same as get_performance: pass start_date +
    end_date (YYYY-MM-DD) for an explicit custom range, or a date_range preset
    for common rolling windows. IMPORTANT: this date range filters the AD
    INTERACTION (click) date, not the conversion date -- so "March 2026" means
    "clicks that happened in March 2026", and the returned percentages show
    how much of THOSE clicks' eventual conversions had already landed by each
    milestone. A very recent window will look artificially low simply because
    conversions haven't had time to land yet -- that's expected, not a bug;
    the "same_day"/"within_N_days" milestones exist precisely to make that
    judgable (see the "note" field returned).

    Args:
        date_range: Preset literal for rolling windows (LAST_30_DAYS, THIS_MONTH,
            LAST_MONTH, ...). Used only when start_date/end_date are omitted.
        start_date: Custom-range start, "YYYY-MM-DD". Pair with end_date.
        end_date: Custom-range end, "YYYY-MM-DD". Must be paired with start_date.
        customer_id: 10-digit CLIENT account ID (not a manager/MCC account).
            Optional if GOOGLE_ADS_CUSTOMER_ID is set. Each Rentumo market is its
            OWN client account, so call this once per market account -- there is
            no cross-market country segment to filter by.
        login_customer_id: Manager (MCC) 10-digit ID for querying a client account
            under a manager. Optional; falls back to GOOGLE_ADS_LOGIN_CUSTOMER_ID.
        campaign_id: Optional -- restrict to one campaign. Omit for the whole
            account (matches "account-niveau" reporting).
        milestone_days: Optional list of day cutoffs for the cumulative "landed
            within N days" percentages. Defaults to [0, 7, 14, 21, 30], where 0
            means "same day" (the LESS_THAN_ONE_DAY bucket alone).

    Returns a dict with:
        total_conversions: grand total across every lag bucket (incl. UNKNOWN),
            for the given window and scope -- comparable to get_performance's
            "conversions" total for the same window/scope.
        same_day_pct / within_7_days_pct / within_14_days_pct / ... : cumulative
            percentage of total_conversions that had landed by that many days
            after the click, one key per entry in milestone_days.
        bucket_breakdown: the raw per-bucket conversion counts and % of total,
            in day order, for anyone who wants the full distribution instead of
            just the milestones.
    """
    date_filter = build_date_filter(date_range, start_date, end_date)

    where = [date_filter]
    if campaign_id:
        where.append(f"campaign.id = {int(campaign_id)}")
    where_clause = " AND ".join(where)

    # Account-wide by default ("account-niveau"); campaign-scoped only when asked.
    resource = "campaign" if campaign_id else "customer"

    client = get_client(login_customer_id)
    cid = resolve_customer_id(customer_id)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT segments.conversion_lag_bucket, metrics.conversions
        FROM {resource}
        WHERE {where_clause}
    """

    bucket_totals: dict[str, float] = {}
    for row in ga_service.search(customer_id=cid, query=query):
        bucket = row.segments.conversion_lag_bucket.name
        bucket_totals[bucket] = bucket_totals.get(bucket, 0.0) + row.metrics.conversions

    total = sum(bucket_totals.values())
    days = sorted(set(milestone_days)) if milestone_days else list(DEFAULT_MILESTONE_DAYS)

    milestones: dict[str, float | None] = {}
    for day in days:
        cutoff = 1 if day == 0 else day
        landed = sum(
            v
            for bucket, v in bucket_totals.items()
            if CONVERSION_LAG_BUCKET_UPPER_DAYS.get(bucket, 10**9) <= cutoff
        )
        key = "same_day_pct" if day == 0 else f"within_{day}_days_pct"
        milestones[key] = round(100 * landed / total, 1) if total else None

    breakdown = sorted(
        bucket_totals.items(),
        key=lambda kv: CONVERSION_LAG_BUCKET_UPPER_DAYS.get(kv[0], 10**9),
    )

    return {
        "customer_id": cid,
        "scope": f"campaign {campaign_id}" if campaign_id else "account",
        "total_conversions": round(total, 2),
        **milestones,
        "bucket_breakdown": [
            {
                "bucket": bucket,
                "conversions": round(v, 2),
                "pct_of_total": round(100 * v / total, 1) if total else None,
            }
            for bucket, v in breakdown
        ],
        "note": (
            "The date window filters the ad-CLICK date, not the conversion date "
            "(this is how Google Ads' own 'Days to conversion' segment works). A "
            "recent window will show low percentages simply because conversions "
            "haven't had time to land yet -- that's expected. Use the milestone "
            "closest to today's elapsed time to judge whether a week's numbers are "
            "'mature' enough to compare."
        ),
    }
