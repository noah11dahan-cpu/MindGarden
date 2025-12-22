import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearToken, getToken, getTier, upgrade, metricsAnalytics } from "../lib/api";
import { formatErr } from "../lib/format";

export function NavBar() {
  const nav = useNavigate();
  const [hasToken, setHasToken] = React.useState(!!getToken());

  // NEW: Tier + upgrade status
  const [tier, setTier] = React.useState(getTier());
  const [tierStatus, setTierStatus] = React.useState("");

  // NEW: on mount, if logged in, fetch a small analytics window to sync tier
  React.useEffect(() => {
    (async () => {
      if (!getToken()) return;
      try {
        const data = await metricsAnalytics(7);
        const t = data.subscription_tier === "premium" ? "premium" : "free";
        setTier(t);
      } catch {
        // ignore
      }
    })();
  }, [hasToken]);

  async function handleUpgrade() {
    setTierStatus("Upgrading...");
    try {
      const data = await upgrade();
      setTier(data.subscription_tier);
      setTierStatus("✅ Premium enabled (placeholder).");
    } catch (e: any) {
      setTierStatus(formatErr(e));
    }
  }

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

        {/* NEW: Tier badge + upgrade */}
        {hasToken && (
          <span className="muted">
            Plan: <strong>{tier === "premium" ? "Premium" : "Free"}</strong>
          </span>
        )}
        {hasToken && tier !== "premium" && (
          <button type="button" onClick={handleUpgrade}>
            Upgrade
          </button>
        )}
        {hasToken && tierStatus && <span className="muted">{tierStatus}</span>}

        <button
          onClick={() => {
            clearToken();
            setHasToken(false);
            setTier("free");
            setTierStatus("");
            nav("/login");
          }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}
