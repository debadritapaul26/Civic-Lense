# Civic AI Platform

This workspace contains the active civic-tech application:

- `backend/` — FastAPI, SQLAlchemy, complaint intake, aggregation, and simulation routes.
- `frontend/` — Next.js App Router dashboard with Tailwind CSS and Recharts.
- `seed_data/seed.py` — idempotent demo-data seeder.

## Run the backend

From `civic-ai-platform/backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r ..\requirements.txt
copy ..\.env.example ..\.env
uvicorn main:app --reload
```

The API is available at `http://localhost:8000/api`.

## Seed demo data

With the backend environment active, from `civic-ai-platform`:

```powershell
python seed_data\seed.py
```

## Run the frontend

From `civic-ai-platform/frontend`:

```powershell
npm install
npm run dev
```

Open `http://localhost:3000`.

The complaint and simulation flows require a valid `ANTHROPIC_API_KEY` in
`civic-ai-platform/.env`. The database defaults to SQLite at
`backend/civic.db`, and `TOTAL_BUDGET` is measured in ₹ crore.
