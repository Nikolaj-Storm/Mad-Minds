"""Reporting tools: get_performance and get_search_terms."""

from .client import get_client, resolve_customer_id, handle_errors, build_date_filter

ALLOWED_LEVELS = {"campaign", "ad_group", "ad"}

# geographic_view.location_type values we let a caller ask for. LOCATION_OF_PRESENCE
# is where the user physically was; AREA_OF_INTEREST is what they searched about.
# For a spend-by-country report you want presence only, or you double-count.
ALLOWED_LOCATION_TYPES = {"LOCATION_OF_PRESENCE", "AREA_OF_INTEREST"}

# Which resource to segment by country. "auto" picks the one that best reconciles
# to the campaign-level spend (see get_geo_performance); the others force it.
ALLOWED_GEO_SOURCES = {"auto", "geographic_view", "user_location_view"}

# In "auto" mode, when geographic_view accounts for at least this share of the
# campaign-level spend we trust it. Below this, some campaigns didn't report geo
# rows — the classic Performance Max gap, which also shows up for a MIX of
# campaign types (e.g. Search reports fine but PMax doesn't) — so we reconcile
# against user_location_view, which covers every campaign type.
_GEO_RECONCILE_MIN_SHARE = 0.99


def _compute_metrics(cost_micros, impressions, clicks, conversions, conv_value) -> dict:
    """Turn raw metric totals into clean, human-friendly numbers.

    Shared by the per-row reporting path (``_metrics_dict``) and the geo report,
    which sums several rows per country before computing the derived rates.
    """
    spend = cost_micros / 1_000_000
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


def _metrics_dict(metrics) -> dict:
    """Turn a Google Ads metrics row into clean, human-friendly numbers."""
    return _compute_metrics(
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value,
    )


# Country criterion IDs (geo-target-constant IDs) resolved to {name, ISO code}.
# geographic_view / user_location_view hand back only the numeric
# country_criterion_id (e.g. 2276), never a name, so we look each one up in the
# geo_target_constant resource. Geo-target constants never change, so we cache
# them across calls for the life of the process.
_COUNTRY_CACHE: dict[str, dict] = {}


def _resolve_countries(ga_service, cid: str, country_ids) -> dict:
    """Map each country_criterion_id -> {"country": name, "country_code": ISO}.

    Batches one geo_target_constant lookup for the IDs not already cached. IDs
    come straight from the API (ints), and we coerce with ``int()`` before they
    touch the query, so there's no injection surface.
    """
    missing = [c for c in country_ids if c and c not in _COUNTRY_CACHE]
    if missing:
        resource_names = ", ".join(
            f"'geoTargetConstants/{int(c)}'" for c in dict.fromkeys(missing)
        )
        query = f"""
            SELECT geo_target_constant.id,
                   geo_target_constant.name,
                   geo_target_constant.country_code
            FROM geo_target_constant
            WHERE geo_target_constant.resource_name IN ({resource_names})
        """
        for row in ga_service.search(customer_id=cid, query=query):
            gt = row.geo_target_constant
            _COUNTRY_CACHE[str(gt.id)] = {
                "country": gt.name or None,
                "country_code": gt.country_code or None,
            }
    return {
        c: _COUNTRY_CACHE.get(c, {"country": None, "country_code": None})
        for c in country_ids
    }


def _aggregate_geo(ga_service, cid: str, query: str, country_id_of) -> dict:
    """Run a geo GAQL query and sum the raw metrics per country_criterion_id.

    ``country_id_of`` pulls the numeric country id off a row — it differs between
    geographic_view and user_location_view, which is the only shape difference
    between the primary query and the fallback.
    """
    totals: dict[str, dict] = {}
    for row in ga_service.search(customer_id=cid, query=query):
        country_id = str(country_id_of(row))
        m = row.metrics
        acc = totals.setdefault(
            country_id,
            {
                "cost_micros": 0,
                "impressions": 0,
                "clicks": 0,
                "conversions": 0.0,
                "conversions_value": 0.0,
            },
        )
        acc["cost_micros"] += m.cost_micros
        acc["impressions"] += m.impressions
        acc["clicks"] += m.clicks
        acc["conversions"] += m.conversions
        acc["conversions_value"] += m.conversions_value
    return totals


