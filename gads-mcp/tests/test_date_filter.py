"""Unit tests for the shared GAQL date-range builder and the reporting tools.

These exercise the pure query-string construction only -- no Google Ads
credentials, network, or ``google-ads`` package are required. ``get_client`` is
monkeypatched with a fake that records the GAQL it is handed.
"""

import pytest

from gads_mcp.client import ALLOWED_DATE_RANGES, build_date_filter
from gads_mcp.performance import get_performance, get_search_terms


# --------------------------------------------------------------------------- #
# build_date_filter -- literal (DURING) branch, i.e. backward compatibility
# --------------------------------------------------------------------------- #
def test_default_is_last_30_days():
    assert build_date_filter() == "segments.date DURING LAST_30_DAYS"


def test_every_allowed_literal_is_unchanged():
    for literal in ALLOWED_DATE_RANGES:
        assert build_date_filter(literal) == f"segments.date DURING {literal}"


def test_literal_is_uppercased():
    assert build_date_filter("last_7_days") == "segments.date DURING LAST_7_DAYS"


def test_unknown_literal_raises():
    with pytest.raises(ValueError) as exc:
        build_date_filter("LAST_45_DAYS")
    assert "LAST_45_DAYS" in str(exc.value)


# --------------------------------------------------------------------------- #
# build_date_filter -- custom range (BETWEEN) branch
# --------------------------------------------------------------------------- #
def test_explicit_dates_build_between():
    assert (
        build_date_filter(start_date="2026-03-01", end_date="2026-03-31")
        == "segments.date BETWEEN '2026-03-01' AND '2026-03-31'"
    )


def test_single_day_range_is_allowed():
    assert (
        build_date_filter(start_date="2026-03-01", end_date="2026-03-01")
        == "segments.date BETWEEN '2026-03-01' AND '2026-03-01'"
    )


def test_explicit_dates_take_precedence_over_literal():
    # A non-default literal AND explicit dates -> explicit dates win, literal ignored.
    assert (
        build_date_filter("LAST_7_DAYS", start_date="2026-01-01", end_date="2026-01-31")
        == "segments.date BETWEEN '2026-01-01' AND '2026-01-31'"
    )


# --------------------------------------------------------------------------- #
# build_date_filter -- validation errors
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bad",
    ["2026-3-1", "03-01-2026", "2026/03/01", "20260301", "March", "2026-03-01T00:00"],
)
def test_bad_format_raises(bad):
    with pytest.raises(ValueError):
        build_date_filter(start_date=bad, end_date="2026-03-31")


def test_impossible_date_raises():
    with pytest.raises(ValueError):
        build_date_filter(start_date="2026-02-31", end_date="2026-03-31")


def test_reversed_range_raises():
    with pytest.raises(ValueError) as exc:
        build_date_filter(start_date="2026-03-31", end_date="2026-03-01")
    assert "before" in str(exc.value).lower()


def test_only_start_date_raises():
    with pytest.raises(ValueError):
        build_date_filter(start_date="2026-03-01")


def test_only_end_date_raises():
    with pytest.raises(ValueError):
        build_date_filter(end_date="2026-03-31")


def test_injection_attempt_is_rejected():
    # A classic GAQL/SQL injection payload must never reach the query string.
    with pytest.raises(ValueError):
        build_date_filter(start_date="2026-03-01' OR '1'='1", end_date="2026-03-31")


# --------------------------------------------------------------------------- #
# Tool-level: confirm the full GAQL WHERE clause is assembled correctly
# --------------------------------------------------------------------------- #
class _FakeGaService:
    def __init__(self, sink):
        self._sink = sink

    def search(self, customer_id, query):
        self._sink["customer_id"] = customer_id
        self._sink["query"] = query
        return iter([])  # no rows -> tools return []


class _FakeClient:
    def __init__(self, sink):
        self._sink = sink

    def get_service(self, name):
        return _FakeGaService(self._sink)


@pytest.fixture
def captured(monkeypatch):
    """Patch get_client in performance.py with a fake that records the GAQL."""
    sink = {}
    monkeypatch.setattr(
        "gads_mcp.performance.get_client", lambda *a, **k: _FakeClient(sink)
    )
    return sink


def test_get_performance_default_gaql_unchanged(captured):
    out = get_performance(customer_id="123-456-7890")
    assert out == []
    assert "WHERE segments.date DURING LAST_30_DAYS" in captured["query"]
    assert "FROM campaign" in captured["query"]
    assert captured["customer_id"] == "1234567890"  # dashes stripped


def test_get_performance_custom_range_gaql(captured):
    get_performance(customer_id="1234567890", start_date="2026-03-01", end_date="2026-03-31")
    assert "WHERE segments.date BETWEEN '2026-03-01' AND '2026-03-31'" in captured["query"]


def test_get_performance_ad_group_level_uses_filter(captured):
    get_performance(date_range="LAST_7_DAYS", level="ad_group", customer_id="1234567890")
    assert "FROM ad_group" in captured["query"]
    assert "WHERE segments.date DURING LAST_7_DAYS" in captured["query"]


def test_get_search_terms_custom_range_with_campaign(captured):
    get_search_terms(
        customer_id="1234567890",
        campaign_id="999",
        start_date="2026-03-01",
        end_date="2026-03-31",
    )
    query = captured["query"]
    assert "segments.date BETWEEN '2026-03-01' AND '2026-03-31'" in query
    assert "campaign.id = 999" in query


def test_get_performance_only_one_date_returns_invalid_input():
    # Validation happens before get_client(), so no fake client is needed here;
    # handle_errors turns the ValueError into a readable dict.
    out = get_performance(customer_id="1234567890", start_date="2026-03-01")
    assert out["error"] == "invalid_input"
