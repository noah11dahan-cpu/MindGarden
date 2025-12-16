from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from . import models, schemas
from .security import get_current_user

router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("", response_model=schemas.HabitOut)
def create_habit(
    habit_in: schemas.HabitCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Count active habits for this user
    active_count = (
        db.query(models.Habit)
        .filter(models.Habit.user_id == current_user.id, models.Habit.active == True)
        .count()
    )

    # Enforce "max 3 habits" for free tier
    if current_user.subscription_tier == "free" and active_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free tier allows a maximum of 3 active habits.",
        )

    habit = models.Habit(user_id=current_user.id, name=habit_in.name, active=True)
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


@router.get("", response_model=List[schemas.HabitOut])
def list_habits(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Habit)
        .filter(models.Habit.user_id == current_user.id, models.Habit.active == True)
        .all()
    )


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    habit = (
        db.query(models.Habit)
        .filter(models.Habit.id == habit_id, models.Habit.user_id == current_user.id)
        .first()
    )
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found.")

    habit.active = False
    db.add(habit)
    db.commit()
    return
