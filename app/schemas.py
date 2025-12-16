from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from datetime import date
from typing import List, Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    subscription_tier: str



class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class HabitCreate(BaseModel):
    name: str

class HabitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    active: bool
 
class CheckinHabitResultIn(BaseModel):
    habit_id: int
    done: bool


class CheckinCreate(BaseModel):
    date: date
    mood: int
    note: Optional[str] = None
    habit_results: List[CheckinHabitResultIn] = []

    @field_validator("mood")
    @classmethod
    def mood_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("mood must be between 1 and 5")
        return v

    @field_validator("note")
    @classmethod
    def note_len(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 1000:
            raise ValueError("note must be <= 1000 characters")
        return v

    @field_validator("habit_results")
    @classmethod
    def no_duplicate_habits(cls, v: List[CheckinHabitResultIn]) -> List[CheckinHabitResultIn]:
        seen = set()
        for item in v:
            if item.habit_id in seen:
                raise ValueError("habit_results contains duplicate habit_id")
            seen.add(item.habit_id)
        return v


class CheckinHabitResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    habit_id: int
    done: bool


class CheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    mood: int
    note: Optional[str]
    habit_results: List[CheckinHabitResultOut]

# --- Day 5: Insights schemas (ADD) ---
from typing import Optional
from datetime import date as date_type
from pydantic import BaseModel

try:
    # Pydantic v2
    from pydantic import ConfigDict
except Exception:  # pragma: no cover
    ConfigDict = None


class InsightOut(BaseModel):
    id: int
    user_id: int
    date: date_type
    mood_avg_7d: Optional[float] = None
    habit_streaks_json: str

    if ConfigDict is not None:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True
