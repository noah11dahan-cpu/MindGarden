import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    # Using TestClient as a context manager ensures FastAPI lifespan runs,
    # so your Base.metadata.create_all() executes during tests.
    with TestClient(app) as c:
        yield c
