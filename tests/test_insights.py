# tests/test_insights.py
import json
import random
import string
from datetime import date, timedelta

import pytest


def _rand_email() -> str:
    suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    return f"insights_{suffix}@example.com"


def _get_openapi(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, f"Expected /openapi.json to work, got {resp.status_code}: {resp.text}"
    return resp.json()


def _find_path(openapi, *, contains: str, method: str):
    """
    Find the first OpenAPI path that contains `contains` in the URL path,
    and has the given HTTP method.
    """
    contains = contains.lower()
    for path, methods in openapi.get("paths", {}).items():
        if contains in path.lower() and method.lower() in methods:
            return path
    return None


def _signup_and_login(client):
    """
    Does NOT assume exact auth route paths.
    It discovers signup/login paths from OpenAPI, then attempts:
      - signup with {"email","password"}
      - login with {"email","password"}
    Returns: (headers_dict_or_empty, user_json_or_none)
    """
    openapi = _get_openapi(client)

    signup_path = _find_path(openapi, contains="signup", method="post")
    login_path = _find_path(openapi, contains="login", method="post")

    if not signup_path or not login_path:
        # If your project doesn't expose auth in OpenAPI, we can't authenticate here.
        return {}, None

    email = _rand_email()
    password = "strongpassword123"

    signup_resp = client.post(signup_path, json={"email": email, "password": password})
    assert signup_resp.status_code in (200, 201), f"Signup failed: {signup_resp.status_code} {signup_resp.text}"

    login_resp = client.post(login_path, json={"email": email, "password": password})
    assert login_resp.status_code == 200, f"Login failed: {login_resp.status_code} {login_resp.text}"

    data = login_resp.json()
    # Try common token keys without assuming which one you used.
    token = data.get("access_token") or data.get("token") or data.get("jwt") or data.get("bearer")
    if not token:
        # If your login returns something else, we can't set Authorization header.
        return {}, None

    return {"Authorization": f"Bearer {token}"}, data


def _create_habit(client, headers, name: str):
    resp = client.post("/habits", json={"name": name}, headers=headers)
    assert resp.status_code == 200, f"Create habit failed: {resp.status_code} {resp.text}"
    return resp.json()


def _checkins_post_payload(date_str: str, mood: int, note: str, habit_done_map: dict[int, bool]):
    """
    Builds the most likely payload shape for your Day 4 schema:
      {
        "date": "YYYY-MM-DD",
        "mood": <int>,
        "note": <str>,
        "habit_results": [{"habit_id": <int>, "done": <bool>}, ...]
      }

    This matches your SQLAlchemy relationship name `habit_results`.
    """
    return {
        "date": date_str,
        "mood": mood,
        "note": note,
        "habit_results": [{"habit_id": hid, "done": bool(done)} for hid, done in habit_done_map.items()],
    }


def _post_checkin(client, headers, payload):
    resp = client.post("/checkins", json=payload, headers=headers)
    return resp


def test_insights_today_mvp(client):
    """
    Integration test for Day 5:
      - create user (if auth exists)
      - create 2 habits
      - create 3 consecutive daily check-ins ending today
      - GET /insights/today
      - verify mood_avg_7d and streaks reflect raw check-ins
    """
    headers, _ = _signup_and_login(client)

    habit_a = _create_habit(client, headers, "Read 10 minutes")
    habit_b = _create_habit(client, headers, "Walk 15 minutes")

    habit_a_id = habit_a.get("id")
    habit_b_id = habit_b.get("id")
    assert isinstance(habit_a_id, int) and isinstance(habit_b_id, int), f"Unexpected habit JSON: {habit_a} {habit_b}"

    today = date.today()
    dates = [today, today - timedelta(days=1), today - timedelta(days=2)]

    # IMPORTANT: mood must be between 1 and 5 (your API validation enforces this)
    moods_by_day = {
        dates[0]: 5,
        dates[1]: 3,
        dates[2]: 4,
    }

    results_by_day = {
        dates[0]: {habit_a_id: True, habit_b_id: True},
        dates[1]: {habit_a_id: True, habit_b_id: False},
        dates[2]: {habit_a_id: True, habit_b_id: True},
    }

    successful_days = []

    for d in dates:
        payload = _checkins_post_payload(
            date_str=d.isoformat(),
            mood=moods_by_day[d],
            note=f"checkin {d.isoformat()}",
            habit_done_map=results_by_day[d],
        )
        resp = _post_checkin(client, headers, payload)

        if resp.status_code == 200:
            successful_days.append(d)
            continue

        if d != today:
            break

        assert False, f"Posting today's check-in failed: {resp.status_code} {resp.text}"

    insights_resp = client.get("/insights/today", headers=headers)
    assert insights_resp.status_code == 200, f"/insights/today failed: {insights_resp.status_code} {insights_resp.text}"

    insights = insights_resp.json()

    assert "mood_avg_7d" in insights, f"Missing mood_avg_7d in response: {insights}"
    assert "habit_streaks_json" in insights, f"Missing habit_streaks_json in response: {insights}"
    assert "date" in insights, f"Missing date in response: {insights}"

    expected_moods = [moods_by_day[d] for d in successful_days if (today - timedelta(days=6)) <= d <= today]
    if expected_moods:
        expected_avg = sum(expected_moods) / float(len(expected_moods))
        assert insights["mood_avg_7d"] == pytest.approx(expected_avg), (
            f"Expected mood_avg_7d≈{expected_avg}, got {insights['mood_avg_7d']}. "
            f"Successful days: {successful_days}"
        )
    else:
        assert insights["mood_avg_7d"] is None, f"Expected mood_avg_7d None when no check-ins exist, got {insights['mood_avg_7d']}"

    try:
        streaks_payload = json.loads(insights["habit_streaks_json"] or "{}")
    except json.JSONDecodeError as e:
        assert False, f"habit_streaks_json is not valid JSON: {insights['habit_streaks_json']} ({e})"

    habits_list = streaks_payload.get("habits")
    assert isinstance(habits_list, list), f"Expected habit_streaks_json to contain 'habits' list, got: {streaks_payload}"

    streak_map = {}
    for item in habits_list:
        if isinstance(item, dict) and "habit_id" in item and "streak" in item:
            streak_map[int(item["habit_id"])] = int(item["streak"])

    assert habit_a_id in streak_map and habit_b_id in streak_map, (
        f"Missing habit ids in streaks. Expected {habit_a_id},{habit_b_id}. Got: {streak_map}"
    )

    if len(successful_days) >= 3 and successful_days[0] == today:
        assert streak_map[habit_a_id] == 3, f"Expected habit A streak 3, got {streak_map[habit_a_id]}"
        assert streak_map[habit_b_id] == 1, f"Expected habit B streak 1, got {streak_map[habit_b_id]}"
    else:
        expected_a = 1 if results_by_day[today][habit_a_id] else 0
        expected_b = 1 if results_by_day[today][habit_b_id] else 0
        assert streak_map[habit_a_id] == expected_a, f"Expected habit A streak {expected_a}, got {streak_map[habit_a_id]}"
        assert streak_map[habit_b_id] == expected_b, f"Expected habit B streak {expected_b}, got {streak_map[habit_b_id]}"
