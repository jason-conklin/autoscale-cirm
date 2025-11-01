import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const client = axios.create({
  baseURL,
  timeout: 8000,
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API error:", error);
    return Promise.reject(error);
  },
);

export const fetchHealth = () => client.get("/api/health");
export const fetchConfig = () => client.get("/api/config");
export const fetchMetrics = (params) => client.get("/api/metrics", { params });
export const fetchForecasts = (params) => client.get("/api/forecast", { params });
export const fetchAlerts = (params) => client.get("/api/alerts", { params });
export const triggerTestAlert = () => client.post("/api/test-alert");

