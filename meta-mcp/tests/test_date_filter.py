"""Unit tests for the shared Insights date-window builder and id helpers.

These exercise pure construction only -- no Meta credentials, network, or live
server are required. ``get_client`` is monkeypatched with a fake that records the
params it is handed.
"""

import json

import pytest

from meta_mcp.client import (
    ALLOWED_DATE_PRESETS,
    build_insights_params,
    normalize_account_id,
    act_path,
    minor_to_major,
    major_to_minor,
)
from meta_mcp.performance import get_performance


# --------------------------------------------------------------------------- #
# build_insights_params -- preset branch
# --------------------------------------------------------------------------- #
def test_default_is_last_30d():
    assert build_insights_params() == {"date_preset": "last_30d"}


def test_every_allowed_preset_passes_through():
    for preset in ALLOWED_DATE_PRESETS:
        assert build_insights_params(preset) == {"date_preset": preset}


def test_preset_is_lowercased():
    assert build_insights_params("LAST_7D") == {"date_preset": "last_7d"}


def test_unknown_preset_raises():
    with pytest.raises(ValueError) as exc:
        build_insights_params("last_45d")
    assert "last_45d" in str(exc.value)


# --------------------------------------------------------------------------- #
# build_insights_params -- custom time_range branch
# --------------------------------------------------------------------------- #
def test_explicit_dates_build_time_range():
    out = build_insights_params(start_date="2026-03-01", end_date="2026-03-31")
    assert json.loads(out["time_range"]) == {"since": "2026-03-01", "until": "2026-03-31"}


def test_single_day_range_is_allowed():
    out = build_insights_params(start_date="2026-03-01", end_date="2026-03-01")
    assert json.loads(out["time_range"]) == {"since": "2026-03-01", "until": "2026-03-01"}


def test_explicit_dates_take_precedence_over_preset():
    out = build_insights_params("last_7d", start_date="2026-01-01", end_date="2026-01-31")
    assert "time_range" in out and "date_preset" not in out


# --------------------------------------------------------------------------- #
# build_insights_params -- validation errors
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bad",
    ["2026-3-1", "03-01-2026", "2026/03/01", "20260301", "March", "2026-03-01T00:00"],
)
def test_bad_format_raises(bad):
    with pytest.raises(ValueError):
        build_insights_params(start_date=bad, end_date="2026-03-31")


def test_impossible_date_raises():
    with pytest.raises(ValueError):
        build_insights_params(start_date="2026-02-31", end_date="2026-03-31")


def test_reversed_range_raises():
    with pytest.raises(ValueError) as exc:
        build_insights_params(start_date="2026-03-31", end_date="2026-03-01")
    assert "before" in str(exc.value).lower()


def test_only_start_date_raises():
    with pytest.raises(ValueError):
        build_insights_params(start_date="2026-03-01")


def test_only_end_date_raises():
    with pytest.raises(ValueError):
        build_insights_params(end_date="2026-03-31")


def test_injection_attempt_is_rejected():
    with pytest.raises(ValueError):
        build_insights_params(start_date="2026-03-01\"}', drop", end_date="2026-03-31")


# --------------------------------------------------------------------------- #
# id + money helpers
# --------------------------------------------------------------------------- #
def test_normalize_account_id_strips_prefix_and_separators():
    assert normalize_account_id("act_123456") == "123456"
    assert normalize_account_id("123-456") == "123456"


def test_act_path():
    assert act_path("123456") == "act_123456"
    assert act_path("act_123456") == "act_123456"


def test_money_minor_major_roundtrip():
    assert minor_to_major("50000") == 500.0
    assert major_to_minor(500) == 50000


# --------------------------------------------------------------------------- #
# Tool-level: confirm the Insights request params are assembled correctly
# --------------------------------------------------------------------------- #
class _FakeClient:
    def __init__(self, sink):
        self._sink = sink

    def get_all(self, path, params=None, max_pages=25):
        self._sink["path"] = path
        self._sink["params"] = params
        return []  # no rows -> tool returns []


@pytest.fixture
def captured(monkeypatch):
    sink = {}
    monkeypatch.setattr("meta_mcp.performance.get_client", lambda: _FakeClient(sink))
    return sink


def test_get_performance_default_params(captured):
    out = get_performance(account_id="act_123456")
    assert out == []
    assert captured["path"] == "act_123456/insights"
    assert captured["params"]["level"] == "campaign"
    assert captured["params"]["date_preset"] == "last_30d"


def test_get_performance_custom_range(captured):
    get_performance(account_id="123456", start_date="2026-03-01", end_date="2026-03-31")
    assert json.loads(captured["params"]["time_range"]) == {
        "since": "2026-03-01",
        "until": "2026-03-31",
    }
    assert "date_preset" not in captured["params"]


def test_get_performance_adset_level(captured):
    get_performance(date_preset="last_7d", level="adset", account_id="123456")
    assert captured["params"]["level"] == "adset"
    assert captured["params"]["date_preset"] == "last_7d"


def test_get_performance_invalid_level_returns_invalid():
    out = get_performance(account_id="123456", level="keyword")
    assert out["error"] == "invalid_level"


def test_get_performance_only_one_date_returns_invalid_input():
    out = get_performance(account_id="123456", start_date="2026-03-01")
    assert out["error"] == "invalid_input"
