import React from "react";
import { healthz } from "../lib/api";
import { formatErr } from "../lib/format";

export function ConnectionTest() {
  const [msg, setMsg] = React.useState("Checking /healthz...");

  async function run() {
    try {
      const data = await healthz();
      setMsg(`OK: ${JSON.stringify(data)}`);
    } catch (e: any) {
      setMsg(formatErr(e));
    }
  }

  React.useEffect(() => {
    run();
  }, []);

  return (
    <div className="page">
      <h2>Connection Test</h2>
      <button onClick={run}>Re-run</button>
      <pre className="pre">{msg}</pre>
    </div>
  );
}
