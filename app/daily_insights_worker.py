# app/daily_insights_worker.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from .models import Checkin, Habit, Insight


@dataclass(frozen=True)
class InsightMetrics:
    """Pure computed metrics (no DB objects)."""
    mood_avg_7d: Optional[float]
    habit_streaks: List[Dict[str, int]]  # [{"habit_id": 123, "streak": 5}, ...]


def _get_contiguous_checkins_ending_on(
    db: Session,
    *,
    user_id: int,
    target_date: date,
) -> List[Checkin]:
    """
    Returns check-ins for a user in a contiguous daily run ending at target_date.
    Example: if target_date has a check-in, and the user also checked in yesterday,
    etc., we keep going until we hit a missing day (gap > 1).
    If there is no check-in on target_date, returns [].
    """
    # Ensure we have the target-date check-in; if not, streaks are 0 by definition.
    target = (
        db.query(Checkin)
        .filter(Checkin.user_id == user_id, Checkin.date == target_date)
        .first()
    )
    if not target:
        return []

    # Pull check-ins up to target_date descending and stop at first gap.
    # We eager-load habit_results so we don't do N+1 queries.
    rows = (
        db.query(Checkin)
        .options(joinedload(Checkin.habit_results))
        .filter(Checkin.user_id == user_id, Checkin.date <= target_date)
        .order_by(Checkin.date.desc())
        .all()
    )

    contiguous: List[Checkin] = []
    expected = target_date
    for c in rows:
        if c.date != expected:
            # We stop when we hit the first gap (or out-of-order day).
            break
        contiguous.append(c)
        expected = expected - timedelta(days=1)

    return contiguous


def _compute_mood_avg_7d(
    db: Session,
    *,
    user_id: int,
    target_date: date,
) -> Optional[float]:
    """
    Computes the average mood for check-ins in [target_date-6, target_date].
    Returns None if no check-ins exist in that window.
    """
    start = target_date - timedelta(days=6)
    rows = (
        db.query(Checkin.mood)
        .filter(
            Checkin.user_id == user_id,
            Checkin.date >= start,
            Checkin.date <= target_date,
        )
        .all()
    )
    moods = [r[0] for r in rows]  # rows are tuples like [(mood,), ...]
    if not moods:
        return None
    return sum(moods) / float(len(moods))


def _compute_habit_streaks(
    db: Session,
    *,
    user_id: int,
    target_date: date,
) -> List[Dict[str, int]]:
    """
    Computes the current streak per active habit, ending at target_date.

    Rules:
    - Streak counts consecutive days ending at target_date where:
      (a) a check-in exists for that day AND
      (b) the habit is marked done for that day.
    - If there is no check-in on target_date -> all streaks are 0.
    - Missing day breaks streak for all habits (handled by contiguous run).
    - A day with check-in but habit not done breaks that habit's streak.
    """
    habits: List[Habit] = (
        db.query(Habit)
        .filter(Habit.user_id == user_id, Habit.active == True)  # noqa: E712
        .order_by(Habit.id.asc())
        .all()
    )

    contiguous = _get_contiguous_checkins_ending_on(
        db, user_id=user_id, target_date=target_date
    )
    if not contiguous:
        # No check-in today => by definition streaks are 0
        return [{"habit_id": h.id, "streak": 0} for h in habits]

    # Build mapping: date -> {habit_id: done_bool}
    # Note: if a habit has no result row that day, treat as not done.
    day_done: Dict[date, Dict[int, bool]] = {}
    for c in contiguous:
        per_day: Dict[int, bool] = {}
        for hr in c.habit_results:
            per_day[hr.habit_id] = bool(hr.done)
        day_done[c.date] = per_day

    # contiguous is in descending date order: [target_date, target_date-1, ...]
    streaks: List[Dict[str, int]] = []
    for h in habits:
        s = 0
        for c in contiguous:
            done_map = day_done.get(c.date, {})
            if done_map.get(h.id, False):
                s += 1
            else:
                break
        streaks.append({"habit_id": h.id, "streak": s})

    return streaks


def compute_metrics_for_date(
    db: Session,
    *,
    user_id: int,
    target_date: date,
) -> InsightMetrics:
    """
    Computes all MVP insight metrics for a given user & day, without writing DB.
    """
    mood_avg = _compute_mood_avg_7d(db, user_id=user_id, target_date=target_date)
    streaks = _compute_habit_streaks(db, user_id=user_id, target_date=target_date)
    return InsightMetrics(mood_avg_7d=mood_avg, habit_streaks=streaks)


def upsert_insight_for_date(
    db: Session,
    *,
    user_id: int,
    target_date: date,
) -> Insight:
    """
    Computes metrics and inserts/updates the Insight row for (user_id, target_date).
    Does NOT commit; caller should db.commit().
    """
    metrics = compute_metrics_for_date(db, user_id=user_id, target_date=target_date)

    existing = (
        db.query(Insight)
        .filter(Insight.user_id == user_id, Insight.date == target_date)
        .first()
    )

    payload = {
        "habits": metrics.habit_streaks,
    }

    now = datetime.utcnow()

    if existing:
        existing.mood_avg_7d = metrics.mood_avg_7d
        existing.habit_streaks_json = json.dumps(payload, ensure_ascii=False)
        existing.updated_at = now
        return existing

    insight = Insight(
        user_id=user_id,
        date=target_date,
        mood_avg_7d=metrics.mood_avg_7d,
        habit_streaks_json=json.dumps(payload, ensure_ascii=False),
        created_at=now,
        updated_at=now,
    )
    db.add(insight)
    return insight
