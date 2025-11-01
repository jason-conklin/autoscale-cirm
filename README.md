# AutoScale CIRM (Cloud Infrastructure Resource Monitor)

AutoScale CIRM delivers real-time and predictive insight into your compute fleet. The stack combines a Flask API with a React + Vite dashboard to monitor CPU, memory, and network utilisation, produce short-term forecasts, and raise proactive alerts via Slack or email.

## Architecture
- **Backend (`/api`)** – Flask, APScheduler, SQLAlchemy, SQLite. Pluggable collectors for AWS CloudWatch, GCP Cloud Monitoring, or a psutil simulator. Linear regression forecasts (scikit-learn) predict threshold breaches and persist alerts.
- **Frontend (`/web`)** – React 18 with Vite, Chart.js visualisations, live KPI tiles, forecast cards, and alert history.
- **Storage** – SQLite database (`api/autoscale.db`) created automatically.

## Prerequisites
- Python 3.10+
- Node.js 18+
- (Optional) AWS or GCP credentials if using cloud providers
- Slack webhook and/or SMTP credentials for alert delivery

## Local Development

### Backend
```powershell
cd api
python -m venv .venv
.venv\Scripts\activate        # use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # update provider + credentials
python app.py                 # serves http://localhost:8000
```

### Frontend
```powershell
cd web
npm install
npm run dev                   # serves http://localhost:5173
```

Visit `http://localhost:5173` and ensure `VITE_API_BASE` (defaults to `http://localhost:8000`) points at the backend.

### Docker Compose (optional)
```powershell
docker compose up --build
```

The dashboard becomes available on `http://localhost:5173`; the API on `http://localhost:8000`. Copy `api/.env.example` to `.env` before starting.

## Configuration
All runtime settings live in `api/.env`:

| Category | Keys |
|----------|------|
| Common | `METRICS_PROVIDER`, `POLL_INTERVAL_MINUTES`, `THRESHOLD_CPU`, `THRESHOLD_MEM`, `ALERT_LOOKAHEAD_MIN` |
| AWS | `AWS_REGION`, `AWS_RESOURCE_IDS` |
| GCP | `GCP_PROJECT_ID`, `GCP_INSTANCE_IDS` |
| Alerts | `SLACK_WEBHOOK_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_TO` |

If AWS/GCP variables or credentials are missing, the backend automatically falls back to the local psutil simulator.

## Alerting
- Slack webhook payloads include resource, metric, ETA, and confidence.
- SMTP alerts send an HTML-free email with the same information.
- Trigger a manual alert from the dashboard (`Settings → Send Test Alert`) or via `POST /api/test-alert`.

## API Endpoints
- `GET /api/health` – health probe
- `GET /api/config` – current provider + thresholds
- `GET /api/metrics?resource_id=...&range=1h|6h|24h`
- `GET /api/forecast?resource_id=...`
- `GET /api/alerts?limit=50`
- `POST /api/test-alert`

Use `Invoke-RestMethod` (PowerShell) or `curl` to validate responses.

## Frontend Highlights
- Resource dropdown and range selector (1/6/24h) with live KPIs.
- Three Chart.js panels (CPU, Memory, Network throughput) with auto-refresh.
- Forecast card showing upcoming threshold breaches (confidence + ETA).
- Alert table with status, channel, and message details.
- Settings page exposing read-only configuration and a “Send Test Alert” control.

## Screenshots & Demos
After seeding data (leave the app running in local mode for a few minutes), capture visuals with:
- Windows: `Win + Shift + S`
- macOS: `Cmd + Shift + 4`
- Linux (GNOME): `Shift + Print`

For animated demos, record with OBS Studio or PowerPoint screen recorder and export a GIF. Store assets in `/docs` or a knowledge base (not committed by default).

## Project Structure
```
AutoScale CIRM/
├── api/                # Flask backend
├── web/                # React + Vite frontend
├── docker-compose.yml
├── README.md
└── .gitignore
```

## Testing & Next Steps
- Swap `METRICS_PROVIDER=local` for cloud providers once credentials are populated.
- Extend collectors with additional metrics (disk IO, latency) as needed.
- Integrate authentication or role-based access control for multi-team usage.
- Add integration tests (pytest + requests) for the API endpoints.

Enjoy proactive autoscaling insights with AutoScale CIRM!

