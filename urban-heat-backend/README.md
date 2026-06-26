# Urban Heat Platform — Backend

FastAPI backend for the ISRO Hackathon **AI-Powered Urban Heat Hotspot & Cooling Recommendation Platform**.

Uses **PostgreSQL** for persistent storage, **Isolation Forest** for ML hotspot detection, and live **OpenWeather** + **Google Maps** APIs for any location.

## ML approach

| Technique | Purpose |
|-----------|---------|
| **Isolation Forest** | Unsupervised anomaly detection — flags grid cells that are outliers in temperature, impervious surface, tree cover, and traffic |
| **K-Means clustering** | Groups detected hotspots into spatial intervention zones for city planners |

## Quick start (Docker — recommended)

From `urban-heat-backend`:

```bash
copy .env.example .env
docker compose up --build -d
```

| Service | URL |
|---------|-----|
| API + Swagger | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |
| HTML dashboard | http://localhost:8080 |
| Health check | http://localhost:8000/health |

Useful commands:

```bash
docker compose ps
docker compose logs -f api
docker compose down
docker compose down -v   # also removes database volume
```

Build only the API image:

```bash
docker build -t urban-heat-api:latest .
```

Run API container alone (requires Postgres reachable at `DATABASE_URL`):

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg2://postgres:postgres@host.docker.internal:5432/urban_heat \
  urban-heat-api:latest
```

## Quick start (local Python)

### 1. Start PostgreSQL

```bash
cd urban-heat-backend
docker compose up -d db
```

### 2. Run the API

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

python scripts/seed_demo_data.py
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for Swagger UI.

## API keys

Enter keys in the UI (HTML dashboard or Streamlit sidebar) or in `.env`:

| Key | Required for | Get it |
|-----|--------------|--------|
| `OPENWEATHER_API_KEY` | Live temperature data | https://openweathermap.org/api |
| `GOOGLE_MAPS_API_KEY` | Location search (Geocoding API) | https://console.cloud.google.com/ |
| `MISTRAL_API_KEY` | AI cooling narratives (primary) | https://console.mistral.ai/ |
| `GEMINI_API_KEY` | AI narratives (fallback) | https://aistudio.google.com/ |

Without keys, Bhopal demo data still works from the seeded grid.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/settings` | API key status |
| POST | `/api/v1/settings` | Save API keys (session) |
| POST | `/api/v1/locations/analyze` | Analyze any city — live weather + ML hotspots |
| GET | `/api/v1/hotspots` | Heat map grid cells |
| GET | `/api/v1/analysis/{cell_id}` | Root cause analysis |
| POST | `/api/v1/recommendations` | Cooling recommendations |
| POST | `/api/v1/simulate` | What-if simulator |
| GET | `/api/v1/priority` | Priority ranking |

### Analyze a location

```json
POST /api/v1/locations/analyze
{
  "location_query": "Delhi, India",
  "openweather_api_key": "your-key",
  "google_maps_api_key": "your-key"
}
```

## UIs

**Streamlit**

```bash
streamlit run streamlit_app/app.py
```

**HTML dashboard** — open `urban-heat-dashboard.html` while the API runs on port 8000. Enter API keys in the sidebar, search any city, and click Analyze Location.

## Environment

See `.env.example` for all configuration options.
