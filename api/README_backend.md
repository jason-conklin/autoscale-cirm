# AutoScale CIRM Backend

The backend is a Flask API that ingests infrastructure metrics, forecasts saturation windows, and dispatches alerts. It is production-ready for a lightweight deployment and can operate against AWS CloudWatch, Google Cloud Monitoring, or a fully local simulator (psutil).

## Features
- Metric collectors for AWS EC2, GCP Compute Engine, and local psutil fallback.
- APScheduler job that polls metrics and persists to SQLite.
- Rolling linear-regression forecasts (scikit-learn) that predict CPU/MEM threshold breaches.
- Slack webhook and SMTP email alerts with lookahead rules.
- REST API powering the React dashboard.

## Prerequisites
- Python 3.10+
- (Optional) AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or GCP ADC credentials available on the host.

## Quick Start

```powershell
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # customize as needed
python app.py
```

The API listens on `http://localhost:8000` by default.

## Environment Variables
All configuration lives in `.env`. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `METRICS_PROVIDER` | `local`, `aws`, or `gcp` | `local` |
| `POLL_INTERVAL_MINUTES` | Scheduler interval in minutes | `5` |
| `THRESHOLD_CPU`, `THRESHOLD_MEM` | Forecast thresholds (%) | `90` |
| `ALERT_LOOKAHEAD_MIN` | Minutes before breach to alert | `60` |
| `AWS_REGION`, `AWS_RESOURCE_IDS` | AWS provider settings | — |
| `GCP_PROJECT_ID`, `GCP_INSTANCE_IDS` | GCP provider settings | — |
| `SLACK_WEBHOOK_URL` | Slack alerts (optional) | — |
| `SMTP_*` | SMTP email settings (optional) | — |

## Key Commands
- `python app.py` – run the API with scheduler
- `pytest` – optional test harness (add if needed)

## API Cheatsheet

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/health` | Liveness probe |
| GET | `/api/config` | Active provider & thresholds |
| GET | `/api/metrics?resource_id=...&range=1h|6h|24h` | Time-series data |
| GET | `/api/forecast?resource_id=...` | Predicted saturation windows |
| GET | `/api/alerts?limit=50` | Recent alert history |
| POST | `/api/test-alert` | Emit a test alert |

### Example Requests
Fetch metrics for the default resource (Windows PowerShell):
```powershell
Invoke-RestMethod http://localhost:8000/api/metrics
```

Trigger a test alert (requires Slack or SMTP configured):
```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/test-alert
```

## Local Simulation Tips
- Leave `METRICS_PROVIDER=local` to use psutil data with simulated multi-resource variation.
- Scheduler seeds the database automatically on startup; leave it running for a few minutes to accumulate data for forecasting.

## Database
- SQLite file: `api/autoscale.db`
- Tables: `metrics`, `forecasts`, `alerts`
- Schema is managed via SQLAlchemy models (`models.py`).

## Troubleshooting
- **Scheduler not running**: Ensure the process is the reloader child (`WERKZEUG_RUN_MAIN=true`) or run `FLASK_DEBUG=0`.
- **No forecasts**: Collect at least ~5 datapoints (keep the service running) and verify thresholds aren't already exceeded.
- **Alerts missing**: Check `.env` for Slack/SMTP configuration and monitor logs for delivery errors.

