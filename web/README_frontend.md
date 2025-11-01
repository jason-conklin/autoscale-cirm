# AutoScale CIRM Frontend

React + Vite dashboard for visualising infrastructure metrics, forecasts, and alert history.

## Stack
- React 18, React Router
- Vite dev server
- Chart.js + react-chartjs-2
- Axios API client
- Tailored CSS (no component library dependency)

## Quick Start
```powershell
cd web
npm install
npm run dev              # http://localhost:5173
```

Set `VITE_API_BASE` (optional) to point at the backend API. Default: `http://localhost:8000`.

## Scripts
| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite with hot module replacement |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production bundle |

## Environment Variables
Create `web/.env` if you need to override defaults:
```dotenv
VITE_API_BASE=http://localhost:8000
```

## Project Layout
```
src/
  api/            API helpers
  components/     Reusable UI pieces
  pages/          Dashboard & Settings views
  styles.css      Global styling
```

## Styling
Custom CSS lives in `styles.css`. Adjust colour palette or typography centrally to align with branding.

## Production Build
```powershell
npm run build
npm run preview
```

Serve the `dist/` directory behind any static file server (NGINX, S3 + CloudFront, etc.) and point `VITE_API_BASE` at the deployed API.

