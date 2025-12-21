from __future__ import annotations

import csv
import json
import os
import time
import uuid
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx

SENTENCE_END_RE = re.compile(r"[.!?]+")

def count_sentences(text: str) -> int:
    parts = [p.strip() for p in SENTENCE_END_RE.split(text or "") if p.strip()]
    return len(parts)

def tone_score(tone: str) -> int:
    table = {"gentle": 1, "neutral": 2, "pushy": 3}
    return table.get((tone or "").strip().lower(), 0)

def context_use_ok(suggestion: str, ctx: Dict[str, Any]) -> bool:
    s = (suggestion or "").lower()

    streak_broken = bool(ctx.get("streak_broken"))
    mood_avg = ctx.get("mood_avg_7d")
    done_rate = ctx.get("habit_done_rate_7d")
    days_with = ctx.get("days_with_checkins")

    if not days_with:
        return any(k in s for k in ["start", "tiny", "2-minute", "2 minute", "show up"])

    if streak_broken:
        return any(k in s for k in ["streak", "restart", "start again", "reset", "small", "tiny"])

    try:
        if mood_avg is not None and float(mood_avg) <= 2.5:
            return any(k in s for k in ["reset", "walk", "water", "5-minute", "5 minute", "hardest"])
    except Exception:
        pass

    try:
        if done_rate is not None and float(done_rate) < 0.5:
            return any(k in s for k in ["consistency", "one habit", "optional", "quick win"])
    except Exception:
        pass

    return any(k in s for k in ["10", "increase", "level up", "stretch", "consistent"])

def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def map_days_to_last_week(days: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    today = date.today()
    n = len(days)
    start = today - timedelta(days=n - 1)
    out = []
    for i, d in enumerate(days):
        dte = start + timedelta(days=i)
        out.append((dte.isoformat(), d))
    return out

def request_with_retry(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
    retries: int = 4,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.request(method, path, json=json_body, headers=headers)
            return resp
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last_exc = e
            sleep_s = min(2 ** (attempt - 1), 8)
            print(f"[retry {attempt}/{retries}] {method} {client.base_url}{path} -> {type(e).__name__} (sleep {sleep_s}s)")
            time.sleep(sleep_s)
    assert last_exc is not None
    raise last_exc

def seed_case(base_url: str, case: Dict[str, Any], mode_tag: str) -> Dict[str, Any]:
    timeout = httpx.Timeout(60.0, connect=15.0)  # ✅ longer timeout
    client = httpx.Client(base_url=base_url, timeout=timeout)

    suffix = uuid.uuid4().hex[:10]
    email = f"{case['case_id']}.{mode_tag}.{suffix}@example.com"
    password = "strongpassword123"

    # signup
    r = request_with_retry(client, "POST", "/auth/signup", json_body={"email": email, "password": password})
    r.raise_for_status()
    token = r.json()["access_token"]

    # create habits
    habit_id_by_name: Dict[str, int] = {}
    for h in case.get("habits", []):
        rr = request_with_retry(client, "POST", "/habits", json_body={"name": h}, headers=auth_headers(token))
        rr.raise_for_status()
        habit_id_by_name[h] = rr.json()["id"]

    # post checkins
    mapped = map_days_to_last_week(case.get("days", []))
    for iso_date, d in mapped:
        if d.get("logged", True) is False:
            continue

        mood = int(d["mood"])
        note = d.get("note", "")

        results_obj = d.get("results") or {}
        habit_results = []
        for habit_name, habit_id in habit_id_by_name.items():
            done = bool(results_obj.get(habit_name, False))
            habit_results.append({"habit_id": habit_id, "done": done})

        payload = {
            "date": iso_date,
            "mood": mood,
            "note": note,
            "habit_results": habit_results,
        }

        rc = request_with_retry(client, "POST", "/checkins", json_body=payload, headers=auth_headers(token))
        rc.raise_for_status()

    # call AI suggestions + latency
    t0 = time.perf_counter()
    ai = request_with_retry(client, "GET", "/ai/suggestions", headers=auth_headers(token))
    dt_ms = (time.perf_counter() - t0) * 1000.0
    ai.raise_for_status()

    data = ai.json()
    data["_latency_ms"] = round(dt_ms, 2)
    data["_email"] = email
    return data

def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    samples_path = repo_root / "evals" / "sample_histories.json"
    out_dir = repo_root / "evals" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "ai_suggestions_eval_compare.csv"

    RULES_BASE_URL = os.getenv("RULES_BASE_URL", "http://127.0.0.1:8001")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:8002")
    LIMIT = int(os.getenv("EVAL_LIMIT", "0"))  # 0 = no limit

    cases: List[Dict[str, Any]] = json.loads(samples_path.read_text(encoding="utf-8"))
    if LIMIT > 0:
        cases = cases[:LIMIT]

    # write incrementally so file exists even if later cases fail
    fieldnames = [
        "case_id",
        "rules_tone","rules_tone_score","rules_sentences","rules_length_ok","rules_context_use_ok","rules_latency_ms","rules_suggestion","rules_context_json",
        "ollama_tone","ollama_tone_score","ollama_sentences","ollama_length_ok","ollama_context_use_ok","ollama_latency_ms","ollama_suggestion","ollama_context_json",
        "changed_by_ollama",
        "error",
    ]

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        ok = 0
        for case in cases:
            case_id = case.get("case_id", "")
            row = {k: "" for k in fieldnames}
            row["case_id"] = case_id

            try:
                rules = seed_case(RULES_BASE_URL, case, "rules")
                rules_s = rules.get("suggestion", "")
                rules_t = rules.get("tone", "")
                rules_ctx = rules.get("context") or {}

                oll = seed_case(OLLAMA_BASE_URL, case, "ollama")
                oll_s = oll.get("suggestion", "")
                oll_t = oll.get("tone", "")
                oll_ctx = oll.get("context") or {}

                rules_sent = count_sentences(rules_s)
                oll_sent = count_sentences(oll_s)

                row.update({
                    "rules_tone": rules_t,
                    "rules_tone_score": tone_score(rules_t),
                    "rules_sentences": rules_sent,
                    "rules_length_ok": int(rules_sent <= 2),
                    "rules_context_use_ok": int(context_use_ok(rules_s, rules_ctx)),
                    "rules_latency_ms": rules.get("_latency_ms", ""),
                    "rules_suggestion": rules_s,
                    "rules_context_json": json.dumps(rules_ctx, ensure_ascii=False),

                    "ollama_tone": oll_t,
                    "ollama_tone_score": tone_score(oll_t),
                    "ollama_sentences": oll_sent,
                    "ollama_length_ok": int(oll_sent <= 2),
                    "ollama_context_use_ok": int(context_use_ok(oll_s, oll_ctx)),
                    "ollama_latency_ms": oll.get("_latency_ms", ""),
                    "ollama_suggestion": oll_s,
                    "ollama_context_json": json.dumps(oll_ctx, ensure_ascii=False),

                    "changed_by_ollama": int((rules_s or "").strip() != (oll_s or "").strip()),
                })

                ok += 1
                print(f"OK {case_id} | changed={row['changed_by_ollama']}")
            except Exception as e:
                row["error"] = f"{type(e).__name__}: {e}"
                print(f"FAIL {case_id} -> {row['error']}")

            w.writerow(row)
            f.flush()

    print(f"\nWrote: {out_csv} (rows: {len(cases)})")

if __name__ == "__main__":
    main()
