from __future__ import annotations

import json
from pathlib import Path

def make_case(case_id: str, habits: list[str], pattern: str) -> dict:
    """
    Generates 7 days of synthetic behavior for a case.

    pattern:
      - "broken_streak": yesterday is missing (simulated no check-in)
      - "consistent": all days logged, high completion, higher mood
      - "low_mood": all days logged, lower mood, mixed completion
    """
    days = []

    base_notes = {
        "broken_streak": [
            "Busy day, slipped a bit.",
            "Felt scattered, hard to start.",
            "Cravings hit late.",
            "Stress spiked, low energy.",
            "Trying to get back on track.",
            "Small win: I showed up briefly.",
            "I want momentum again."
        ],
        "consistent": [
            "Routine felt smooth.",
            "Stayed consistent.",
            "Good focus today.",
            "Solid day, no drama.",
            "Kept the streak alive.",
            "Productive and calm.",
            "Feeling strong."
        ],
        "low_mood": [
            "Brain fog today.",
            "Low energy, but tried.",
            "Mood dipped in afternoon.",
            "Did one small thing.",
            "Still heavy, want something doable.",
            "Slept poorly, trying again.",
            "Slightly better today."
        ],
    }

    base_moods = {
        "broken_streak": [4, 3, 2, 2, 2, 3, 3],
        "consistent":    [4, 4, 5, 4, 4, 4, 5],
        "low_mood":      [2, 2, 2, 3, 2, 2, 3],
    }

    done_targets = {
        "broken_streak": [2, 2, 1, 1, 1, 2, 1],
        "consistent":    [3, 3, 3, 3, 3, 3, 3],
        "low_mood":      [1, 1, 1, 2, 1, 1, 2],
    }

    notes = base_notes[pattern]
    moods = base_moods[pattern]
    targets = done_targets[pattern]

    for i in range(7):
        results = {}
        for h_idx, h in enumerate(habits):
            results[h] = (h_idx < targets[i])

        day_obj = {
            "logged": True,
            "mood": int(moods[i]),
            "note": notes[i],
            "results": results,
        }
        days.append(day_obj)

    if pattern == "broken_streak":
        # Map day[-1] to TODAY, so day[-2] is "yesterday".
        days[-2]["logged"] = False

    return {"case_id": case_id, "habits": habits, "days": days}

def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    out_path = repo_root / "evals" / "sample_histories.json"

    habit_sets = [
        ["Workout", "Read 10 pages", "No sugar"],
        ["Meditate", "Study 45 min", "Drink water"],
        ["Sleep by 11", "Journal", "Walk"],
        ["Stretch", "Plan tomorrow", "No phone in bed"],
        ["Code 30 min", "Protein breakfast", "Outside sunlight"],
    ]

    cases = []

    idx = 1
    for k in range(10):
        cases.append(make_case(f"case_{idx:02d}_broken_streak", habit_sets[k % len(habit_sets)], "broken_streak"))
        idx += 1
    for k in range(10):
        cases.append(make_case(f"case_{idx:02d}_consistent", habit_sets[k % len(habit_sets)], "consistent"))
        idx += 1
    for k in range(10):
        cases.append(make_case(f"case_{idx:02d}_low_mood", habit_sets[k % len(habit_sets)], "low_mood"))
        idx += 1

    out_path.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {out_path}")

if __name__ == "__main__":
    main()
