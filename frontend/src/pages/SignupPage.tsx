import React from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup } from "../lib/api";
import { formatErr } from "../lib/format";

export function SignupPage() {
  const nav = useNavigate();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [status, setStatus] = React.useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("Creating account...");
    try {
      await signup(email, password);
      setStatus("✅ Account created. You can log in now.");
      nav("/login", { replace: true });
    } catch (err: any) {
      setStatus(formatErr(err));
    }
  }

  return (
    <div className="center">
      <div className="card" style={{ maxWidth: 520, width: "100%" }}>
        <h2>Sign up</h2>
        <p className="muted">Creates a user via POST /auth/signup.</p>

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

          <button type="submit">Create account</button>
        </form>

        <div className="row" style={{ marginTop: 10 }}>
          <span className="muted">Already have an account?</span>
          <Link to="/login">Login</Link>
        </div>

        {status && <div className="status">{status}</div>}
      </div>
    </div>
  );
}
