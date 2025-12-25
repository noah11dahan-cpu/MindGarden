# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
import os

from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

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
from .routes_billing import router as billing_router
from .routes_export import router as export_router


class HealthStatus(BaseModel):
    status: str
    db_ok: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


# IMPORTANT:
# We explicitly control docs + openapi endpoints so they work for:
#   - direct backend: /docs + /openapi.json
#   - proxied backend under /api: /api/docs + /api/openapi.json
app = FastAPI(
    title="MindGarden API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
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

# --- OpenAPI schema (shared) ---
def _build_openapi_schema():
    return get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )


@app.get("/openapi.json", include_in_schema=False)
def openapi_json():
    return JSONResponse(_build_openapi_schema())


@app.get("/api/openapi.json", include_in_schema=False)
def openapi_json_api():
    return JSONResponse(_build_openapi_schema())


# --- Swagger UI ---
@app.get("/docs", include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="MindGarden API - Swagger UI",
    )


@app.get("/api/docs", include_in_schema=False)
def swagger_ui_api():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="MindGarden API - Swagger UI",
    )


# --- ReDoc (optional, but nice) ---
@app.get("/redoc", include_in_schema=False)
def redoc():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="MindGarden API - ReDoc",
    )


@app.get("/api/redoc", include_in_schema=False)
def redoc_api():
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title="MindGarden API - ReDoc",
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
app.include_router(metrics_router)
app.include_router(billing_router)
app.include_router(export_router)
if os.getenv("ENABLE_DEV_ROUTES", "0") == "1":
    from .routes_dev import router as dev_router
    app.include_router(dev_router)
