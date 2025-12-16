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
