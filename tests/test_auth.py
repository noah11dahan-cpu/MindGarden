# tests/test_auth.py
import uuid


def test_signup_and_login(client):
    # Use a unique email each run so the first signup doesn't collide
    unique_email = f"auth_test_{uuid.uuid4().hex}@example.com"

    payload = {
        "email": unique_email,
        "password": "strongpassword123"
    }

    # 1) Signup
    resp_signup = client.post("/auth/signup", json=payload)
    assert resp_signup.status_code == 200
    data = resp_signup.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # 2) Login
    resp_login = client.post("/auth/login", json=payload)
    assert resp_login.status_code == 200
    data_login = resp_login.json()
    assert "access_token" in data_login
    assert data_login["token_type"] == "bearer"

    # 3) Duplicate signup with the same ema
