from datetime import date, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models


def get_7_day_mood_avg(db: Session, user_id: int, end_date: date) -> Optional[float]:
    start_date = end_date - timedelta(days=6)
    avg_val = (
        db.query(func.avg(models.Checkin.mood))
        .filter(
            models.Checkin.user_id == user_id,
            models.Checkin.date >= start_date,
            models.Checkin.date <= end_date,
        )
        .scalar()
    )
    return float(avg_val) if avg_val is not None else None


def get_last_n_moods(db: Session, user_id: int, n: int, end_date: date) -> List[int]:
    rows = (
        db.query(models.Checkin.mood)
        .filter(models.Checkin.user_id == user_id, models.Checkin.date <= end_date)
        .order_by(models.Checkin.date.desc())
        .limit(n)
        .all()
    )
    return [r[0] for r in rows]
