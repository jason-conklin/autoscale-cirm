import { useEffect, useMemo, useState } from "react";
import { formatDistanceToNow } from "date-fns";

import AlertList from "../components/AlertList.jsx";
import ForecastCard from "../components/ForecastCard.jsx";
import KPI from "../components/KPI.jsx";
import MetricChart from "../components/MetricChart.jsx";
import { fetchAlerts, fetchConfig, fetchForecasts, fetchMetrics } from "../api/client.js";

const RANGE_OPTIONS = [
  { value: "1h", label: "Last 1h" },
  { value: "6h", label: "Last 6h" },
  { value: "24h", label: "Last 24h" },
];

const Dashboard = () => {
  const [config, setConfig] = useState(null);
  const [resourceId, setResourceId] = useState("");
  const [range, setRange] = useState("6h");
  const [metrics, setMetrics] = useState([]);
  const [availableResources, setAvailableResources] = useState([]);
  const [latest, setLatest] = useState(null);
  const [forecasts, setForecasts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const { data } = await fetchConfig();
        setConfig(data);
        setResourceId(data.resource_ids?.[0] || "");
      } catch (err) {
        console.error(err);
        setError("Unable to load configuration from API.");
      }
    };
    loadConfig();
  }, []);

  useEffect(() => {
    if (!resourceId) {
      return;
    }

    let cancelled = false;

    const loadData = async (silent = false) => {
      if (!silent) {
        setLoading(true);
      }
      try {
        const [metricsResponse, forecastResponse, alertsResponse] = await Promise.all([
          fetchMetrics({ resource_id: resourceId, range }),
          fetchForecasts({ resource_id: resourceId }),
          fetchAlerts({ limit: 20 }),
        ]);
        if (cancelled) return;

        setMetrics(metricsResponse.data.metrics || []);
        setAvailableResources(metricsResponse.data.available_resources || []);
        setLatest(metricsResponse.data.latest || null);
        setForecasts(forecastResponse.data.forecasts || []);
        setAlerts(alertsResponse.data.alerts || []);
        setError(null);
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError("Failed to load dashboard data.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadData();
    const interval = setInterval(() => loadData(true), 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [resourceId, range]);

  const cpuSeries = useMemo(
    () => metrics.map((item) => ({ timestamp: item.timestamp, value: item.cpu_pct ?? 0 })),
    [metrics],
  );
  const memSeries = useMemo(
    () => metrics.map((item) => ({ timestamp: item.timestamp, value: item.mem_pct ?? 0 })),
    [metrics],
  );
  const netSeries = useMemo(
    () =>
      metrics.map((item) => ({
        timestamp: item.timestamp,
        value: (item.net_in_kbps ?? 0) + (item.net_out_kbps ?? 0),
      })),
    [metrics],
  );

  const latestTimestamp = latest?.timestamp ? formatDistanceToNow(new Date(latest.timestamp), { addSuffix: true }) : "—";
  const latestCpu = latest?.cpu_pct != null ? `${latest.cpu_pct.toFixed(1)}%` : "—";
  const latestMem = latest?.mem_pct != null ? `${latest.mem_pct.toFixed(1)}%` : "—";
  const latestNet = latest
    ? `${(((latest.net_in_kbps ?? 0) + (latest.net_out_kbps ?? 0))).toFixed(1)} kbps`
    : "—";

  const computeTrend = (series) => {
    if (series.length < 2) return null;
    const penultimate = series[series.length - 2].value;
    const latestValue = series[series.length - 1].value;
    const delta = latestValue - penultimate;
    if (Math.abs(delta) < 0.5) return "Holding steady";
    return delta > 0 ? `Up ${delta.toFixed(1)} (last sample)` : `Down ${Math.abs(delta).toFixed(1)} (last sample)`;
  };

  return (
    <div className="dashboard-grid">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Resource</span>
          <select className="select" value={resourceId} onChange={(event) => setResourceId(event.target.value)}>
            {availableResources.length
              ? availableResources.map((resource) => (
                  <option key={resource} value={resource}>
                    {resource}
                  </option>
                ))
              : config?.resource_ids?.map((resource) => (
                  <option key={resource} value={resource}>
                    {resource}
                  </option>
                ))}
          </select>
        </div>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setRange(option.value)}
              className={range === option.value ? "nav-link active" : "nav-link"}
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="kpi-grid" style={{ marginTop: "1.5rem" }}>
          <KPI label="CPU Utilisation" value={latestCpu} trend={computeTrend(cpuSeries)} />
          <KPI label="Memory Utilisation" value={latestMem} trend={computeTrend(memSeries)} />
          <KPI label="Network Throughput" value={latestNet} trend={computeTrend(netSeries)} />
        </div>
        <div style={{ marginTop: "1.5rem", color: "#64748b", fontSize: "0.9rem" }}>
          Last sample {latestTimestamp}. Auto-refresh every 30 seconds.
        </div>
      </div>

      {error ? (
        <div className="panel">
          <div className="panel-title">Error</div>
          <div className="empty-state">{error}</div>
        </div>
      ) : null}

      <div className="chart-grid">
        <MetricChart title="CPU %" points={cpuSeries} metricKey="cpu" />
        <MetricChart title="Memory %" points={memSeries} metricKey="mem" />
        <MetricChart title="Network kbps" points={netSeries} metricKey="net" />
      </div>

      <ForecastCard forecasts={forecasts} />

      <AlertList alerts={alerts} />
    </div>
  );
};

export default Dashboard;

