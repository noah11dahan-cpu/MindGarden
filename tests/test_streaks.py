# tests/test_streaks.py
from datetime import date, timedelta

from app.streaks import compute_streak_from_daily_done


def test_no_history_streak_zero():
    today = date(2025, 12, 16)
    daily = {}
    assert compute_streak_from_daily_done(daily, today) == 0


def test_completed_today_only_streak_one():
    today = date(2025, 12, 16)
    daily = {today: True}
    assert compute_streak_from_daily_done(daily, today) == 1


def test_completed_today_and_yesterday_missing_day_before_streak_two():
    today = date(2025, 12, 16)
    yesterday = today - timedelta(days=1)

    # Missing (today - 2 days) entirely => streak should still be 2
    daily = {today: True, yesterday: True}
    assert compute_streak_from_daily_done(daily, today) == 2


def test_completed_today_missed_yesterday_missing_day_breaks_streak_at_one():
    today = date(2025, 12, 16)

    # We define: if today is True but yesterday is missing, streak is 1
    daily = {today: True}
    assert compute_streak_from_daily_done(daily, today) == 1


def test_completed_three_days_then_false_stops_at_false():
    today = date(2025, 12, 16)
    d1 = today - timedelta(days=1)
    d2 = today - timedelta(days=2)
    d3 = today - timedelta(days=3)

    # True, True, True, then False => streak should be 3
    daily = {today: True, d1: True, d2: True, d3: False}
    assert compute_streak_from_daily_done(daily, today) == 3


def test_completed_two_days_then_missing_day_stops_at_two():
    today = date(2025, 12, 16)
    d1 = today - timedelta(days=1)
    d2 = today - timedelta(days=2)

    # Missing d2 entirely => streak should be 2 (today + d1)
    daily = {today: True, d1: True}
    assert compute_streak_from_daily_done(daily, today) == 2


def test_today_false_streak_zero():
    today = date(2025, 12, 16)
    daily = {today: False}
    assert compute_streak_from_daily_done(daily, today) == 0
