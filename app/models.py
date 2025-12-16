# app/models.py
from datetime import datetime, date

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date, UniqueConstraint, Float, Text
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    subscription_tier = Column(String, nullable=False, default="free")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # "1 check-in per user per day"
    date = Column(Date, nullable=False, index=True)

    # Keep mood simple for now; validate range in Pydantic
    mood = Column(Integer, nullable=False)

    # Optional note
    note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_checkins_user_date"),
    )

    # Relationship name MUST match schema field name "habit_results"
    habit_results = relationship(
        "CheckinHabitResult",
        back_populates="checkin",
        cascade="all, delete-orphan",
    )


class CheckinHabitResult(Base):
    __tablename__ = "checkin_habit_results"

    id = Column(Integer, primary_key=True, index=True)
    checkin_id = Column(Integer, ForeignKey("checkins.id"), nullable=False, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False, index=True)

    done = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("checkin_id", "habit_id", name="uq_checkin_habit"),
    )

    checkin = relationship("Checkin", back_populates="habit_results")
    habit = relationship("Habit")

class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # The day this insight represents (usually "today")
    date = Column(Date, nullable=False, index=True)

    # 7-day mood average ending on `date` (nullable when no check-ins exist in window)
    mood_avg_7d = Column(Float, nullable=True)

    # Store computed streaks as JSON string (safe/simple for SQLite)
    habit_streaks_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_insights_user_date"),
    )

    user = relationship("User")