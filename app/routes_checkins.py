from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from . import models, schemas
from .security import get_current_user

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("", response_model=schemas.CheckinOut)
def create_checkin(
    checkin_in: schemas.CheckinCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 1) Enforce "1 per day" (friendly pre-check)
    existing = (
        db.query(models.Checkin)
        .filter(models.Checkin.user_id == current_user.id, models.Checkin.date == checkin_in.date)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Check-in already exists for this date.",
        )

    # 2) Validate habit_ids (must belong to user, must be active)
    habit_ids = [hr.habit_id for hr in checkin_in.habit_results]
    if habit_ids:
        habits = (
            db.query(models.Habit)
            .filter(
                models.Habit.id.in_(habit_ids),
                models.Habit.user_id == current_user.id,
                models.Habit.active == True,
            )
            .all()
        )
        found_ids = {h.id for h in habits}
        missing = [hid for hid in habit_ids if hid not in found_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid habit_id(s) for this user: {missing}",
            )

    # 3) Insert checkin + habit results in one transaction
    checkin = models.Checkin(
        user_id=current_user.id,
        date=checkin_in.date,
        mood=checkin_in.mood,
        note=checkin_in.note,
    )
    db.add(checkin)

    try:
        db.flush()  # assign checkin.id before inserting results

        for hr in checkin_in.habit_results:
            db.add(
                models.CheckinHabitResult(
                    checkin_id=checkin.id,
                    habit_id=hr.habit_id,
                    done=hr.done,
                )
            )

        db.commit()
        db.refresh(checkin)
        return checkin

    except IntegrityError:
        db.rollback()
        # covers race condition if two requests happen same day
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Check-in already exists for this date.",
        )
