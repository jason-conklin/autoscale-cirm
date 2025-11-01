import { useEffect, useState } from "react";

import { fetchConfig, triggerTestAlert } from "../api/client.js";

const Settings = () => {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const { data } = await fetchConfig();
        setConfig(data);
      } catch (err) {
        console.error(err);
        setStatus({ type: "error", message: "Failed to load configuration." });
      }
    };
    loadConfig();
  }, []);

  const handleTestAlert = async () => {
    setLoading(true);
    setStatus(null);
    try {
      const { data } = await triggerTestAlert();
      setStatus({ type: "success", message: `Test alert triggered via: ${data.channels.join(", ")}` });
    } catch (err) {
      console.error(err);
      setStatus({ type: "error", message: "Unable to send test alert. Check server logs." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-grid">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Active Configuration</span>
        </div>
        {config ? (
          <div style={{ display: "grid", gap: "1rem" }}>
            <ConfigRow label="Provider" value={config.provider} />
            <ConfigRow label="Resource IDs" value={config.resource_ids?.join(", ") || "—"} />
            <ConfigRow label="Poll Interval (min)" value={config.poll_interval_minutes} />
            <ConfigRow label="CPU Threshold (%)" value={config.threshold_cpu} />
            <ConfigRow label="Memory Threshold (%)" value={config.threshold_mem} />
            <ConfigRow label="Alert Lookahead (min)" value={config.alert_lookahead_min} />
            <ConfigRow
              label="Alert Channels"
              value={config.available_alert_channels?.length ? config.available_alert_channels.join(", ") : "None"}
            />
          </div>
        ) : (
          <div className="empty-state">Loading configuration…</div>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Test Alert</span>
        </div>
        <p>
          Ensure Slack and/or SMTP are configured in <code>.env</code>, then trigger a test alert to confirm delivery.
        </p>
        <button
          type="button"
          onClick={handleTestAlert}
          className="nav-link active"
          style={{ width: "fit-content", marginTop: "1rem" }}
          disabled={loading}
        >
          {loading ? "Sending…" : "Send Test Alert"}
        </button>
        {status ? (
          <div className="toast" style={{ backgroundColor: status.type === "error" ? "rgba(248, 113, 113, 0.15)" : undefined }}>
            {status.message}
          </div>
        ) : null}
      </div>
    </div>
  );
};

const ConfigRow = ({ label, value }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
    <span style={{ fontWeight: 600, color: "#475569" }}>{label}</span>
    <span style={{ color: "#1f2937" }}>{value}</span>
  </div>
);

export default Settings;

