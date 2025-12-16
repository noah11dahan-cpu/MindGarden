# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text

from .db import engine, Base
from . import models  # ensure models are imported so tables are registered
from .routes_auth import router as auth_router
from .routes_habits import router as habits_router
from .routes_checkins import router as checkins_router


class HealthStatus(BaseModel):
    status: str
    db_ok: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs on startup
    Base.metadata.create_all(bind=engine)
    yield
    # If you ever need shutdown logic, put it after yield


app = FastAPI(
    title="MindGarden API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {"message": "MindGarden API is running"}


@app.get("/healthz", response_model=HealthStatus)
def healthz():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return HealthStatus(status="ok", db_ok=True)
    except Exception:
        # small fix: if DB check fails, reflect that in status
        return HealthStatus(status="error", db_ok=False)


# Routers
app.include_router(auth_router)
app.include_router(habits_router)
app.include_router(checkins_router)