# app/routes_insights.py
from __future__ import annotations

import json
from datetime import date as date_type

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from . import models, schemas
from .security import get_current_user
from .daily_insights_worker import upsert_insight_for_date

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/today", response_model=schemas.InsightOut)
def get_today_insights(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    today: date_type = date_type.today()

    # Compute and upsert (insert or update) the insight row for today.
    insight = upsert_insight_for_date(db, user_id=current_user.id, target_date=today)
    db.commit()
    db.refresh(insight)

    # Ensure JSON string is always present (defensive)
    if not insight.habit_streaks_json:
        insight.habit_streaks_json = "{}"

    return insight
