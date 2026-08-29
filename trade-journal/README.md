# Trade Journal

A self-hosted trade journal that imports Interactive Brokers Activity
Statement CSV exports and turns them into a realized P&L journal: summary
stats, a calendar heatmap of daily P&L, and P&L aggregated by day, week, or
month.

Stack: **React + TypeScript** (Vite) frontend, **FastAPI** backend,
**PostgreSQL** storage, all containerized with **Docker Compose**.

## Features

- Import an IBKR Activity Statement CSV export (drag & drop or file picker)
- Idempotent import — re-uploading the same statement skips already-imported
  fills instead of double-counting
- Realized P&L is read directly from IBKR's own `Realized P/L` column (net of
  commission), so figures match what IBKR itself reports — no separate
  FIFO/lot-matching engine to get out of sync
- Calendar view of daily P&L (green/red heatmap, like a trading journal)
- P&L aggregation by day / week / month with a bar chart
- Summary stats: total P&L, win rate, avg win/loss, profit factor, best/worst
  day
- Paginated, filterable trade blotter

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

Database tables are created automatically on backend startup.

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

**Frontend**

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

## API

| Method | Path                 | Description                                   |
| ------ | -------------------- | ---------------------------------------------- |
| POST   | `/api/upload`         | Upload an IBKR Activity Statement CSV          |
| GET    | `/api/pnl/calendar`   | Daily P&L for a given `year`/`month`           |
| GET    | `/api/pnl/aggregate`  | P&L aggregated by `period=day\|week\|month`    |
| GET    | `/api/pnl/summary`    | Overall summary stats                          |
| GET    | `/api/trades`         | Paginated trade list (`symbol`, `start`, `end`)|
| DELETE | `/api/trades`         | Clear all imported trades                      |

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
