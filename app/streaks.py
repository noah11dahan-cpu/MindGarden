# app/streaks.py
from datetime import date, timedelta
from sqlalchemy.orm import Session

from . import models


def compute_habit_streak(db: Session, user_id: int, habit_id: int, as_of_date: date) -> int:
    """
    Basic MVP streak: counts consecutive days ending at as_of_date
    where the user has a check-in AND that habit was marked done=True.
    Stops at first miss or done=False.
    """
    streak = 0
    d = as_of_date

    while True:
        row = (
            db.query(models.CheckinHabitResult.done)
            .join(models.Checkin, models.Checkin.id == models.CheckinHabitResult.checkin_id)
            .filter(
                models.Checkin.user_id == user_id,
                models.Checkin.date == d,
                models.CheckinHabitResult.habit_id == habit_id,
            )
            .first()
        )

        if not row:
            break

        done = bool(row[0])
        if not done:
            break

        streak += 1
        d = d - timedelta(days=1)

    return streak


# Day 5 addition: pure streak logic (no DB) for unit tests / edge cases
def compute_streak_from_daily_done(
    daily_done_by_date: dict[date, bool],
    as_of_date: date,
) -> int:
    """
    Pure streak function.

    Counts consecutive days ending at as_of_date where daily_done_by_date[day] is True.
    Stops at first missing day OR first False.

    Example:
      daily_done_by_date = {
        2025-12-16: True,
        2025-12-15: True,
        2025-12-14: False,
      }
      as_of_date=2025-12-16 -> streak = 2
    """
    streak = 0
    d = as_of_date
    while True:
        if d not in daily_done_by_date:
            break
        if not bool(daily_done_by_date[d]):
            break
        streak += 1
        d = d - timedelta(days=1)
    return streak
