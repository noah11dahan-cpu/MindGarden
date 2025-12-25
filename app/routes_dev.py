# app/routes_dev.py
from __future__ import annotations

import os
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from . import models
from .security import get_password_hash

# Optional (RAG). Seed should still work if these fail.
from .embedding_model import get_embedder
from .rag_store import get_rag_store

router = APIRouter(prefix="/dev", tags=["dev"])


def _require_dev_enabled() -> None:
    if os.getenv("ENABLE_DEV_ROUTES", "0") != "1":
        # Hide in prod-like runs
        raise HTTPException(status_code=404, detail="Not found")


def _require_seed_key(x_dev_seed_key: str | None) -> None:
    expected = os.getenv("DEV_SEED_KEY", "")
    if not expected or x_dev_seed_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/seed_demo")
def seed_demo(
    db: Session = Depends(get_db),
    x_dev_seed_key: str | None = Header(default=None),
):
    """
    Creates/updates a deterministic premium demo user + 3 habits + 7 days of check-ins
    ending YESTERDAY, so you can create TODAY's check-in live in your demo.
    """
    _require_dev_enabled()
    _require_seed_key(x_dev_seed_key)

    demo_email = os.getenv("DEMO_EMAIL", "noah11dahan@gmail.com")
    demo_password = os.getenv("DEMO_PASSWORD", "DemoPass123!")
    tier = "premium"

    today = date.today()
    through = today - timedelta(days=1)

    # 1) Upsert user
    user = db.query(models.User).filter(models.User.email == demo_email).first()
    if user is None:
        user = models.User(
            email=demo_email,
            hashed_password=get_password_hash(demo_password),
            subscription_tier=tier,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.subscription_tier = tier
        user.hashed_password = get_password_hash(demo_password)
        db.commit()
        db.refresh(user)

    # 2) Wipe existing demo data (safe reseed)
    # Delete dependent rows first
    checkins = db.query(models.Checkin).filter(models.Checkin.user_id == user.id).all()
    checkin_ids = [c.id for c in checkins]

    if checkin_ids:
        db.query(models.CheckinHabitResult).filter(models.CheckinHabitResult.checkin_id.in_(checkin_ids)).delete(synchronize_session=False)
        db.query(models.ReflectionEmbedding).filter(models.ReflectionEmbedding.checkin_id.in_(checkin_ids)).delete(synchronize_session=False)

    db.query(models.Checkin).filter(models.Checkin.user_id == user.id).delete(synchronize_session=False)
    db.query(models.Habit).filter(models.Habit.user_id == user.id).delete(synchronize_session=False)
    db.query(models.Insight).filter(models.Insight.user_id == user.id).delete(synchronize_session=False)
    db.commit()

    # 3) Create 3 habits
    habit_names = ["Sleep by 11", "20 min walk", "No sugar"]
    habits: list[models.Habit] = []
    for name in habit_names:
        h = models.Habit(user_id=user.id, name=name, active=True)
        db.add(h)
        habits.append(h)
    db.commit()
    for h in habits:
        db.refresh(h)

    # 4) Seed 7 days of check-ins ending yesterday (no check-in today)
    notes = [
        "Felt anxious before a presentation. A short walk helped a lot.",
        "Slept late. Sugar cravings hit around mid-afternoon.",
        "Good focus day. Walk boosted mood.",
        "Low energy. Skipped walk but avoided sugar.",
        "Great sleep. Calm mood. Stayed consistent.",
        "Stressful workload. Mood dipped after snacking.",
        "Felt proud. Outdoor walk improved everything.",
    ]

    # Try to enable RAG embeddings during seeding (optional)
    embedder = None
    rag = None
    try:
        embedder = get_embedder()
        rag = get_rag_store(embedder) if embedder is not None else None
    except Exception:
        rag = None

    for i in range(7):
        d = today - timedelta(days=(7 - i))  # 7 days ago .. yesterday
        mood = 4 + (i % 3)  # 4..6

        c = models.Checkin(
            user_id=user.id,
            date=d,
            mood=mood,
            note=notes[i],
        )
        db.add(c)
        db.flush()  # gives c.id

        # Habit results pattern: show variety
        for j, h in enumerate(habits):
            done = True
            if h.name == "20 min walk":
                done = (i % 2 == 0)
            elif h.name == "No sugar":
                done = (i % 3 != 0)
            db.add(models.CheckinHabitResult(checkin_id=c.id, habit_id=h.id, done=done))

        # RAG embedding if available and note present
        try:
            if rag is not None:
                rag.add_reflection_for_checkin(db=db, user_id=user.id, checkin=c)
        except Exception:
            pass

    db.commit()

    return {
        "ok": True,
        "email": demo_email,
        "password": demo_password,
        "tier": tier,
        "seeded_days": 7,
        "seeded_through": str(through),
        "note": "Seeded through yesterday so you can create today's check-in live.",
    }
