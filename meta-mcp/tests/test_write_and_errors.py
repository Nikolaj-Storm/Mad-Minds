"""Unit tests for the write tools' READONLY simulate paths, validation, the
Graph error parser, pagination, and the campaign budget-level logic.

No network or credentials: ``get_client`` is monkeypatched with a fake recorder,
and ``httpx.get`` is monkeypatched for the pagination test.
"""

import pytest

from meta_mcp import client as client_mod
from meta_mcp.client import (
    handle_errors,
    MetaApiError,
    account_status_label,
    minor_to_major,
    major_to_minor,
)
from meta_mcp import campaigns as campaigns_mod
from meta_mcp.campaigns import (
    pause_entity,
    enable_entity,
    update_budget,
    get_campaigns,
)


# --------------------------------------------------------------------------- #
# Fake Graph client recorder
# --------------------------------------------------------------------------- #
class _Recorder:
    def __init__(self, rows=None):
        self.posts = []
        self.gets = []
        self._rows = rows or []

    def post(self, path, data=None):
        self.posts.append((path, data))
        return {"success": True}

    def get_all(self, path, params=None, max_pages=25):
        self.gets.append((path, params))
        return list(self._rows)


@pytest.fixture
def rec(monkeypatch):
    r = _Recorder()
    monkeypatch.setattr(campaigns_mod, "get_client", lambda: r)
    return r


# --------------------------------------------------------------------------- #
# READONLY simulate path — every write tool
# --------------------------------------------------------------------------- #
def test_pause_entity_readonly_simulates(monkeypatch, rec):
    monkeypatch.setenv("READONLY_MODE", "true")
    out = pause_entity("campaign", "120330000000000")
    assert out["simulated"] is True and out["readonly_mode"] is True
    assert out["action"] == "pause_entity"
    assert rec.posts == []  # nothing actually sent


def test_enable_entity_readonly_simulates(monkeypatch, rec):
    monkeypatch.setenv("READONLY_MODE", "true")
    out = enable_entity("adset", "60000000000")
    assert out["simulated"] is True
    assert rec.posts == []


def test_update_budget_readonly_simulates(monkeypatch, rec):
    monkeypatch.setenv("READONLY_MODE", "true")
    out = update_budget("120330000000000", daily_budget=500)
    assert out["simulated"] is True
    assert out["would_have_changed"]["new_daily_budget"] == 500
    assert rec.posts == []


# --------------------------------------------------------------------------- #
# Real write path — converts + posts correctly
# --------------------------------------------------------------------------- #
def test_pause_entity_real_posts_paused(monkeypatch, rec):
    monkeypatch.setenv("READONLY_MODE", "false")
    out = pause_entity("campaign", "123")
    assert out["success"] is True and out["status"] == "PAUSED"
    assert rec.posts == [("123", {"status": "PAUSED"})]


def test_enable_entity_real_posts_active(monkeypatch, rec):
    monkeypatch.setenv("READONLY_MODE", "false")
    out = enable_entity("ad", "456")
    assert out["status"] == "ACTIVE"
    assert rec.posts == [("456", {"status": "ACTIVE"})]


def test_update_budget_real_converts_to_minor_units(monkeypatch, rec):
    monkeypatch.setenv("READONLY_MODE", "false")
    out = update_budget("789", daily_budget=500, entity_type="adset")
    assert out["success"] is True and out["new_daily_budget"] == 500.0
    # 500 whole units -> 50000 minor units
    assert rec.posts == [("789", {"daily_budget": 50000})]


def test_update_budget_lifetime_path(monkeypatch, rec):
    monkeypatch.setenv("READONLY_MODE", "false")
    out = update_budget("789", lifetime_budget=1000)
    assert rec.posts == [("789", {"lifetime_budget": 100000})]
    assert out["new_lifetime_budget"] == 1000.0


# --------------------------------------------------------------------------- #
# Validation (returns readable dict, never raises)
# --------------------------------------------------------------------------- #
def test_invalid_entity_type():
    out = pause_entity("keyword", "1")
    assert out["error"] == "invalid_entity_type"
    assert "campaign" in out["allowed"]


