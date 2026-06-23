"""Unit tests for the Meta Insights time-range builder and get_performance.

The build_time_params tests are pure -- no facebook-business package, network,
or credentials. The get_performance test uses a fake AdAccount that records the
params it is handed; it is skipped where facebook-business isn't installed.
"""

import pytest

from meta_ads_mcp.client import ALLOWED_DATE_PRESETS, build_time_params


# --------------------------------------------------------------------------- #
# build_time_params -- preset (date_preset) branch
# --------------------------------------------------------------------------- #
def test_default_is_last_30d():
    assert build_time_params() == {"date_preset": "last_30d"}


def test_every_allowed_preset_is_accepted():
    for preset in ALLOWED_DATE_PRESETS:
        assert build_time_params(preset) == {"date_preset": preset}


def test_preset_is_lowercased():
    assert build_time_params("LAST_7D") == {"date_preset": "last_7d"}


def test_unknown_preset_raises():
    with pytest.raises(ValueError) as exc:
        build_time_params("last_45d")
    assert "last_45d" in str(exc.value)


# --------------------------------------------------------------------------- #
# build_time_params -- custom range (time_range) branch
# --------------------------------------------------------------------------- #
def test_explicit_dates_build_time_range():
    assert build_time_params(start_date="2026-03-01", end_date="2026-03-31") == {
        "time_range": {"since": "2026-03-01", "until": "2026-03-31"}
    }


def test_single_day_range_is_allowed():
    assert build_time_params(start_date="2026-03-01", end_date="2026-03-01") == {
        "time_range": {"since": "2026-03-01", "until": "2026-03-01"}
    }


def test_explicit_dates_take_precedence_over_preset():
    assert build_time_params(
        "last_7d", start_date="2026-01-01", end_date="2026-01-31"
    ) == {"time_range": {"since": "2026-01-01", "until": "2026-01-31"}}


# --------------------------------------------------------------------------- #
# build_time_params -- validation errors
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bad",
    ["2026-3-1", "03-01-2026", "2026/03/01", "20260301", "March", "2026-03-01T00:00"],
)
def test_bad_format_raises(bad):
    with pytest.raises(ValueError):
        build_time_params(start_date=bad, end_date="2026-03-31")


def test_impossible_date_raises():
    with pytest.raises(ValueError):
        build_time_params(start_date="2026-02-31", end_date="2026-03-31")


def test_reversed_range_raises():
    with pytest.raises(ValueError) as exc:
        build_time_params(start_date="2026-03-31", end_date="2026-03-01")
    assert "before" in str(exc.value).lower()


def test_only_start_date_raises():
    with pytest.raises(ValueError):
        build_time_params(start_date="2026-03-01")


def test_only_end_date_raises():
    with pytest.raises(ValueError):
        build_time_params(end_date="2026-03-31")


def test_injection_attempt_is_rejected():
    with pytest.raises(ValueError):
        build_time_params(start_date="2026-03-01' OR '1'='1", end_date="2026-03-31")


# --------------------------------------------------------------------------- #
# account-id normalization
# --------------------------------------------------------------------------- #
def test_account_id_normalization():
    from meta_ads_mcp.client import normalize_account_id

    assert normalize_account_id("123456") == "act_123456"
    assert normalize_account_id("act_123456") == "act_123456"
    assert normalize_account_id("act_123-456") == "act_123456"


def test_money_round_trip():
    from meta_ads_mcp.client import minor_to_units, units_to_minor

    assert minor_to_units("50000") == 500.0
    assert minor_to_units(None) is None
    assert units_to_minor(500) == 50000
    assert units_to_minor(12.34) == 1234


# --------------------------------------------------------------------------- #
# get_performance -- confirm the Insights params/fields are assembled correctly.
# Skipped where facebook-business isn't installed (the import is lazy).
# --------------------------------------------------------------------------- #
@pytest.fixture
def fake_account(monkeypatch):
    pytest.importorskip("facebook_business")

    class _FakeAccount:
        last: dict = {}

        def __init__(self, acct_id, api=None):
            _FakeAccount.last["acct_id"] = acct_id
            _FakeAccount.last["api"] = api

        def get_insights(self, fields=None, params=None):
            _FakeAccount.last["fields"] = fields
            _FakeAccount.last["params"] = params
            return iter([])  # no rows -> tool returns []

    monkeypatch.setattr(
        "facebook_business.adobjects.adaccount.AdAccount", _FakeAccount
    )
    monkeypatch.setattr("meta_ads_mcp.insights.get_api", lambda: object())
    return _FakeAccount


def test_get_performance_default_params(fake_account):
    from meta_ads_mcp.insights import get_performance

    out = get_performance(account_id="act_123")
    assert out == []
    assert fake_account.last["acct_id"] == "act_123"
    assert fake_account.last["params"]["level"] == "campaign"
    assert fake_account.last["params"]["date_preset"] == "last_30d"
    assert "campaign_id" in fake_account.last["fields"]
    assert "spend" in fake_account.last["fields"]


def test_get_performance_custom_range_and_level(fake_account):
    from meta_ads_mcp.insights import get_performance

    get_performance(
        account_id="123", level="ad", start_date="2026-03-01", end_date="2026-03-31"
    )
    assert fake_account.last["acct_id"] == "act_123"  # normalized
    assert fake_account.last["params"]["level"] == "ad"
    assert fake_account.last["params"]["time_range"] == {
        "since": "2026-03-01",
        "until": "2026-03-31",
    }
    assert "ad_id" in fake_account.last["fields"]


def test_get_performance_only_one_date_returns_invalid_input():
    # Validation happens before any SDK import; handle_errors -> readable dict.
    from meta_ads_mcp.insights import get_performance

    out = get_performance(account_id="123", start_date="2026-03-01")
    assert out["error"] == "invalid_input"


def test_get_performance_bad_level_returns_error(fake_account):
    from meta_ads_mcp.insights import get_performance

    out = get_performance(account_id="123", level="keyword")
    assert out["error"] == "invalid_level"
