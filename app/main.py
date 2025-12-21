# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from .db import engine, Base
from . import models  # ensure models are imported so tables are registered
from .routes_auth import router as auth_router
from .routes_habits import router as habits_router
from .routes_checkins import router as checkins_router
from .routes_insights import router as insights_router
from .routes_ai import router as ai_router
from .routes_rag import router as rag_router
from .routes_metrics import router as metrics_router
from .observability.logging_config import configure_logging
from .observability.middleware import RequestLoggingMiddleware

class HealthStatus(BaseModel):
    status: str
    db_ok: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MindGarden API",
    version="0.1.0",
    lifespan=lifespan,
)

# NEW (Day 10): logging config + request timing/user logging middleware
configure_logging()
app.add_middleware(RequestLoggingMiddleware)

# CORS for React dev server (Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
        return HealthStatus(status="error", db_ok=False)


app.include_router(auth_router)
app.include_router(habits_router)
app.include_router(checkins_router)
app.include_router(insights_router)
app.include_router(ai_router)
app.include_router(rag_router)
app.include_router(metrics_router)  # NEW (Day 10)
