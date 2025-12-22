from fastapi import HTTPException, status

def is_premium(user) -> bool:
    return getattr(user, "subscription_tier", "free") == "premium"

def require_premium(user) -> None:
    if not is_premium(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium feature. Upgrade required.",
        )