def _expected_cost_micros(ga_service, cid: str, date_filter: str, campaign_filter: str) -> int:
    """Campaign-level spend (in micros) for the same window/campaign filter.

    Used as the reconciliation yardstick: it's the total the per-country split
    should add up to, so "auto" mode can tell when geographic_view is missing a
    chunk of spend (e.g. a PMax or other campaign that didn't report geo rows).
    """
    query = f"""
        SELECT campaign.id, metrics.cost_micros
        FROM campaign
        WHERE {date_filter}{campaign_filter}
    """
    return sum(row.metrics.cost_micros for row in ga_service.search(customer_id=cid, query=query))


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
def get_geo_performance(
    date_range: str = "LAST_30_DAYS",
    campaign_id: str | None = None,
    location_type: str = "LOCATION_OF_PRESENCE",
    source: str = "auto",
    customer_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    login_customer_id: str | None = None,
) -> list | dict:
    """Get Google Ads performance (spend, impressions, clicks, conversions, ROAS) split BY COUNTRY.

    Segments metrics across the countries a campaign targets — the one thing
    get_performance can't do. Works for ANY campaign type that splits spend
    between countries: Performance Max, Search, Shopping, Demand Gen, Display,
    Video. Pass a campaign_id to break down a single campaign, or omit it to
    break the whole account down by country.

    Countries come back as readable names + ISO codes, not the numeric geo IDs the
    API returns. Rows are aggregated per country and sorted by spend (highest
    first); each row's per-country spend sums to the campaign/account total you'd
    see in get_performance for the same window (allow minor rounding).

    Works for ANY time period, exactly like get_performance: pass start_date +
    end_date (YYYY-MM-DD) for an explicit custom range — a specific month, quarter,
    or anything older than 30 days — or a date_range preset for common rolling
    windows. Explicit dates win when both are given.

    Data source (see the `source` arg): "auto" starts from geographic_view, then
    checks the country split against the campaign-level spend. Performance Max —
    and any other campaign type — can under-report to geographic_view, so when the
    split doesn't account for the full spend, it reconciles against
    user_location_view (physical-presence only, covers every campaign type) and
    keeps whichever resource reconciles best. This is what makes a MIXED account
    (e.g. Search + PMax) add up correctly, not just an all-PMax campaign. Each
    row's "source" field records which resource it came from.

    Args:
        date_range: Preset literal for rolling windows — TODAY, YESTERDAY, LAST_7_DAYS,
            LAST_14_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH (and a few other Google
            literals). Used only when start_date/end_date are omitted. Default LAST_30_DAYS.
        campaign_id: Optional — restrict the report to ONE campaign (e.g. a single
            PMax campaign). Omit to break the whole account down by country.
        location_type: Which geographic_view rows to count — "LOCATION_OF_PRESENCE"
            (where the user physically was; the default, and what you want for a
            spend-by-country report) or "AREA_OF_INTEREST" (what they searched
            about). Counting both double-counts spend, so this picks exactly one.
            user_location_view is presence-only, so AREA_OF_INTEREST always uses
            geographic_view.
        source: Which resource to segment by — "auto" (default; reconcile
            geographic_view against the campaign total and fall back to
            user_location_view when it under-reports), "geographic_view" (force it,
            no fallback), or "user_location_view" (force presence-only geo, the
            most reliable single source for Performance Max). Use a forced source
            to compare or when you already know which one an account reports to.
        start_date: Custom-range start, "YYYY-MM-DD". Pair with end_date. Takes precedence
            over date_range when both ends are given. Ranges older than 30 days are fine.
        end_date: Custom-range end, "YYYY-MM-DD". Must be paired with start_date.
            Dates use the account's reporting time zone (no conversion).
        customer_id: 10-digit account ID — a CLIENT account, not a manager/MCC account
            (managers have no metrics). Optional if GOOGLE_ADS_CUSTOMER_ID is set.
        login_customer_id: Manager (MCC) 10-digit ID to send as login-customer-id, for
            querying client accounts under a manager. Optional; falls back to the
            GOOGLE_ADS_LOGIN_CUSTOMER_ID env var.
    """
    date_filter = build_date_filter(date_range, start_date, end_date)
    location_type = (location_type or "LOCATION_OF_PRESENCE").upper()
    if location_type not in ALLOWED_LOCATION_TYPES:
        return {
            "error": "invalid_location_type",
            "message": f"'{location_type}' is not supported.",
            "allowed": sorted(ALLOWED_LOCATION_TYPES),
        }
    source = (source or "auto").lower()
    if source not in ALLOWED_GEO_SOURCES:
        return {
            "error": "invalid_source",
            "message": f"'{source}' is not supported.",
            "allowed": sorted(ALLOWED_GEO_SOURCES),
        }

    client = get_client(login_customer_id)
    cid = resolve_customer_id(customer_id)
    ga_service = client.get_service("GoogleAdsService")

    metric_fields = (
        "metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "metrics.conversions, metrics.conversions_value"
    )
    campaign_filter = f" AND campaign.id = {int(campaign_id)}" if campaign_id else ""

    def run_geographic_view() -> dict:
        # Filtered to the requested location_type so presence and area-of-interest
        # rows are never summed together.
        query = f"""
            SELECT campaign.id, campaign.name,
                   geographic_view.country_criterion_id,
                   geographic_view.location_type,
                   {metric_fields}
            FROM geographic_view
            WHERE {date_filter}
              AND geographic_view.location_type = '{location_type}'{campaign_filter}
        """
        return _aggregate_geo(
            ga_service, cid, query,
            lambda row: row.geographic_view.country_criterion_id,
        )

    def run_user_location_view() -> dict:
        # Physical-presence only (no location_type segment) — the most reliable
        # single geo source for Performance Max, and it covers every campaign type.
        query = f"""
            SELECT campaign.id, campaign.name,
                   user_location_view.country_criterion_id,
                   {metric_fields}
            FROM user_location_view
            WHERE {date_filter}{campaign_filter}
        """
        return _aggregate_geo(
            ga_service, cid, query,
            lambda row: row.user_location_view.country_criterion_id,
        )

    def cost_of(totals: dict) -> int:
        return sum(acc["cost_micros"] for acc in totals.values())

    if source == "geographic_view":
        totals, used_source = run_geographic_view(), "geographic_view"
    elif source == "user_location_view":
        totals, used_source = run_user_location_view(), "user_location_view"
    elif location_type == "AREA_OF_INTEREST":
        # Only geographic_view carries area-of-interest; nothing to reconcile against.
        totals, used_source = run_geographic_view(), "geographic_view"
    else:
        # auto + LOCATION_OF_PRESENCE: trust geographic_view only if it accounts
        # for the campaign-level spend; otherwise reconcile via user_location_view.
        totals, used_source = run_geographic_view(), "geographic_view"
        expected = _expected_cost_micros(ga_service, cid, date_filter, campaign_filter)
        geo_cost = cost_of(totals)
        if expected > 0 and geo_cost < expected * _GEO_RECONCILE_MIN_SHARE:
            user_totals = run_user_location_view()
            # Keep whichever resource lands closest to the campaign-level total.
            if abs(expected - cost_of(user_totals)) <= abs(expected - geo_cost):
                totals, used_source = user_totals, "user_location_view"

    names = _resolve_countries(ga_service, cid, list(totals.keys()))

    results = []
    for country_id, acc in totals.items():
        info = names.get(country_id, {"country": None, "country_code": None})
        results.append(
            {
                "country_id": country_id,
                "country": info["country"],
                "country_code": info["country_code"],
                "location_type": location_type,
                "source": used_source,
                **_compute_metrics(
                    acc["cost_micros"],
                    acc["impressions"],
                    acc["clicks"],
                    acc["conversions"],
                    acc["conversions_value"],
                ),
            }
        )
    results.sort(key=lambda r: r["spend"], reverse=True)
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
