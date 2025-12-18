import React from "react";
import { apiFetch, getAiSuggestion } from "../lib/api";
import { CONFIG } from "../config";
import { todayISO } from "../lib/date";
import { formatErr } from "../lib/format";
import { InsightsPanel } from "../components/InsightsPanel";

type Habit = { id: number; name: string; active: boolean };

export function DashboardPage() {
  const [habits, setHabits] = React.useState<Habit[]>([]);
  const [date, setDate] = React.useState(todayISO());
  const [mood, setMood] = React.useState<number>(5);
  const [note, setNote] = React.useState("");
  const [doneByHabitId, setDoneByHabitId] = React.useState<Record<number, boolean>>({});
  const [status, setStatus] = React.useState("");

  // --- Day 7: AI suggestion UI state (ADD) ---
  const [aiStatus, setAiStatus] = React.useState("");
  const [aiSuggestion, setAiSuggestion] = React.useState<string | null>(null);
  const [aiTone, setAiTone] = React.useState<string | null>(null);

  const habitNameById = React.useMemo(() => {
    const m: Record<number, string> = {};
    for (const h of habits) m[h.id] = h.name;
    return m;
  }, [habits]);

  async function loadHabits() {
    setStatus("Loading habits...");
    try {
      const data = await apiFetch<Habit[]>(CONFIG.habits.listPath);
      const list = Array.isArray(data) ? data : [];
      setHabits(list);

      setDoneByHabitId((prev) => {
        const next: Record<number, boolean> = { ...prev };
        for (const h of list) if (next[h.id] === undefined) next[h.id] = false;
        return next;
      });

      setStatus("");
    } catch (e: any) {
      setStatus(formatErr(e));
    }
  }

  React.useEffect(() => {
    loadHabits();
  }, []);

  function toggle(habitId: number) {
    setDoneByHabitId((prev) => ({ ...prev, [habitId]: !prev[habitId] }));
  }

  async function submitCheckin() {
    setStatus("Submitting check-in...");
    try {
      const habit_results = habits.map((h) => ({
        [CONFIG.checkins.habitIdField]: h.id,
        [CONFIG.checkins.doneField]: !!doneByHabitId[h.id],
      }));

      const payload = {
        date,
        mood,
        note,
        [CONFIG.checkins.habitResultsField]: habit_results,
      };

      await apiFetch(CONFIG.checkins.createPath, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setStatus("✅ Check-in saved. Refresh insights to see updates.");
    } catch (e: any) {
      setStatus(formatErr(e));
    }
  }

  // --- Day 7: AI suggestion fetch (ADD) ---
  async function fetchTinyChallenge() {
    setAiStatus("Thinking...");
    try {
      const data = await getAiSuggestion();
      setAiSuggestion(data.suggestion);
      setAiTone(data.tone);
      setAiStatus("");
    } catch (e: any) {
      setAiStatus(formatErr(e));
    }
  }

  return (
    <div className="page">
      <h2>Dashboard</h2>

      <div className="grid">
        <div className="card">
          <div className="card-header">
            <h3>Daily check-in</h3>
            <button onClick={loadHabits}>Refresh habits</button>
          </div>

          <div className="form">
            <label>
              Date
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </label>

            <label>
              Mood
              <input type="number" value={mood} onChange={(e) => setMood(Number(e.target.value))} />
            </label>

            <label>
              Note
              <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} />
            </label>

            <div>
              <div className="label">Habits</div>
              {habits.length === 0 ? (
                <div className="muted">Create a habit first in Habits.</div>
              ) : (
                <div className="list">
                  {habits.map((h) => (
                    <label key={h.id} className="row">
                      <input
                        type="checkbox"
                        checked={!!doneByHabitId[h.id]}
                        onChange={() => toggle(h.id)}
                      />
                      {h.name}
                    </label>
                  ))}
                </div>
              )}
            </div>

            <button onClick={submitCheckin} disabled={habits.length === 0}>
              Submit check-in
            </button>

            {/* --- Day 7: Tiny challenge button + output (ADD) --- */}
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
              <button type="button" onClick={fetchTinyChallenge}>
                Give me a tiny challenge
              </button>
              <button
                type="button"
                onClick={() => {
                  setAiSuggestion(null);
                  setAiTone(null);
                  setAiStatus("");
                }}
              >
                Clear
              </button>
            </div>

            {aiStatus && <div className="status">{aiStatus}</div>}

            {aiSuggestion && (
              <div className="card" style={{ marginTop: 12 }}>
                <div className="card-header">
                  <h3>Tiny Challenge</h3>
                  <div className="muted" style={{ fontSize: 13 }}>
                    Tone: {aiTone ?? "unknown"}
                  </div>
                </div>
                <div style={{ paddingTop: 8 }}>{aiSuggestion}</div>
              </div>
            )}
          </div>

          {status && <div className="status">{status}</div>}
        </div>

        <InsightsPanel habitNameById={habitNameById} />
      </div>
    </div>
  );
}
