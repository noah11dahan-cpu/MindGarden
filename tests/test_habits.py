import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_free_tier_max_3_habits():
    email = f"auth_test_{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "strongpassword123"}

    # signup returns token
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 200
    token = r.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # create 3 habits
    for i in range(3):
        rr = client.post("/habits", json={"name": f"Habit {i}"}, headers=headers)
        assert rr.status_code == 200

    # 4th should fail
    rr4 = client.post("/habits", json={"name": "Habit 4"}, headers=headers)
    assert rr4.status_code == 400
