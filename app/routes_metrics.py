from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Literal, List

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .db import get_db
from . import models
from datetime import date as date_type
from sqlalchemy import func

# NEW (Day 11 Monetization hooks)
from .security import get_current_user
from .entitlements import require_premium

router = APIRouter(tags=["metrics"])


def _p95(values: List[int]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    # Nearest-rank p95
    idx = int(round(0.95 * (len(values) - 1)))
    return float(values[idx])


@router.get("/metrics")
def metrics(
    format: Literal["json", "prometheus"] = Query("prometheus"),
    db: Session = Depends(get_db),
):
    """Basic app metrics for debugging + recruiter demos.

    - /metrics?format=json
    - /metrics?format=prometheus
    """

    # IMPORTANT: check-in "date" is a date field users submit (local day).
    # Using UTC date can be "tomorrow" in the evening and breaks the "today" counter.
    today = date_type.today()
    today_utc = datetime.utcnow().date()

    start_dt = datetime.combine(today, time.min)
    end_dt = start_dt + timedelta(days=1)

    checkins_today = db.query(models.Checkin).filter(models.Checkin.date == today).count()

    ai_events_today = (
        db.query(models.AIRequestEvent)
        .filter(models.AIRequestEvent.created_at >= start_dt)
        .filter(models.AIRequestEvent.created_at < end_dt)
        .all()
    )
    latencies = [int(e.latency_ms) for e in ai_events_today if e.latency_ms is not None]
    ai_count_today = len(ai_events_today)
    avg_latency = (sum(latencies) / len(latencies)) if latencies else None
    p95_latency = _p95(latencies)

    payload = {
        "date_utc": str(today_utc),
        "checkins_today": checkins_today,
        "ai_suggestions_count_today": ai_count_today,
        "ai_suggestions_latency_ms_avg_today": round(avg_latency, 2) if avg_latency is not None else None,
        "ai_suggestions_latency_ms_p95_today": p95_latency,
    }

    if format == "json":
        return payload

    # Prometheus-compatible text format
    lines = [
        "# HELP mindgarden_checkins_today Total check-ins created today (UTC)",
        "# TYPE mindgarden_checkins_today gauge",
        f"mindgarden_checkins_today {checkins_today}",
        "# HELP mindgarden_ai_suggestions_count_today Total AI suggestion requests today (UTC)",
        "# TYPE mindgarden_ai_suggestions_count_today gauge",
        f"mindgarden_ai_suggestions_count_today {ai_count_today}",
    ]
    if avg_latency is not None:
        lines += [
            "# HELP mindgarden_ai_suggestions_latency_ms_avg_today Average AI suggestion latency in ms today (UTC)",
            "# TYPE mindgarden_ai_suggestions_latency_ms_avg_today gauge",
            f"mindgarden_ai_suggestions_latency_ms_avg_today {round(avg_latency, 2)}",
        ]
    if p95_latency is not None:
        lines += [
            "# HELP mindgarden_ai_suggestions_latency_ms_p95_today p95 AI suggestion latency in ms today (UTC)",
            "# TYPE mindgarden_ai_suggestions_latency_ms_p95_today gauge",
            f"mindgarden_ai_suggestions_latency_ms_p95_today {p95_latency}",
        ]

    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")


# NEW (Day 11): authenticated analytics window (freemium gate >30 days)
@router.get("/metrics/analytics")
def metrics_analytics(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Long-term analytics hook:
    - Free: up to 30 days
    - Premium: >30 days
    """

    if days > 30:
        require_premium(current_user)

    today = datetime.utcnow().date()
    window_start = today - timedelta(days=days - 1)

    # Check-ins in window (inclusive)
    checkins_window = (
        db.query(models.Checkin)
        .filter(models.Checkin.user_id == current_user.id)
        .filter(models.Checkin.date >= window_start)
        .filter(models.Checkin.date <= today)
        .count()
    )

    # AI events in window (inclusive)
    start_dt = datetime.combine(window_start, time.min)
    end_dt = datetime.combine(today, time.max)

    ai_events_window = (
        db.query(models.AIRequestEvent)
        .filter(models.AIRequestEvent.user_id == current_user.id)
        .filter(models.AIRequestEvent.created_at >= start_dt)
        .filter(models.AIRequestEvent.created_at <= end_dt)
        .all()
    )

    latencies = [int(e.latency_ms) for e in ai_events_window if e.latency_ms is not None]
    ai_count_window = len(ai_events_window)
    avg_latency = (sum(latencies) / len(latencies)) if latencies else None
    p95_latency = _p95(latencies)

    return {
        "date_utc": str(today),
        "window_days": days,
        "window_start_utc": str(window_start),
        "checkins_window": checkins_window,
        "ai_suggestions_count_window": ai_count_window,
        "ai_suggestions_latency_ms_avg_window": round(avg_latency, 2) if avg_latency is not None else None,
        "ai_suggestions_latency_ms_p95_window": p95_latency,
        "subscription_tier": getattr(current_user, "subscription_tier", "free"),
    }
