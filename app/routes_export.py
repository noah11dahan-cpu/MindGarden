from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .security import get_current_user
from .entitlements import require_premium
from . import models

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/reflections")
def export_reflections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_premium(current_user)

    rows = (
        db.query(models.Checkin)
        .filter(models.Checkin.user_id == current_user.id)
        .filter(models.Checkin.note.isnot(None))
        .order_by(models.Checkin.date.asc())
        .all()
    )

    return {
        "count": len(rows),
        "reflections": [
            {"date": str(r.date), "mood": r.mood, "note": r.note}
            for r in rows
        ],
    }
