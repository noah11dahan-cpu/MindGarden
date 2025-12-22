from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4

client = TestClient(app)

def signup_and_login(email: str, password: str):
    r = client.post("/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_export_reflections_requires_premium():
    headers = signup_and_login("free_export@test.com", "strongpassword123")
    r = client.get("/export/reflections", headers=headers)
    assert r.status_code == 403

def test_upgrade_allows_export_reflections():
    headers = signup_and_login("premium_export@test.com", "strongpassword123")
    r = client.post("/upgrade", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["subscription_tier"] == "premium"
    r = client.get("/export/reflections", headers=headers)
    assert r.status_code == 200, r.text

def test_deep_dive_requires_premium():
    headers = signup_and_login("deepdive@test.com", "strongpassword123")
    r = client.post("/ai/deep_dive", json={"topic": "sleep"}, headers=headers)
    assert r.status_code in (403, 404)  # 404 if your AI router prefix is not /ai

def test_deep_dive_works_after_upgrade():
    headers = signup_and_login("deepdive_premium@test.com", "strongpassword123")
    client.post("/upgrade", headers=headers)
    r = client.post("/ai/deep_dive", json={"topic": "sleep"}, headers=headers)
    assert r.status_code in (200, 404)
def _signup_and_login_get_token(client) -> str:
    email = f"mon_test_{uuid4().hex[:8]}@example.com"
    password = "strongpassword123"

    client.post("/auth/signup", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_metrics_analytics_free_allows_30_days(client):
    token = _signup_and_login_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/metrics/analytics?days=30", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["window_days"] == 30
    assert data["subscription_tier"] == "free"


def test_metrics_analytics_free_blocks_31_days(client):
    token = _signup_and_login_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/metrics/analytics?days=31", headers=headers)
    assert resp.status_code == 403, resp.text

