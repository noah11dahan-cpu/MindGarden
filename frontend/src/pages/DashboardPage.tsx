import React from "react";
import {
  apiFetch,
  getAiSuggestion,
  ApiError,
  deepDive,
  exportReflections,
  metricsAnalytics,
  getTier,
} from "../lib/api";
import type { RetrievedReflection } from "../lib/api";
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

  const [aiStatus, setAiStatus] = React.useState("");
  const [aiSuggestion, setAiSuggestion] = React.useState<string | null>(null);
  const [aiTone, setAiTone] = React.useState<string | null>(null);

  // Day 8: RAG memories shown in UI
  const [aiMemories, setAiMemories] = React.useState<RetrievedReflection[]>([]);

  // NEW (Day 11 Premium UI state)
  const [tier, setTier] = React.useState<"free" | "premium">(getTier());
  const [premiumStatus, setPremiumStatus] = React.useState("");
  const [deepDiveTopic, setDeepDiveTopic] = React.useState("sleep");
  const [deepDiveResponse, setDeepDiveResponse] = React.useState<string | null>(null);

  const [exportStatus, setExportStatus] = React.useState("");
  const [exportCount, setExportCount] = React.useState<number | null>(null);

  const [analyticsDays, setAnalyticsDays] = React.useState<number>(7);
  const [analyticsStatus, setAnalyticsStatus] = React.useState("");
  const [analyticsData, setAnalyticsData] = React.useState<any>(null);

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

  // NEW: keep tier synced (even if upgraded in NavBar)
  React.useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === "mg_tier") {
        setTier(e.newValue === "premium" ? "premium" : "free");
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
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

      // Day 8: Extract RAG memories from the AI context (if present)
      const mem = data?.context?.retrieved_reflections;
      setAiMemories(Array.isArray(mem) ? mem : []);

      setAiStatus("");
    } catch (e: any) {
      setAiStatus(formatErr(e));
    }
  }

  // NEW: premium actions
  async function runDeepDive() {
    setPremiumStatus("Running deep dive...");
    setDeepDiveResponse(null);
    try {
      const data = await deepDive(deepDiveTopic);
      setDeepDiveResponse(data.response);
      setPremiumStatus("");
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 403) {
        setPremiumStatus("🔒 Premium feature. Use Upgrade in the nav to unlock.");
      } else {
        setPremiumStatus(formatErr(e));
      }
    }
  }

  async function runExport() {
    setExportStatus("Exporting reflections...");
    setExportCount(null);
    try {
      const data = await exportReflections();
      setExportCount(data.count);
      setExportStatus("");

      // Auto-download JSON (recruiter-friendly demo)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mindgarden_reflections_export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 403) {
        setExportStatus("🔒 Premium feature. Use Upgrade in the nav to unlock export.");
      } else {
        setExportStatus(formatErr(e));
      }
    }
  }

  async function loadAnalytics() {
    setAnalyticsStatus("Loading analytics...");
    setAnalyticsData(null);
    try {
      const data = await metricsAnalytics(analyticsDays);
      setAnalyticsData(data);
      setAnalyticsStatus("");
      // update tier if backend reports it
      const t = data.subscription_tier === "premium" ? "premium" : "free";
      setTier(t);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 403) {
        setAnalyticsStatus("🔒 Premium feature. Free is limited to 30 days.");
      } else {
        setAnalyticsStatus(formatErr(e));
      }
    }
  }

  return (
    <div className="page">
      <h2>Dashboard</h2>

      <div className="muted" style={{ marginBottom: 10 }}>
        Plan: <strong>{tier === "premium" ? "Premium" : "Free"}</strong>
      </div>

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
                  // Day 8: clear memories too
                  setAiMemories([]);
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

                {/* Day 8: RAG memories panel */}
                <div style={{ marginTop: 12 }}>
                  <div className="label">Relevant past notes</div>

                  {aiMemories.length === 0 ? (
                    <div className="muted">
                      No relevant past notes found yet. Add notes to your check-ins to unlock memory.
                    </div>
                  ) : (
                    <div className="list" style={{ marginTop: 6 }}>
                      {aiMemories.slice(0, 5).map((m) => (
                        <div key={m.reflection_id} className="row between" style={{ gap: 10 }}>
                          <div style={{ flex: 1 }}>
                            <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
                              {m.checkin_date}
                            </div>
                            <div>{m.text}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* NEW: Premium panel */}
                <div style={{ marginTop: 14 }}>
                  <div className="label">Premium features</div>

                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 8 }}>
                    <input
                      value={deepDiveTopic}
                      onChange={(e) => setDeepDiveTopic(e.target.value)}
                      placeholder="Deep dive topic (e.g., sleep)"
                      style={{ flex: 1, minWidth: 220 }}
                    />
                    <button type="button" onClick={runDeepDive}>
                      Deep Dive (premium)
                    </button>
                    <button type="button" onClick={runExport}>
                      Export Reflections (premium)
                    </button>
                  </div>

                  {premiumStatus && <div className="status">{premiumStatus}</div>}

                  {exportStatus && <div className="status">{exportStatus}</div>}
                  {exportCount !== null && (
                    <div className="muted" style={{ marginTop: 6 }}>
                      Exported reflections: <strong>{exportCount}</strong> (downloaded as JSON)
                    </div>
                  )}

                  {deepDiveResponse && (
                    <div className="card" style={{ marginTop: 10 }}>
                      <div className="card-header">
                        <h3>Deep Dive</h3>
                        <div className="muted" style={{ fontSize: 13 }}>
                          Topic: {deepDiveTopic || "—"}
                        </div>
                      </div>
                      <div style={{ paddingTop: 8 }}>{deepDiveResponse}</div>
                    </div>
                  )}

                  <div style={{ marginTop: 12 }}>
                    <div className="label">Long-term analytics</div>
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 6, alignItems: "center" }}>
                      <select value={analyticsDays} onChange={(e) => setAnalyticsDays(Number(e.target.value))}>
                        <option value={7}>7 days</option>
                        <option value={30}>30 days</option>
                        <option value={60}>60 days (premium)</option>
                        <option value={90}>90 days (premium)</option>
                      </select>
                      <button type="button" onClick={loadAnalytics}>
                        Load analytics
                      </button>
                    </div>

                    {analyticsStatus && <div className="status">{analyticsStatus}</div>}
                    {analyticsData && (
                      <div className="muted" style={{ marginTop: 6 }}>
                        Window start: {analyticsData.window_start_utc} • Check-ins:{" "}
                        <strong>{analyticsData.checkins_window}</strong> • AI calls:{" "}
                        <strong>{analyticsData.ai_suggestions_count_window}</strong>
                      </div>
                    )}
                  </div>
                </div>
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
