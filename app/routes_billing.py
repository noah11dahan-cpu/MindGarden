from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .security import get_current_user
from . import models

router = APIRouter(tags=["billing"])

@router.post("/upgrade")
def upgrade_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    current_user.subscription_tier = "premium"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"subscription_tier": current_user.subscription_tier}
