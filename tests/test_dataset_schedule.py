from datetime import datetime, timezone

from run_pipeline import last_dataset_publication


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_midweek_returns_previous_sunday():
    # Wednesday Nov 11, 2026 -> Sunday Nov 8 at 10:00 UTC
    assert last_dataset_publication(utc(2026, 11, 11, 15, 0)) == utc(2026, 11, 8, 10, 0)


def test_sunday_before_publication_returns_last_week():
    # One minute before Sunday's publication, last week's still counts
    assert last_dataset_publication(utc(2026, 11, 8, 9, 59)) == utc(2026, 11, 1, 10, 0)


def test_sunday_at_publication_returns_today():
    assert last_dataset_publication(utc(2026, 11, 8, 10, 0)) == utc(2026, 11, 8, 10, 0)
