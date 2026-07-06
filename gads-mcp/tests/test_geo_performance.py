"""Unit tests for get_geo_performance — the per-country reporting tool.

Like test_date_filter.py these exercise pure query construction and the
aggregation/fallback logic only — no Google Ads credentials, network, or the
``google-ads`` package are required. ``get_client`` is monkeypatched with a fake
GoogleAdsService that records every GAQL query it is handed and returns canned
rows chosen by the query's FROM clause.
"""

from types import SimpleNamespace

import pytest

import gads_mcp.performance as perf
from gads_mcp.performance import get_geo_performance


def _metric_row(country_id, *, cost_micros, impressions, clicks,
                conversions=0.0, conversions_value=0.0, location_type="LOCATION_OF_PRESENCE"):
    """A geographic_view / user_location_view row. Both geo attrs are set so the
    same fixture row works whichever resource the query targets."""
    geo = SimpleNamespace(country_criterion_id=country_id, location_type=location_type)
    return SimpleNamespace(
        campaign=SimpleNamespace(id=1, name="C"),
        geographic_view=geo,
        user_location_view=geo,
        metrics=SimpleNamespace(
            cost_micros=cost_micros,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            conversions_value=conversions_value,
        ),
    )


def _country_row(id_, name, code):
    return SimpleNamespace(
        geo_target_constant=SimpleNamespace(id=id_, name=name, country_code=code)
    )


class _FakeGaService:
    def __init__(self, sink):
        self._sink = sink

    def search(self, customer_id, query):
        self._sink["customer_id"] = customer_id
        self._sink.setdefault("queries", []).append(query)
        if "FROM geographic_view" in query:
            return iter(self._sink.get("geo_rows", []))
        if "FROM user_location_view" in query:
            return iter(self._sink.get("user_loc_rows", []))
        if "FROM geo_target_constant" in query:
            return iter(self._sink.get("country_rows", []))
        return iter([])


class _FakeClient:
    def __init__(self, sink):
        self._sink = sink

    def get_service(self, name):
        return _FakeGaService(self._sink)


@pytest.fixture(autouse=True)
def _clear_country_cache():
    # The country name cache is module-level and persists across calls; reset it
    # so each test sees a deterministic geo_target_constant lookup.
    perf._COUNTRY_CACHE.clear()
    yield
    perf._COUNTRY_CACHE.clear()


@pytest.fixture
def captured(monkeypatch):
    sink = {}
    monkeypatch.setattr("gads_mcp.performance.get_client", lambda *a, **k: _FakeClient(sink))
    return sink


def _last(sink, needle):
    return next(q for q in sink["queries"] if needle in q)


# --------------------------------------------------------------------------- #
# GAQL assembly
# --------------------------------------------------------------------------- #
def test_default_geographic_view_query(captured):
    out = get_geo_performance(customer_id="123-456-7890")
    assert out == []  # no rows -> empty (both resources empty)
    geo_q = _last(captured, "FROM geographic_view")
    assert "WHERE segments.date DURING LAST_30_DAYS" in geo_q
    assert "geographic_view.location_type = 'LOCATION_OF_PRESENCE'" in geo_q
    assert "geographic_view.country_criterion_id" in geo_q
    assert captured["customer_id"] == "1234567890"  # dashes stripped


def test_custom_range_and_campaign_filter(captured):
    get_geo_performance(
        customer_id="1234567890",
        campaign_id="21782060119",
        start_date="2026-03-01",
        end_date="2026-03-31",
    )
    geo_q = _last(captured, "FROM geographic_view")
    assert "segments.date BETWEEN '2026-03-01' AND '2026-03-31'" in geo_q
    assert "campaign.id = 21782060119" in geo_q


def test_area_of_interest_filters_and_does_not_fall_back(captured):
    # AREA_OF_INTEREST is presence-agnostic, so an empty geographic_view result
    # must NOT be backfilled from user_location_view (which is presence-only).
    get_geo_performance(customer_id="1234567890", location_type="AREA_OF_INTEREST")
    geo_q = _last(captured, "FROM geographic_view")
    assert "geographic_view.location_type = 'AREA_OF_INTEREST'" in geo_q
    assert not any("FROM user_location_view" in q for q in captured["queries"])


def test_invalid_location_type_returns_error(captured):
    out = get_geo_performance(customer_id="1234567890", location_type="ON_THE_MOON")
    assert out["error"] == "invalid_location_type"
    assert "LOCATION_OF_PRESENCE" in out["allowed"]


# --------------------------------------------------------------------------- #
# Aggregation, country resolution, and output shape
# --------------------------------------------------------------------------- #
def test_aggregates_by_country_and_resolves_names(captured):
    # Two DE rows (should sum) + one DK row; sorted by spend desc.
    captured["geo_rows"] = [
        _metric_row(2276, cost_micros=6_000_000, impressions=100, clicks=10, conversions=2, conversions_value=200),
        _metric_row(2276, cost_micros=2_000_000, impressions=50, clicks=5, conversions=1, conversions_value=100),
        _metric_row(2208, cost_micros=3_000_000, impressions=30, clicks=3, conversions=0, conversions_value=0),
    ]
    captured["country_rows"] = [
        _country_row(2276, "Germany", "DE"),
        _country_row(2208, "Denmark", "DK"),
    ]
    out = get_geo_performance(customer_id="1234567890")

    assert [r["country"] for r in out] == ["Germany", "Denmark"]  # DE=8 DKK first
    de = out[0]
    assert de["country_id"] == "2276"
    assert de["country_code"] == "DE"
    assert de["source"] == "geographic_view"
    assert de["location_type"] == "LOCATION_OF_PRESENCE"
    assert de["spend"] == 8.0            # 6 + 2 micros summed then /1e6
    assert de["impressions"] == 150
    assert de["clicks"] == 15
    assert de["conversions"] == 3.0
    assert de["cpa"] == round(8.0 / 3, 2)
    assert de["roas"] == round(300 / 8.0, 2)


def test_falls_back_to_user_location_view_when_geo_empty(captured):
    captured["geo_rows"] = []  # PMax: geographic_view returns nothing
    captured["user_loc_rows"] = [
        _metric_row(2036, cost_micros=11_800_000, impressions=500, clicks=40, conversions=5, conversions_value=1500),
    ]
    captured["country_rows"] = [_country_row(2036, "Australia", "AU")]
    out = get_geo_performance(customer_id="1234567890", campaign_id="21782060119")

    assert any("FROM user_location_view" in q for q in captured["queries"])
    assert len(out) == 1
    row = out[0]
    assert row["source"] == "user_location_view"
    assert row["country"] == "Australia"
    assert row["country_code"] == "AU"
    assert row["spend"] == 11.8
    # the fallback query still carries the campaign + date filter
    user_q = _last(captured, "FROM user_location_view")
    assert "campaign.id = 21782060119" in user_q
    assert "WHERE segments.date DURING LAST_30_DAYS" in user_q


def test_unresolved_country_id_degrades_gracefully(captured):
    captured["geo_rows"] = [
        _metric_row(9999, cost_micros=1_000_000, impressions=10, clicks=1),
    ]
    captured["country_rows"] = []  # geo_target_constant returns nothing for 9999
    out = get_geo_performance(customer_id="1234567890")
    assert out[0]["country_id"] == "9999"
    assert out[0]["country"] is None
    assert out[0]["country_code"] is None
    assert out[0]["spend"] == 1.0
