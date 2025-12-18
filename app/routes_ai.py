from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from .security import get_current_user

from app.services.ai_suggestions import (
    fetch_last_7_checkins,
    build_features,
    rule_based_suggestion,
    maybe_ollama_polish,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/suggestions")
async def get_ai_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    checkins = fetch_last_7_checkins(db, user.id)
    features = build_features(checkins)
    suggestion, tone, ctx = rule_based_suggestion(features)
    suggestion = await maybe_ollama_polish(suggestion, tone, ctx)

    return {"suggestion": suggestion, "tone": tone, "context": ctx}
