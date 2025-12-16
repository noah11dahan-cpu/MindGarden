import uuid
from datetime import date
from app.db import SessionLocal
from app import models




def test_post_checkin_updates_db(client):
    email = f"checkin_test_{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "strongpassword123"}

    # signup -> token
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create 2 habits
    h1 = client.post("/habits", json={"name": "Sleep"}, headers=headers)
    assert h1.status_code == 200
    habit1_id = h1.json()["id"]

    h2 = client.post("/habits", json={"name": "Study"}, headers=headers)
    assert h2.status_code == 200
    habit2_id = h2.json()["id"]

    # post check-in
    checkin_payload = {
        "date": str(date(2025, 1, 1)),
        "mood": 4,
        "note": "Solid day.",
        "habit_results": [
            {"habit_id": habit1_id, "done": True},
            {"habit_id": habit2_id, "done": False},
        ],
    }

    rc = client.post("/checkins", json=checkin_payload, headers=headers)
    assert rc.status_code == 200
    data = rc.json()
    assert data["mood"] == 4
    assert data["date"] == "2025-01-01"
    assert len(data["habit_results"]) == 2

    # verify DB updated
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None

        checkin = (
            db.query(models.Checkin)
            .filter(models.Checkin.user_id == user.id, models.Checkin.date == date(2025, 1, 1))
            .first()
        )
        assert checkin is not None

        results = (
            db.query(models.CheckinHabitResult)
            .filter(models.CheckinHabitResult.checkin_id == checkin.id)
            .all()
        )
        assert len(results) == 2
    finally:
        db.close()


def test_one_checkin_per_day_enforced(client):
    email = f"checkin_dupe_{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "strongpassword123"}

    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create 1 habit
    h = client.post("/habits", json={"name": "Run"}, headers=headers)
    assert h.status_code == 200
    habit_id = h.json()["id"]

    checkin_payload = {
        "date": "2025-01-02",
        "mood": 3,
        "note": None,
        "habit_results": [{"habit_id": habit_id, "done": True}],
    }

    r1 = client.post("/checkins", json=checkin_payload, headers=headers)
    assert r1.status_code == 200

    r2 = client.post("/checkins", json=checkin_payload, headers=headers)
    assert r2.status_code == 409
