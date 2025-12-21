from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple, Dict, Any
import os
import re

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import Checkin


@dataclass
class Features:
    days_with_checkins: int
    mood_avg_7d: Optional[float]
    habit_done_rate_7d: Optional[float]
    latest_checkin_date: Optional[date]
    streak_broken: bool


def _last_7_days_window(today: date) -> Tuple[date, date]:
    start = today - timedelta(days=6)
    end = today
    return start, end


def fetch_last_7_checkins(db: Session, user_id: int, today: Optional[date] = None) -> List[Checkin]:
    if today is None:
        today = date.today()
    start, end = _last_7_days_window(today)

    q = (
        db.query(Checkin)
        .filter(Checkin.user_id == user_id)
        .filter(Checkin.date >= start)
        .filter(Checkin.date <= end)
        .order_by(desc(Checkin.date))
    )
    return q.all()


def build_features(checkins: List[Checkin], today: Optional[date] = None) -> Features:
    if today is None:
        today = date.today()

    if not checkins:
        return Features(
            days_with_checkins=0,
            mood_avg_7d=None,
            habit_done_rate_7d=None,
            latest_checkin_date=None,
            streak_broken=True,
        )

    days_with_checkins = len({c.date for c in checkins})
    moods = [c.mood for c in checkins if c.mood is not None]
    mood_avg = round(sum(moods) / len(moods), 2) if moods else None

    total_results = 0
    total_done = 0
    for c in checkins:
        for hr in (c.habit_results or []):
            total_results += 1
            total_done += 1 if hr.done else 0

    habit_done_rate = round(total_done / total_results, 2) if total_results > 0 else None

    latest_date = max(c.date for c in checkins)
    yesterday = today - timedelta(days=1)
    streak_broken = (yesterday not in {c.date for c in checkins})

    return Features(
        days_with_checkins=days_with_checkins,
        mood_avg_7d=mood_avg,
        habit_done_rate_7d=habit_done_rate,
        latest_checkin_date=latest_date,
        streak_broken=streak_broken,
    )


def _sentences_count(s: str) -> int:
    s = s.strip()
    if not s:
        return 0
    return len(re.findall(r"[.!?]+", s))


def rule_based_suggestion(f: Features) -> tuple[str, str, Dict[str, Any]]:
    ctx: Dict[str, Any] = {
        "days_with_checkins": f.days_with_checkins,
        "mood_avg_7d": f.mood_avg_7d,
        "habit_done_rate_7d": f.habit_done_rate_7d,
        "latest_checkin_date": str(f.latest_checkin_date) if f.latest_checkin_date else None,
        "streak_broken": f.streak_broken,
    }

    if f.days_with_checkins == 0:
        tone = "gentle"
        suggestion = "Start tiny: do a 2-minute version of one habit right now, then log a check-in. Keep it easy and just show up today."
        return suggestion, tone, ctx

    if f.streak_broken:
        tone = "gentle"
        suggestion = "Your streak broke, so restart small: pick one habit and do the easiest 2-minute version today. Check in immediately after to lock the win."
        return suggestion, tone, ctx

    if f.mood_avg_7d is not None and f.mood_avg_7d <= 2.5:
        tone = "gentle"
        suggestion = "Do a 5-minute reset: water, a short walk, and one quick habit action. Then write one sentence about what felt hardest."
        return suggestion, tone, ctx

    if f.habit_done_rate_7d is not None and f.habit_done_rate_7d < 0.5:
        tone = "neutral"
        suggestion = "Today, aim for consistency: complete just one habit fully and leave the rest as optional. If you finish, add a one-line note on what helped."
        return suggestion, tone, ctx

    tone = "pushy"
    suggestion = "You’re consistent this week: add a small stretch by increasing one habit by 10 percent today. Keep it short, then celebrate with a quick check-in note."
    return suggestion, tone, ctx


async def maybe_ollama_polish(suggestion: str, tone: str, ctx: Dict[str, Any]) -> str:
    provider = os.getenv("AI_PROVIDER", "hybrid").lower()
    if provider not in ("hybrid", "ollama"):
        return suggestion

    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    if not ollama_url:
        return suggestion

    model = os.getenv("OLLAMA_MODEL", "llama3").strip()

    prompt = (
        "Rewrite the following as a personalized tiny challenge.\n"
        "Constraints: 1 to 2 sentences, no lists, no emojis.\n"
        f"Tone target: {tone}\n"
        f"Context: {ctx}\n"
        f"Text: {suggestion}\n"
        "Return only the rewritten text."
    )

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{ollama_url.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            out = (data.get("response") or "").strip()

        if not out:
            return suggestion
        if _sentences_count(out) > 2:
            return suggestion
        if len(out) > 260:
            return suggestion

        return out
    except Exception:
        return suggestion
async def maybe_ollama_polish_with_provider(
    suggestion: str,
    tone: str,
    ctx: Dict[str, Any],
) -> tuple[str, str]:
    provider = os.getenv("AI_PROVIDER", "hybrid").lower()
    if provider not in ("hybrid", "ollama"):
        return suggestion, "rules"

    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    if not ollama_url:
        return suggestion, "rules"

    model = os.getenv("OLLAMA_MODEL", "llama3").strip()

    prompt = (
        "Rewrite the following as a personalized tiny challenge.\n"
        "Constraints: 1 to 2 sentences, no lists, no emojis.\n"
        f"Tone target: {tone}\n"
        f"Context: {ctx}\n"
        f"Text: {suggestion}\n"
        "Return only the rewritten text."
    )

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{ollama_url.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            out = (data.get("response") or "").strip()

        if not out:
            return suggestion, "rules"
        if _sentences_count(out) > 2:
            return suggestion, "rules"
        if len(out) > 260:
            return suggestion, "rules"

        return out, "ollama"
    except Exception:
        return suggestion, "rules"


async def maybe_ollama_polish(suggestion: str, tone: str, ctx: Dict[str, Any]) -> str:
    """Backwards-compatible wrapper.

    Returns only the suggestion text (original behavior).
    """
    out, _provider = await maybe_ollama_polish_with_provider(suggestion, tone, ctx)
    return out
