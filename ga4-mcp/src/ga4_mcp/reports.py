"""GA4 reporting tools (read-only): curated reports + a generic escape hatch.

All tools accept ANY date window. Dates are GA4-native: a strict ISO ``YYYY-MM-DD``
or a relative token (``today``, ``yesterday``, ``NdaysAgo`` like ``28daysAgo``).
Dates resolve in the GA4 property's reporting time zone.
"""
from .client import (
    data_client,
    resolve_property_id,
    handle_errors,
    validate_ga4_date,
    validate_names,
    coerce,
)

# A safe default engagement/traffic metric set that exists on every GA4 property.
_TRAFFIC_METRICS = [
    "sessions",
    "totalUsers",
    "newUsers",
    "engagedSessions",
    "engagementRate",
    "averageSessionDuration",
    "screenPageViews",
]


def _run(property_id, dimensions, metrics, start_date, end_date, limit, order_metric=None):
    """Run a GA4 report and return clean rows. Shared by every curated tool."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )

    pid = resolve_property_id(property_id)
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

    resp = data_client().run_report(RunReportRequest(**kwargs))
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


@handle_errors
def get_traffic(
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    dimension: str = "sessionDefaultChannelGroup",
    limit: int = 100,
) -> dict:
    """Traffic & engagement broken down by a dimension (default: channel group).

    Returns sessions, users, new users, engaged sessions, engagement rate, average
    session duration and pageviews per ``dimension`` value.

    Args:
        property_id: Numeric GA4 property ID. Optional if GA4_PROPERTY_ID is set.
        start_date / end_date: ISO YYYY-MM-DD or a relative token (e.g. '28daysAgo',
            'today'). Default last 28 days.
        dimension: How to break traffic down. Common values:
            'sessionDefaultChannelGroup' (default), 'sessionSource', 'sessionMedium',
            'sessionSourceMedium', 'sessionCampaignName', 'country', 'deviceCategory',
            'date'. Pass 'date' for a daily time series.
        limit: Max rows (default 100).
    """
    return _run(
        property_id, [dimension], _TRAFFIC_METRICS,
        start_date, end_date, limit, order_metric="sessions",
    )


@handle_errors
def get_top_pages(
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 50,
) -> dict:
    """Most-viewed pages (by pageviews), with users and average engagement time.

    Args:
        property_id: Numeric GA4 property ID. Optional if GA4_PROPERTY_ID is set.
        start_date / end_date: ISO YYYY-MM-DD or a relative token. Default last 28 days.
        limit: Max pages to return (default 50).
    """
    return _run(
        property_id,
        ["pagePath", "pageTitle"],
        ["screenPageViews", "totalUsers", "userEngagementDuration"],
        start_date, end_date, limit, order_metric="screenPageViews",
    )


@handle_errors
def get_conversions(
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 100,
) -> dict:
    """Key events / conversions by event name, with event count and revenue.

    Args:
        property_id: Numeric GA4 property ID. Optional if GA4_PROPERTY_ID is set.
        start_date / end_date: ISO YYYY-MM-DD or a relative token. Default last 28 days.
        limit: Max event rows (default 100).
    """
    return _run(
        property_id,
        ["eventName"],
        ["keyEvents", "eventCount", "totalRevenue"],
        start_date, end_date, limit, order_metric="keyEvents",
    )


@handle_errors
def get_report(
    property_id: str | None = None,
    dimensions: list | None = None,
    metrics: list | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 100,
) -> dict:
    """Run an arbitrary GA4 report (escape hatch for any dimension/metric combo).

    Use the curated tools (get_traffic, get_top_pages, get_conversions) for common
    questions; reach for this when you need a specific combination.

    Args:
        property_id: Numeric GA4 property ID. Optional if GA4_PROPERTY_ID is set.
        dimensions: GA4 dimension API names, e.g. ['date','sessionDefaultChannelGroup'].
            Default ['date'].
        metrics: GA4 metric API names, e.g. ['sessions','conversions']. Default ['sessions'].
        start_date / end_date: ISO YYYY-MM-DD or a relative token. Default last 28 days.
        limit: Max rows (default 100).
    """
    return _run(
        property_id,
        dimensions or ["date"],
        metrics or ["sessions"],
        start_date, end_date, limit,
    )


@handle_errors
def get_realtime(
    property_id: str | None = None,
    dimensions: list | None = None,
    metrics: list | None = None,
    limit: int = 100,
) -> dict:
    """Realtime report — activity in roughly the last 30 minutes.

    Args:
        property_id: Numeric GA4 property ID. Optional if GA4_PROPERTY_ID is set.
        dimensions: Realtime dimension API names, e.g. ['unifiedScreenName'],
            ['country'], ['deviceCategory']. Default ['unifiedScreenName'].
        metrics: Realtime metric API names. Default ['activeUsers'].
        limit: Max rows (default 100).
    """
    from google.analytics.data_v1beta.types import (
        Dimension, Metric, RunRealtimeReportRequest,
    )

    pid = resolve_property_id(property_id)
    dims = validate_names(dimensions or ["unifiedScreenName"], "dimensions")
    mets = validate_names(metrics or ["activeUsers"], "metrics")
    req = RunRealtimeReportRequest(
        property=f"properties/{pid}",
        dimensions=[Dimension(name=d) for d in dims],
        metrics=[Metric(name=m) for m in mets],
        limit=int(limit),
    )
    resp = data_client().run_realtime_report(req)
    dim_names = [h.name for h in resp.dimension_headers]
    met_names = [h.name for h in resp.metric_headers]
    rows = []
    for r in resp.rows:
        row = {dim_names[i]: v.value for i, v in enumerate(r.dimension_values)}
        row.update({met_names[i]: coerce(v.value) for i, v in enumerate(r.metric_values)})
        rows.append(row)
    return {"property_id": pid, "dimensions": dim_names, "metrics": met_names, "rows": rows}
