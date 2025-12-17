import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearToken, getToken } from "../lib/api";

export function NavBar() {
  const nav = useNavigate();
  const [hasToken, setHasToken] = React.useState(!!getToken());

  return (
    <div className="nav">
      <div className="nav-left">
        <strong>MindGarden</strong>
        <Link to="/">Dashboard</Link>
        <Link to="/habits">Habits</Link>
        <Link to="/connect">Connection</Link>
      </div>

      <div className="nav-right">
        <span className="muted">Token: {hasToken ? "set" : "missing"}</span>
        <button
          onClick={() => {
            clearToken();
            setHasToken(false);
            nav("/login");
          }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}
