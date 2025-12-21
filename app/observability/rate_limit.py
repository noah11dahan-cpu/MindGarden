from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RateLimitEvent, User
from app.security import get_current_user


def rate_limit(
    *,
    endpoint_key: str,
    limit: int,
    window_seconds: int,
) -> Callable:
    """DB-backed per-user rate limiter.

    This works across process restarts and multiple API workers because the
    counter lives in the database.
    """

    async def _dep(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> None:
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        count = (
            db.query(RateLimitEvent)
            .filter(RateLimitEvent.user_id == user.id)
            .filter(RateLimitEvent.endpoint == endpoint_key)
            .filter(RateLimitEvent.created_at >= window_start)
            .count()
        )

        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {endpoint_key}. Try again later.",
                headers={"Retry-After": str(window_seconds)},
            )

        db.add(
            RateLimitEvent(
                user_id=user.id,
                endpoint=endpoint_key,
                created_at=now,
            )
        )
        db.commit()

    return _dep
