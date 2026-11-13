from datetime import date

import update_bills


def budget_on(monkeypatch, today, used):
    """todays_budget() for a given day and number of calls already used this month."""

    class FakeDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(update_bills, "date", FakeDate)
    monkeypatch.setattr(update_bills, "calls_this_month", lambda conn: used)
    monkeypatch.setattr(update_bills, "MONTHLY_LIMIT", 8000)
    monkeypatch.setattr(update_bills, "MAX_BILLS_PER_RUN", 200)
    return update_bills.todays_budget(conn=None)


def test_capped_at_max_bills_per_run(monkeypatch):
    # Nov 13: 7950 left / 18 days = 441, capped to 200
    assert budget_on(monkeypatch, date(2026, 11, 13), used=0) == 200


def test_remaining_calls_spread_over_days_left(monkeypatch):
    # Nov 13: (8000 - 50 - 7000) // 18 days = 52
    assert budget_on(monkeypatch, date(2026, 11, 13), used=7000) == 52


def test_last_day_gets_everything_left(monkeypatch):
    # Nov 30 is the last day: (8000 - 50 - 7900) // 1 = 50
    assert budget_on(monkeypatch, date(2026, 11, 30), used=7900) == 50


def test_reserve_kept_for_weekly_dataset_job(monkeypatch):
    # 50 calls technically left, but they're reserved
    assert budget_on(monkeypatch, date(2026, 11, 30), used=7950) == 0


def test_never_negative_when_over_limit(monkeypatch):
    assert budget_on(monkeypatch, date(2026, 11, 13), used=9000) == 0
