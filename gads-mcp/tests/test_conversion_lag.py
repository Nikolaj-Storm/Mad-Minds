"""Unit tests for get_conversion_lag -- the "Days to conversion" report.

No Google Ads credentials, network, or the ``google-ads`` package are required:
get_client is monkeypatched with a fake that records the GAQL it is handed and
serves canned segments.conversion_lag_bucket / metrics.conversions rows.
"""

import pytest

from gads_mcp.performance import get_conversion_lag


# --------------------------------------------------------------------------- #
# Fakes -- shaped like the bits of a real google-ads row this tool reads.
# --------------------------------------------------------------------------- #
class _FakeLagBucket:
    def __init__(self, name):
        self.name = name


class _FakeSegments:
    def __init__(self, bucket_name):
        self.conversion_lag_bucket = _FakeLagBucket(bucket_name)


class _FakeMetrics:
    def __init__(self, conversions):
        self.conversions = conversions


class _FakeLagRow:
    def __init__(self, bucket_name, conversions):
        self.segments = _FakeSegments(bucket_name)
        self.metrics = _FakeMetrics(conversions)


class _FakeGaService:
    def __init__(self, sink, rows):
        self._sink = sink
        self._rows = rows

    def search(self, customer_id, query):
        self._sink["customer_id"] = customer_id
        self._sink["query"] = query
        return iter(self._rows)


class _FakeClient:
    def __init__(self, sink, rows):
        self._sink = sink
        self._rows = rows

    def get_service(self, name):
        return _FakeGaService(self._sink, self._rows)


@pytest.fixture
def make_captured(monkeypatch):
    """Patch get_client in performance.py to serve the given canned rows."""

    def _install(rows):
        sink = {}
        monkeypatch.setattr(
            "gads_mcp.performance.get_client", lambda *a, **k: _FakeClient(sink, rows)
        )
        return sink

    return _install


# A distribution that mirrors the UK row from the "Days to Conversion" chart
# closely enough to sanity-check the milestone math: 85% same day, 93% <=7d,
# 96% <=14d, 98% <=21d, 100% <=30d, out of 100 conversions total.
_UK_LIKE_ROWS = [
    _FakeLagRow("LESS_THAN_ONE_DAY", 85.0),
    _FakeLagRow("SIX_TO_SEVEN_DAYS", 8.0),  # 85 + 8 = 93 by day 7
    _FakeLagRow("THIRTEEN_TO_FOURTEEN_DAYS", 3.0),  # 93 + 3 = 96 by day 14
    _FakeLagRow("FOURTEEN_TO_TWENTY_ONE_DAYS", 2.0),  # 96 + 2 = 98 by day 21
    _FakeLagRow("TWENTY_ONE_TO_THIRTY_DAYS", 2.0),  # 98 + 2 = 100 by day 30
]


# --------------------------------------------------------------------------- #
# GAQL construction
# --------------------------------------------------------------------------- #
def test_default_scope_queries_customer_resource(make_captured):
    sink = make_captured([])
    get_conversion_lag(customer_id="1234567890")
    assert "FROM customer" in sink["query"]
    assert "segments.conversion_lag_bucket" in sink["query"]
    assert "metrics.conversions" in sink["query"]
    assert "WHERE segments.date DURING LAST_30_DAYS" in sink["query"]
    assert sink["customer_id"] == "1234567890"


def test_campaign_id_scopes_to_campaign_resource(make_captured):
    sink = make_captured([])
    get_conversion_lag(customer_id="1234567890", campaign_id="999")
    assert "FROM campaign" in sink["query"]
    assert "campaign.id = 999" in sink["query"]


def test_custom_date_range_builds_between(make_captured):
    sink = make_captured([])
    get_conversion_lag(
        customer_id="1234567890", start_date="2026-03-01", end_date="2026-05-31"
    )
    assert "segments.date BETWEEN '2026-03-01' AND '2026-05-31'" in sink["query"]


# --------------------------------------------------------------------------- #
# Cumulative milestone math
# --------------------------------------------------------------------------- #
def test_milestones_match_uk_like_distribution(make_captured):
    make_captured(_UK_LIKE_ROWS)
    out = get_conversion_lag(customer_id="1234567890")

    assert out["total_conversions"] == 100.0
    assert out["same_day_pct"] == 85.0
    assert out["within_7_days_pct"] == 93.0
    assert out["within_14_days_pct"] == 96.0
    assert out["within_21_days_pct"] == 98.0
    assert out["within_30_days_pct"] == 100.0


def test_bucket_breakdown_is_sorted_by_day_and_sums_to_total(make_captured):
    make_captured(_UK_LIKE_ROWS)
    out = get_conversion_lag(customer_id="1234567890")

    buckets = out["bucket_breakdown"]
    assert [b["bucket"] for b in buckets] == [
        "LESS_THAN_ONE_DAY",
        "SIX_TO_SEVEN_DAYS",
        "THIRTEEN_TO_FOURTEEN_DAYS",
        "FOURTEEN_TO_TWENTY_ONE_DAYS",
        "TWENTY_ONE_TO_THIRTY_DAYS",
    ]
    assert sum(b["conversions"] for b in buckets) == out["total_conversions"]


def test_custom_milestone_days(make_captured):
    make_captured(_UK_LIKE_ROWS)
    out = get_conversion_lag(customer_id="1234567890", milestone_days=[0, 14])

    assert set(k for k in out if k.endswith("_pct")) == {"same_day_pct", "within_14_days_pct"}
    assert out["same_day_pct"] == 85.0
    assert out["within_14_days_pct"] == 96.0


def test_unknown_bucket_counts_toward_total_but_not_milestones(make_captured):
    rows = [
        _FakeLagRow("LESS_THAN_ONE_DAY", 10.0),
        _FakeLagRow("UNKNOWN", 5.0),
    ]
    make_captured(rows)
    out = get_conversion_lag(customer_id="1234567890", milestone_days=[0])

    assert out["total_conversions"] == 15.0
    # Only the 10 same-day conversions count toward the milestone; UNKNOWN has
    # no day bound and is excluded from the numerator but not the denominator.
    assert out["same_day_pct"] == round(100 * 10 / 15, 1)


def test_no_conversions_returns_none_percentages(make_captured):
    make_captured([])
    out = get_conversion_lag(customer_id="1234567890")

    assert out["total_conversions"] == 0
    assert out["same_day_pct"] is None
    assert out["within_30_days_pct"] is None
    assert out["bucket_breakdown"] == []


def test_scope_field_reflects_campaign_vs_account(make_captured):
    make_captured([])
    account_out = get_conversion_lag(customer_id="1234567890")
    campaign_out = get_conversion_lag(customer_id="1234567890", campaign_id="42")

    assert account_out["scope"] == "account"
    assert campaign_out["scope"] == "campaign 42"
