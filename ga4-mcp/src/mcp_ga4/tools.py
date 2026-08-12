"""Google Analytics (GA4) MCP tools — read-only reporting via per-user OAuth.

Mirrors the gsc-mcp pattern: async tools, FastMCP Context for logging, and the
signed-in marketer's token from ``get_access_token()``. GA4 is reporting-only, so
every tool here reads — there are no write/mutate tools.

Dates are GA4-native: a strict ISO ``YYYY-MM-DD`` or a relative token (``today``,
``yesterday``, ``NdaysAgo`` e.g. ``28daysAgo``). Dates resolve in the property's
reporting time zone.
"""
from typing import Any, Optional

from fastmcp import Context
from fastmcp.server.dependencies import get_access_token

from .service import ga4_data_client, ga4_admin_client
from .utils import (
    normalize_property_id, validate_ga4_date, validate_names, coerce,
    format_error_message,
)

# A safe default engagement/traffic metric set that exists on every GA4 property.
_TRAFFIC_METRICS = [
    "sessions", "totalUsers", "newUsers", "engagedSessions",
    "engagementRate", "averageSessionDuration", "screenPageViews",
]


def _token() -> str:
    return get_access_token().token


def _run_report(access_token, property_id, dimensions, metrics, start_date, end_date,
                limit, order_metric=None):
    """Run a GA4 report and return clean rows. Shared by the curated tools."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    pid = normalize_property_id(property_id)
    if not pid:
        raise ValueError("property_id is required (numeric GA4 property ID; see list_properties).")
    start = validate_ga4_date(start_date, "start_date")
    end = validate_ga4_date(end_date, "end_date")
    dims = validate_names(dimensions, "dimensions") if dimensions else []
    mets = validate_names(metrics, "metrics")

    kwargs = dict(
        property=f"properties/{pid}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name=d) for d in dims],
        metrics=[Metric(name=m) for m in mets],
        limit=int(limit),
    )
    if order_metric and order_metric in mets:
        kwargs["order_bys"] = [
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_metric), desc=True)
        ]

    resp = ga4_data_client(access_token).run_report(RunReportRequest(**kwargs))
    dim_names = [h.name for h in resp.dimension_headers]
    met_names = [h.name for h in resp.metric_headers]
    rows = []
    for r in resp.rows:
        row = {dim_names[i]: v.value for i, v in enumerate(r.dimension_values)}
        row.update({met_names[i]: coerce(v.value) for i, v in enumerate(r.metric_values)})
        rows.append(row)
    return {
        "property_id": pid,
        "date_range": {"start": start, "end": end},
        "dimensions": dim_names,
        "metrics": met_names,
        "row_count": getattr(resp, "row_count", len(rows)),
        "rows": rows,
    }


async def list_properties(ctx: Optional[Context] = None) -> dict[str, Any]:
    """List every GA4 property your Google account can read.

    Returns each property's numeric ``property_id`` (pass it to the other tools),
    display name and parent account.
    """
    try:
        if ctx:
            await ctx.info("Listing GA4 properties")
        client = ga4_admin_client(_token())
        properties, accounts = [], []
        for summary in client.list_account_summaries():
            accounts.append({"account": summary.account, "account_name": summary.display_name})
            for ps in summary.property_summaries:
                properties.append({
                    "property_id": ps.property.split("/")[-1],
                    "display_name": ps.display_name,
                    "property_type": getattr(ps, "property_type", None).name
                    if getattr(ps, "property_type", None) else None,
                    "account": summary.account,
                    "account_name": summary.display_name,
                })
        if ctx:
            await ctx.info(f"Found {len(properties)} properties")
        return {"properties": properties, "accounts": accounts, "total": len(properties)}
    except Exception as e:
        msg = format_error_message(e)
        if ctx:
            await ctx.error(msg)
        raise Exception(msg)


async def get_traffic(
    property_id: str,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    dimension: str = "sessionDefaultChannelGroup",
    limit: int = 100,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """Traffic & engagement broken down by a dimension (default: channel group).

    Returns sessions, users, new users, engaged sessions, engagement rate, average
    session duration and pageviews per ``dimension`` value.

    Args:
        property_id: Numeric GA4 property ID (see list_properties).
        start_date / end_date: ISO YYYY-MM-DD or a relative token (e.g. '28daysAgo',
            'today'). Default last 28 days.
        dimension: How to break traffic down — 'sessionDefaultChannelGroup' (default),
            'sessionSource', 'sessionMedium', 'sessionSourceMedium', 'sessionCampaignName',
            'country', 'deviceCategory', or 'date' (daily time series).
        limit: Max rows (default 100).
    """
    try:
        if ctx:
            await ctx.info(f"GA4 traffic for {property_id} by {dimension} ({start_date}..{end_date})")
        return _run_report(_token(), property_id, [dimension], _TRAFFIC_METRICS,
                           start_date, end_date, limit, order_metric="sessions")
    except Exception as e:
        msg = format_error_message(e)
        if ctx:
            await ctx.error(msg)
        raise Exception(msg)


async def get_top_pages(
    property_id: str,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 50,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """Most-viewed pages (by pageviews), with users and total engagement time.

    Args:
        property_id: Numeric GA4 property ID (see list_properties).
        start_date / end_date: ISO YYYY-MM-DD or a relative token. Default last 28 days.
        limit: Max pages to return (default 50).
    """
    try:
        if ctx:
            await ctx.info(f"GA4 top pages for {property_id} ({start_date}..{end_date})")
        return _run_report(_token(), property_id, ["pagePath", "pageTitle"],
                           ["screenPageViews", "totalUsers", "userEngagementDuration"],
                           start_date, end_date, limit, order_metric="screenPageViews")
    except Exception as e:
        msg = format_error_message(e)
        if ctx:
            await ctx.error(msg)
        raise Exception(msg)


async def get_conversions(
    property_id: str,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 100,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """Key events / conversions by event name, with event count and revenue.

    Args:
        property_id: Numeric GA4 property ID (see list_properties).
        start_date / end_date: ISO YYYY-MM-DD or a relative token. Default last 28 days.
        limit: Max event rows (default 100).
    """
    try:
        if ctx:
            await ctx.info(f"GA4 conversions for {property_id} ({start_date}..{end_date})")
        return _run_report(_token(), property_id, ["eventName"],
                           ["keyEvents", "eventCount", "totalRevenue"],
                           start_date, end_date, limit, order_metric="keyEvents")
    except Exception as e:
        msg = format_error_message(e)
        if ctx:
            await ctx.error(msg)
        raise Exception(msg)


async def get_report(
    property_id: str,
    dimensions: Optional[list] = None,
    metrics: Optional[list] = None,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 100,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """Run an arbitrary GA4 report (escape hatch for any dimension/metric combo).

    Args:
        property_id: Numeric GA4 property ID (see list_properties).
        dimensions: GA4 dimension API names, e.g. ['date','sessionDefaultChannelGroup'].
            Default ['date'].
        metrics: GA4 metric API names, e.g. ['sessions','conversions']. Default ['sessions'].
        start_date / end_date: ISO YYYY-MM-DD or a relative token. Default last 28 days.
        limit: Max rows (default 100).
    """
    try:
        if ctx:
            await ctx.info(f"GA4 report for {property_id} ({start_date}..{end_date})")
        return _run_report(_token(), property_id, dimensions or ["date"],
                           metrics or ["sessions"], start_date, end_date, limit)
    except Exception as e:
        msg = format_error_message(e)
        if ctx:
            await ctx.error(msg)
        raise Exception(msg)


async def get_realtime(
    property_id: str,
    dimensions: Optional[list] = None,
    metrics: Optional[list] = None,
    limit: int = 100,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """Realtime report — activity in roughly the last 30 minutes.

    Args:
        property_id: Numeric GA4 property ID (see list_properties).
        dimensions: Realtime dimension API names, e.g. ['unifiedScreenName'], ['country'],
            ['deviceCategory']. Default ['unifiedScreenName'].
        metrics: Realtime metric API names. Default ['activeUsers'].
        limit: Max rows (default 100).
    """
    try:
        if ctx:
            await ctx.info(f"GA4 realtime for {property_id}")
        from google.analytics.data_v1beta.types import (
            Dimension, Metric, RunRealtimeReportRequest,
        )
        pid = normalize_property_id(property_id)
        if not pid:
            raise ValueError("property_id is required (numeric GA4 property ID; see list_properties).")
        dims = validate_names(dimensions or ["unifiedScreenName"], "dimensions")
        mets = validate_names(metrics or ["activeUsers"], "metrics")
        req = RunRealtimeReportRequest(
            property=f"properties/{pid}",
            dimensions=[Dimension(name=d) for d in dims],
            metrics=[Metric(name=m) for m in mets],
            limit=int(limit),
        )
        resp = ga4_data_client(_token()).run_realtime_report(req)
        dim_names = [h.name for h in resp.dimension_headers]
        met_names = [h.name for h in resp.metric_headers]
        rows = []
        for r in resp.rows:
            row = {dim_names[i]: v.value for i, v in enumerate(r.dimension_values)}
            row.update({met_names[i]: coerce(v.value) for i, v in enumerate(r.metric_values)})
            rows.append(row)
        return {"property_id": pid, "dimensions": dim_names, "metrics": met_names, "rows": rows}
    except Exception as e:
        msg = format_error_message(e)
        if ctx:
            await ctx.error(msg)
        raise Exception(msg)
