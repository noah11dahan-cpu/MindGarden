import React from "react";
import { apiFetch } from "../lib/api";
import { CONFIG } from "../config";
import { formatErr } from "../lib/format";

type Habit = { id: number; name: string; active: boolean };

export function HabitsPage() {
  const [habits, setHabits] = React.useState<Habit[]>([]);
  const [name, setName] = React.useState("");
  const [status, setStatus] = React.useState("");

  async function load() {
    setStatus("Loading habits...");
    try {
      const data = await apiFetch<Habit[]>(CONFIG.habits.listPath);
      setHabits(Array.isArray(data) ? data : []);
      setStatus("");
    } catch (e: any) {
      setStatus(formatErr(e));
    }
  }

  async function createHabit() {
    setStatus("Creating habit...");
    try {
      await apiFetch(CONFIG.habits.createPath, {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setName("");
      await load();
    } catch (e: any) {
      setStatus(formatErr(e));
    }
  }

  async function deleteHabit(id: number) {
    setStatus("Deleting habit...");
    try {
      const path = CONFIG.habits.deletePathTemplate.replace("{id}", String(id));
      await apiFetch(path, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setStatus(formatErr(e));
    }
  }

  React.useEffect(() => {
    load();
  }, []);

  return (
    <div className="page">
      <h2>Habits</h2>

      <div className="row">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Habit name" />
        <button onClick={createHabit} disabled={!name.trim()}>
          Add
        </button>
        <button onClick={load}>Refresh</button>
      </div>

      {status && <div className="status">{status}</div>}

      <div className="card">
        {habits.length === 0 ? (
          <div className="muted">No habits yet.</div>
        ) : (
          habits.map((h) => (
            <div key={h.id} className="row between">
              <div>
                <strong>{h.name}</strong>
                <div className="muted">id: {h.id} · active: {String(h.active)}</div>
              </div>
              <button onClick={() => deleteHabit(h.id)}>Delete</button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
