import os
from datetime import date
from uuid import uuid4


def _signup_and_login_get_token(client) -> str:
    email = f"obs_test_{uuid4().hex[:8]}@example.com"
    password = "strongpassword123"

    client.post("/auth/signup", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_metrics_checkins_today_increments(client):
    token = _signup_and_login_get_token(client)

    base = client.get("/metrics?format=json").json()["checkins_today"]

    today = date.today()
    resp = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={"date": str(today), "mood": 4, "note": "obs", "habit_results": []},
    )
    assert resp.status_code in (200, 201), resp.text

    after = client.get("/metrics?format=json").json()["checkins_today"]
    assert after == base + 1


def test_ai_rate_limit_works(client):
    os.environ["AI_PROVIDER"] = "rules"

    token = _signup_and_login_get_token(client)

    for i in range(30):
        resp = client.get("/ai/suggestions", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"call {i+1} failed: {resp.text}"

    resp = client.get("/ai/suggestions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 429, resp.text
