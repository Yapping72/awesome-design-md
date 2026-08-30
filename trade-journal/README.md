# Trade Journal

A self-hosted trade journal that imports Interactive Brokers Activity
Statement CSV exports and turns them into a realized P&L journal: summary
stats, a calendar heatmap of daily P&L, and P&L aggregated by day, week, or
month.

Stack: **React + TypeScript** (Vite) frontend, **FastAPI** backend,
**PostgreSQL** storage (schema managed by **Alembic**), all containerized
with **Docker Compose**.

See **[SPEC.md](./SPEC.md)** for the full current feature list, data model,
API reference, and the enhancement backlog — this README covers setup and a
few cross-cutting design decisions. SPEC.md is the living document; this
README isn't duplicated there to avoid the two drifting out of sync.

## Getting an IBKR-compatible export

In IBKR Client Portal or TWS:

1. **Reports / Statements → Activity Statement**
2. Choose a date range, format **CSV**
3. Make sure the **Trades** section is included
4. Download and upload the `.csv` file directly — no conversion needed

The parser (`backend/app/parsers/ibkr.py`) reads IBKR's multi-section
Activity Statement CSV format and extracts only the `Trades` section.

## Running with Docker

```bash
cd trade-journal
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (docs at `/docs`)
- Postgres: localhost:5432 (`journal` / `journal` / `trade_journal`)

The database schema is brought up to date automatically on backend startup
(`alembic upgrade head` runs in the app's lifespan handler) — no manual
migration step needed to get a fresh container running.

## Local development (without Docker)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg2://journal:journal@localhost:5432/trade_journal
uvicorn app.main:app --reload
```

Run tests: `pytest`

**Database migrations**

Schema changes go through Alembic, not `Base.metadata.create_all`:

```bash
# after changing a model in app/models.py
alembic revision --autogenerate -m "describe the change"
# review the generated file in alembic/versions/, then:
alembic upgrade head
```

`alembic/env.py` reads the same `DATABASE_URL` env var as the app, so no
separate configuration is needed. The app also runs `alembic upgrade head`
itself on startup, so applying a new migration to a running deployment is
just restarting the backend container after the migration file is merged.

**Frontend**

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

## API

Full endpoint reference is in [SPEC.md § API reference](./SPEC.md#5-api-reference)
— kept there rather than here so it's only ever accurate in one place. The
short version: everything is under `/api/`, with interactive docs (and the
canonical, always-current schema) at `/docs` on the running backend.

## Design notes

- **Why not FIFO ourselves?** IBKR already computes realized P/L per closing
  fill using its own cost-basis method. Re-deriving it client-side risks
  drifting from what the broker (and the user's tax reporting) shows.
  Instead, each fill keeps IBKR's `Realized P/L` (0 on opens, populated on
  closes) plus its own commission, and every aggregate is `sum(realized_pnl +
  commission)` grouped by day/week/month.
- **Idempotent imports**: each fill gets a stable id hashed from
  account/symbol/timestamp/quantity/price/proceeds, enforced as a unique
  constraint, so re-uploading overlapping statements is safe.
- **Alembic, not `create_all`**: `Base.metadata.create_all()` only ever
  creates tables that don't exist yet — it silently does nothing about a
  column added to an existing table, which would otherwise mean a schema
  change quietly failing to apply to an already-running deployment. Alembic
  migrations (`alembic/versions/`) make every schema change explicit and
  applied in order, and the app runs `alembic upgrade head` itself on
  startup so this stays a zero-extra-step deploy.
- **Live quotes via `yfinance`**: there's no supported public API for Google
  Finance, so `yfinance` (Yahoo Finance) is used for both equity quotes and
  the USD/SGD rate (`USDSGD=X`). Quotes are cached in-process for 30s to
  avoid hammering/being rate-limited by Yahoo. If a quote can't be fetched
  (network issue, symbol not found, rate limit), the API returns `null` for
  that field instead of erroring, and the UI shows "—" until the next
  refresh — it never blocks the rest of the dashboard.
- **Open-position cost basis**: unrealized P&L needs a cost basis for shares
  still held, which IBKR's per-fill Realized P/L doesn't provide (it's 0 on
  opens). `backend/app/services/positions.py` tracks a running
  weighted-average cost per symbol from the imported fills — simpler than
  FIFO lot tracking and a standard approximation for this purpose.
