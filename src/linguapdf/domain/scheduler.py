from __future__ import annotations

from datetime import datetime, timedelta, timezone

from linguapdf.domain.models import ScheduleResult


def schedule_review(
    repetitions: int,
    interval_days: float,
    ease_factor: float,
    rating: int,
    *,
    now: datetime | None = None,
) -> ScheduleResult:
    """Return the next review using a gentle SM-2 inspired schedule.

    Ratings are 0=again, 2=hard, 3=good and 4=easy.
    """
    if rating not in {0, 2, 3, 4}:
        raise ValueError("rating must be one of 0, 2, 3, 4")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    if rating == 0:
        return ScheduleResult(0, 0.007, max(1.3, ease_factor - 0.2), current + timedelta(minutes=10))

    next_repetitions = repetitions + 1
    if rating == 2:
        next_interval = max(1.0, interval_days * 1.2)
        next_ease = max(1.3, ease_factor - 0.15)
    elif rating == 3:
        if repetitions == 0:
            next_interval = 1.0
        elif repetitions == 1:
            next_interval = 3.0
        else:
            next_interval = max(1.0, interval_days * ease_factor)
        next_ease = ease_factor
    else:
        if repetitions == 0:
            next_interval = 3.0
        else:
            next_interval = max(4.0, interval_days * (ease_factor + 0.3))
        next_ease = min(3.0, ease_factor + 0.15)

    return ScheduleResult(
        next_repetitions,
        round(next_interval, 3),
        round(next_ease, 2),
        current + timedelta(days=next_interval),
    )

