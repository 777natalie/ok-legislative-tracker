import pytest

import legiscan_client
from legiscan_client import BudgetExceeded, LegiScanError, call_api


class FakeCursor:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.log.append((sql, params))


class FakeConn:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return FakeCursor(self.executed)


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code

    def json(self):
        if self.body is None:
            raise ValueError("not JSON")
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def fake(monkeypatch):
    """Fake database and HTTP for call_api. Tests set fake['used'] / fake['response'] and inspect the rest."""
    fake = {"used": 0, "response": FakeResponse({"status": "OK"}), "requests": [], "conn": FakeConn()}

    def fake_get(url, params, timeout):
        fake["requests"].append(params)
        return fake["response"]

    monkeypatch.setattr(legiscan_client.psycopg, "connect", lambda url: fake["conn"])
    monkeypatch.setattr(legiscan_client, "calls_this_month", lambda conn: fake["used"])
    monkeypatch.setattr(legiscan_client.requests, "get", fake_get)
    monkeypatch.setattr(legiscan_client, "MONTHLY_LIMIT", 8000)
    monkeypatch.setattr(legiscan_client, "API_KEY", "test-key")
    monkeypatch.setattr(legiscan_client, "_last_call_time", 0.0)  # no rate-limit sleep
    return fake


def logged(fake):
    """(operation, params, status, http_status) from the last meta.api_calls insert."""
    sql, values = fake["conn"].executed[-1]
    assert "meta.api_calls" in sql
    return values


def test_budget_exceeded_makes_no_request(fake):
    fake["used"] = 8000
    with pytest.raises(BudgetExceeded):
        call_api("getBill", id=1)
    assert fake["requests"] == []


def test_ok_response_is_returned_and_logged(fake):
    fake["response"] = FakeResponse({"status": "OK", "bill": {"bill_id": 1}})
    assert call_api("getBill", id=1)["bill"]["bill_id"] == 1
    op, _, status, http_status = logged(fake)
    assert (op, status, http_status) == ("getBill", "OK", 200)


def test_api_key_is_sent_but_not_logged(fake):
    call_api("getBill", id=1)
    assert fake["requests"][0]["key"] == "test-key"
    _, params, _, _ = logged(fake)
    assert "key" not in params.obj


def test_legiscan_error_is_logged_then_raised(fake):
    fake["response"] = FakeResponse({"status": "ERROR", "alert": {"message": "Unknown bill id"}})
    with pytest.raises(LegiScanError):
        call_api("getBill", id=999)
    assert logged(fake)[2] == "ERROR"


def test_server_error_is_logged_then_raised(fake):
    fake["response"] = FakeResponse(None, status_code=500)
    with pytest.raises(RuntimeError):
        call_api("getBill", id=1)
    assert logged(fake)[3] == 500
