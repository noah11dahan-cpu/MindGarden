import React from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../lib/api";
import { formatErr } from "../lib/format";

export function LoginPage() {
  const nav = useNavigate();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [status, setStatus] = React.useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("Logging in...");
    try {
      await login(email, password);
      nav("/", { replace: true });
    } catch (err: any) {
      setStatus(formatErr(err));
    }
  }

  return (
    <div className="center">
      <div className="card" style={{ maxWidth: 520, width: "100%" }}>
        <h2>Login</h2>
        <p className="muted">Uses POST /auth/login and stores JWT (access_token).</p>

        <form onSubmit={onSubmit} className="form">
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="password"
            />
          </label>

          <button type="submit">Login</button>
        </form>
        <div className="row" style={{ marginTop: 10 }}>
            <span className="muted">No account?</span>
            <Link to="/signup">Create one</Link>
        </div>

        {status && <div className="status">{status}</div>}
      </div>
    </div>
  );
}
