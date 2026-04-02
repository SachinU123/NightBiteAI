# NightBite AI — Backend

FastAPI + PostgreSQL backend for the NightBite AI mobile app.

## Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 14+

### 2. Create PostgreSQL Database

```sql
CREATE USER nightbite_user WITH PASSWORD 'nightbite_pass';
CREATE DATABASE nightbite_db OWNER nightbite_user;
GRANT ALL PRIVILEGES ON DATABASE nightbite_db TO nightbite_user;
```

### 3. Setup Python Environment

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update values if needed.

### 5. Run Migrations

```bash
alembic upgrade head
```

### 6. Seed Demo Data (Optional)

```bash
python seed.py
```

### 7. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

## API Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | Login, get JWT |
| GET | /api/v1/auth/me | Current user |
| POST | /api/v1/devices/register | Register device |
| POST | /api/v1/devices/notification-status | Update listener status |
| POST | /api/v1/food-events/manual-entry | Analyze manual food entry |
| POST | /api/v1/food-events/notification-capture | Analyze notification capture |
| GET | /api/v1/food-events/latest | Latest analyzed event |
| GET | /api/v1/food-events/history | Paginated history |
| GET | /api/v1/user-insights | Weekly personal insights |
| GET | /api/v1/analytics/heatmap | Heatmap aggregates |
| GET | /api/v1/analytics/dashboard-summary | Admin dashboard stats |

## Architecture

```
app/
├── api/           # FastAPI routers (auth, devices, food_events, insights, analytics)
├── core/          # Config, security, dependency injection
├── db/            # SQLAlchemy session + base
├── models/        # SQLAlchemy ORM models (all 8 tables)
├── schemas/       # Pydantic request/response contracts
├── services/
│   ├── nlp_service.py          # spaCy + regex food text analysis
│   ├── risk_engine.py          # Deterministic risk scoring (BaseRisk × Time × Behavior)
│   ├── nudge_generator.py      # Template-based smart nudge generation
│   └── ingestion_adapters.py   # ManualEntryAdapter + NotificationCaptureAdapter
└── main.py        # FastAPI app factory
```

## Demo Credentials (after seeding)

| Name | Email | Password |
|------|-------|----------|
| Priya Sharma | demo1@nightbite.ai | Demo@1234 |
| Rahul Verma | demo2@nightbite.ai | Demo@1234 |
| Admin User | admin@nightbite.ai | Admin@1234 |