def test_update_budget_requires_exactly_one_budget(monkeypatch):
    monkeypatch.setenv("READONLY_MODE", "true")
    both = update_budget("1", daily_budget=10, lifetime_budget=20)
    neither = update_budget("1")
    assert both["error"] == "validation"
    assert neither["error"] == "validation"


# --------------------------------------------------------------------------- #
# get_campaigns budget-level detection
# --------------------------------------------------------------------------- #
def test_get_campaigns_budget_levels(monkeypatch):
    rows = [
        {"id": "1", "name": "CBO", "status": "ACTIVE", "daily_budget": "50000"},
        {"id": "2", "name": "ABO", "status": "ACTIVE"},  # budget on ad sets
        {"id": "3", "name": "LIFE", "status": "PAUSED", "lifetime_budget": "200000"},
    ]
    monkeypatch.setattr(campaigns_mod, "get_client", lambda: _Recorder(rows))
    out = get_campaigns(account_id="act_1")
    by_id = {c["id"]: c for c in out}
    assert by_id["1"]["budget_level"] == "campaign" and by_id["1"]["daily_budget"] == 500.0
    assert by_id["2"]["budget_level"] == "adset" and by_id["2"]["daily_budget"] is None
    assert by_id["3"]["budget_level"] == "campaign" and by_id["3"]["lifetime_budget"] == 2000.0


# --------------------------------------------------------------------------- #
# Graph error parser — matches real Graph error shapes (codes verified live)
# --------------------------------------------------------------------------- #
def _raiser(error):
    @handle_errors
    def boom():
        raise MetaApiError(error)

    return boom()


def test_error_invalid_token_code_190():
    out = _raiser({"message": "Invalid OAuth access token", "code": 190, "fbtrace_id": "x"})
    assert out["error"] == "meta_api_error"
    assert out["code"] == 190
    assert out["fbtrace_id"] == "x"
    assert "reconnect" in out["hint"].lower() or "expired" in out["hint"].lower()


def test_error_no_token_code_2500_caught_by_message():
    # Real no-token response: code 2500, message contains "access token".
    out = _raiser({"message": "An active access token must be used", "code": 2500})
    assert out["hint"] is not None and "reconnect" in out["hint"].lower()


def test_error_rate_limit_code_4():
    out = _raiser({"message": "User request limit reached", "code": 4})
    assert "rate limit" in out["hint"].lower()


def test_error_permission_code_200():
    out = _raiser({"message": "Permissions error", "code": 200})
    assert "permission" in out["hint"].lower()


def test_error_unknown_code_has_no_false_hint():
    out = _raiser({"message": "Some new error", "code": 99999})
    assert out["error"] == "meta_api_error"
    assert out["hint"] is None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def test_account_status_label():
    assert account_status_label(1) == "ACTIVE"
    assert account_status_label(101) == "CLOSED"
    assert account_status_label(12345) == "12345"  # unknown passes through
    assert account_status_label(None) == "None"


def test_money_helpers():
    assert minor_to_major("50000") == 500.0
    assert minor_to_major(None) == 0.0  # defensive
    assert major_to_minor(4.5) == 450


# --------------------------------------------------------------------------- #
# GraphClient.get_all — cursor pagination follows 'next' then stops
# --------------------------------------------------------------------------- #
def test_graphclient_pagination(monkeypatch):
    pages = [
        {"data": [{"id": "1"}, {"id": "2"}], "paging": {"next": "https://next/page2"}},
        {"data": [{"id": "3"}], "paging": {}},  # no next -> stop
    ]
    calls = {"n": 0}

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, params=None, timeout=None):
        i = calls["n"]
        calls["n"] += 1
        return _Resp(pages[i])

    monkeypatch.setattr(client_mod.httpx, "get", fake_get)
    gc = client_mod.GraphClient("tok")
    rows = gc.get_all("act_1/campaigns", {"fields": "id"})
    assert [r["id"] for r in rows] == ["1", "2", "3"]
    assert calls["n"] == 2  # exactly two pages fetched


def test_graphclient_raises_metaapierror(monkeypatch):
    class _Resp:
        def json(self):
            return {"error": {"message": "bad", "code": 100}}

    monkeypatch.setattr(client_mod.httpx, "get", lambda *a, **k: _Resp())
    gc = client_mod.GraphClient("tok")
    with pytest.raises(MetaApiError):
        gc.get("me")
