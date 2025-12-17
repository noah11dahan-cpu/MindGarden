import React from "react";
import { apiFetch } from "../lib/api";
import { CONFIG } from "../config";
import { formatErr } from "../lib/format";

type HabitStreak = { habit_id: number; streak: number };

export function InsightsPanel(props: { habitNameById: Record<number, string> }) {
  const [status, setStatus] = React.useState("");
  const [moodAvg7d, setMoodAvg7d] = React.useState<number | null>(null);
  const [streaks, setStreaks] = React.useState<HabitStreak[]>([]);

  async function load() {
    setStatus("Loading insights...");
    try {
      const data = await apiFetch<any>(CONFIG.insights.todayPath);

      const avg = data?.[CONFIG.insights.moodAvg7dField];
      setMoodAvg7d(typeof avg === "number" ? avg : null);

      const hsRaw = data?.[CONFIG.insights.habitStreaksJsonField];
      let habits: HabitStreak[] = [];
      if (typeof hsRaw === "string" && hsRaw.trim()) {
        const parsed = JSON.parse(hsRaw);
        if (Array.isArray(parsed?.habits)) habits = parsed.habits;
      }
      setStreaks(habits);

      setStatus("");
    } catch (e: any) {
      setStatus(formatErr(e));
    }
  }

  React.useEffect(() => {
    load();
  }, []);

  return (
    <div className="card">
      <div className="card-header">
        <h3>Today’s Insights</h3>
        <button onClick={load}>Refresh</button>
      </div>

      {status && <div className="status">{status}</div>}

      <div className="section">
        <div className="label">7-day mood average</div>
        <div className="big">{moodAvg7d ?? "—"}</div>
      </div>

      <div className="section">
        <div className="label">Habit streaks</div>
        {streaks.length === 0 ? (
          <div className="muted">No streak data found yet.</div>
        ) : (
          <div className="list">
            {streaks.map((s, idx) => (
              <div key={idx} className="row between">
                <span>{props.habitNameById[s.habit_id] ?? `Habit ${s.habit_id}`}</span>
                <strong>{s.streak}</strong>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="section">
        <div className="label">Mood chart</div>
        <div className="muted">Placeholder for Day 6 (chart needs a “recent check-ins” endpoint).</div>
      </div>
    </div>
  );
}
