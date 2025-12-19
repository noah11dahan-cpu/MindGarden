# tests/conftest.py
import os

import pytest
from fastapi.testclient import TestClient

# IMPORTANT: set DB_URL BEFORE importing app modules that create the engine/sessionmaker.
# Use a file DB so multiple connections (API + SessionLocal in tests) share the same tables.
os.environ["DB_URL"] = "sqlite:///./test.db"

# Prevent RAG/model downloads during tests
os.environ.setdefault("RAG_ENABLED", "0")

from app.main import app  # noqa: E402
from app.db import Base, engine  # noqa: E402


@pytest.fixture()
def client():
    # Fresh schema per test to avoid state bleed
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Using TestClient as a context manager ensures FastAPI lifespan runs too
    with TestClient(app) as c:
        yield c
