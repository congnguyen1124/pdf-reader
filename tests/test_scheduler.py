from datetime import datetime, timezone

from linguapdf.domain.scheduler import schedule_review

NOW = datetime(2026, 10, 22, tzinfo=timezone.utc)


def test_again_returns_card_in_ten_minutes() -> None:
    result = schedule_review(3, 8, 2.5, 0, now=NOW)

    assert result.repetitions == 0
    assert result.interval_days == 0.007
    assert int((result.due_at - NOW).total_seconds()) == 600


def test_good_builds_interval() -> None:
    first = schedule_review(0, 0, 2.5, 3, now=NOW)
    second = schedule_review(first.repetitions, first.interval_days, first.ease_factor, 3, now=NOW)

    assert first.interval_days == 1
    assert second.interval_days == 3


def test_easy_increases_ease_but_caps_it() -> None:
    result = schedule_review(4, 10, 2.95, 4, now=NOW)

    assert result.ease_factor == 3.0
    assert result.interval_days == 32.5

