import os
import re
from datetime import date, timedelta
from uuid import uuid4  # NEW


def _count_sentences(s: str) -> int:
    return len(re.findall(r"[.!?]+", s.strip()))


def _signup_and_login_get_token(client) -> str:
    email = f"ai_test_{uuid4().hex[:8]}@example.com"  # CHANGED (unique per test run)
    password = "strongpassword123"

    # signup (may already exist if tests reuse DB; ignore failure if 400)
    client.post("/auth/signup", json={"email": email, "password": password})

    # login must succeed
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["access_token"]


def test_ai_suggestions_returns_200_and_two_sentences_max(client):
    # Force rules mode so tests do not depend on Ollama
    os.environ["AI_PROVIDER"] = "rules"

    token = _signup_and_login_get_token(client)

    # Seed 2 checkins: today and yesterday, with habit_results empty (valid)
    today = date.today()
    yesterday = today - timedelta(days=1)

    resp1 = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={"date": str(yesterday), "mood": 3, "note": "ok", "habit_results": []},
    )
    assert resp1.status_code in (200, 201), resp1.text

    resp2 = client.post(
        "/checkins",
        headers={"Authorization": f"Bearer {token}"},
        json={"date": str(today), "mood": 4, "note": "better", "habit_results": []},
    )
    assert resp2.status_code in (200, 201), resp2.text

    # Call AI suggestions endpoint
    resp = client.get(
        "/ai/suggestions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "suggestion" in data
    assert isinstance(data["suggestion"], str)
    assert _count_sentences(data["suggestion"]) <= 2
    assert data["tone"] in ("gentle", "neutral", "pushy")
