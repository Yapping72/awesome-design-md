# Trade Journal — Spec

Living document: current state of the system, plus a prioritized backlog of
enhancements. Updated after each backlog item lands — see **Backlog**
status column and **Changelog** at the bottom.

## 1. Purpose

A self-hosted trade journal for active/retail equity traders. Import an
IBKR Activity Statement CSV, get back a realized P&L journal (calendar
heatmap, day/week/month aggregates, summary stats) plus live portfolio
valuation for positions still open.

## 2. Architecture

```
trade-journal/
├── backend/    FastAPI + SQLAlchemy, Python 3.11
├── frontend/   React 18 + TypeScript + Vite, plain CSS (no framework)
└── docker-compose.yml   postgres + backend + frontend(nginx)
```

- **Database**: PostgreSQL. Tables: `executions`, `trade_notes`; schema
  created via `Base.metadata.create_all()` at backend startup (no
  migrations yet — see backlog).
- **Auth**: none. Single-user, self-hosted, no login. Out of scope unless
  requested.
- **Market data**: `yfinance` (Yahoo Finance) for equity quotes and the
  USD/SGD FX rate, in-process cached 30s, degrades to `null` on failure
  rather than erroring.

## 3. Data model

### `executions` (one row per IBKR fill)

| Column | Type | Notes |
|---|---|---|
| `id` | int, PK | |
| `external_id` | string, unique | sha256 of account/symbol/datetime/qty/price/proceeds — makes re-import idempotent |
| `account_id` | string, nullable | |
| `asset_category` | string, nullable | e.g. "Stocks" |
| `currency` | string, nullable | e.g. "USD" |
| `symbol` | string | |
| `trade_datetime` | datetime | |
| `trade_date` | date | denormalized for cheap `GROUP BY` |
| `quantity` | float | signed: +buy, -sell |
| `price` | float | fill price |
| `proceeds` | float, nullable | |
| `commission` | float, nullable | signed negative (a cost) |
| `realized_pnl` | float | IBKR's own value; 0 on opening fills, populated on closing fills |
| `code` | string, nullable | IBKR fill code, e.g. "O"/"C" |
| `created_at` | datetime | |

### `trade_notes` (journal notes/tags for a round-trip trade)

| Column | Type | Notes |
|---|---|---|
| `id` | int, PK | |
| `round_trip_id` | string, unique | `"{entry_execution_id}:{exit_execution_id}"` — deterministic, not a surrogate key, since round trips aren't stored rows (see backlog #2) |
| `notes` | string, nullable | free text |
| `tags` | string, nullable | comma-separated |
| `updated_at` | datetime | |

## 4. Current features

- **Import**: drag-and-drop or file-picker upload of an IBKR Activity
  Statement CSV. Parses only the `Trades` section
  (`backend/app/parsers/ibkr.py`). Idempotent — re-uploading overlapping
  statements skips already-imported fills via the `external_id` unique
  constraint.
- **Realized P&L**: read directly from IBKR's own `Realized P/L` column
  (net of commission) rather than recomputed via FIFO — see Design Notes
  in README for why. `net_pnl = realized_pnl + commission` everywhere.
- **Calendar view**: month grid, daily P&L as a green/red heatmap with
  fill count per day. Month navigation.
- **Aggregation**: P&L bar chart, toggle between day / week / month
  (`GET /api/pnl/aggregate`).
- **Summary stats**: total P&L, win rate, avg win/loss, profit factor,
  best/worst day (`GET /api/pnl/summary`).
- **Trade blotter**: paginated, symbol-filterable list of raw fills
  (`GET /api/trades`).
- **Round-trip trades**: raw fills are FIFO-matched per symbol into
  discrete entry→exit trades (side, quantity, entry/exit price & time,
  hold duration, commission, P&L) via
  `backend/app/services/round_trips.py` and
  `GET /api/trades/round-trips`. The Trades page defaults to this view,
  with a toggle back to the raw fills blotter for auditing.
- **Trade notes & tags**: each round trip can carry free-text notes and
  comma-tags, edited inline in the Round Trips table (click a row's
  "Notes" cell) and persisted via
  `PUT /api/trades/round-trips/{round_trip_id}/notes`. Keyed on a
  deterministic id derived from the entry/exit execution ids, not a
  surrogate key, since round trips are recomputed on the fly rather than
  stored.
- **Open positions**: running weighted-average cost basis per symbol
  computed from imported fills (`backend/app/services/positions.py`),
  enriched with live last price, market value, and unrealized P&L
  (`GET /api/portfolio`). Refreshes every 30s in the UI.
- **Live FX**: USD/SGD rate ticker in the header
  (`GET /api/fx/usdsgd`), and portfolio totals also shown converted to
  SGD.

## 5. API reference

| Method | Path | Description |
|---|---|---|
| POST | `/api/upload` | Upload an IBKR Activity Statement CSV (`multipart/form-data`, field `file`) |
| GET | `/api/pnl/calendar` | Daily P&L for `year`/`month` |
| GET | `/api/pnl/aggregate` | P&L by `period=day\|week\|month`, optional `start`/`end` |
| GET | `/api/pnl/summary` | Overall summary stats |
| GET | `/api/trades` | Paginated fills (`page`, `page_size`, `symbol`, `start`, `end`) |
| GET | `/api/trades/round-trips` | Paginated FIFO-matched round-trip trades (`page`, `page_size`, `symbol`) |
| PUT | `/api/trades/round-trips/{round_trip_id}/notes` | Upsert notes/tags for a round-trip trade |
| DELETE | `/api/trades` | Clear all imported fills |
| GET | `/api/portfolio` | Open positions with live quotes, unrealized P&L (USD + SGD) |
| GET | `/api/fx/usdsgd` | Live USD/SGD rate |

Full interactive docs at `/docs` (FastAPI auto-generated).

## 6. Known limitations (by design, for now)

- No auth / multi-user support — single self-hosted instance.
- Unrealized P&L (open positions, `/api/portfolio`) uses weighted-average
  cost, not FIFO — intentionally simpler, since it only needs to answer
  "am I up or down on this position right now". Closed-trade history uses
  proper FIFO lot matching instead (`services/round_trips.py`); the two
  are separate calculations for separate questions.
- `DELETE /api/trades` wipes everything — no per-import undo. See backlog #7.
- Schema managed by `create_all`, not versioned migrations. See backlog #6.
- Only USD→SGD FX conversion; other currencies pass through unconverted.

## 7. Backlog

Status: `planned` → `in progress` → `done`. Ordered by priority within
each tier.

### Tier 1 — journal-core value

| # | Feature | Status |
|---|---|---|
| 1 | **Round-trip trade view**: FIFO-match opening/closing fills per symbol into discrete entry→exit trades (side, quantity, entry/exit price & time, hold duration, P&L), as a new view alongside the raw fills blotter | done |
| 2 | **Trade notes & tags**: free-text notes + strategy/setup tags attached to a round-trip trade, editable in the UI | done |
| 3 | **Equity curve**: cumulative realized P&L over time as a line chart on the dashboard | planned |
| 4 | **Symbol performance breakdown**: P&L, win rate, trade count grouped by symbol | planned |
| 5 | **CSV export**: download trades / round-trips / daily P&L as CSV | planned |

### Tier 2 — robustness & operability

| # | Feature | Status |
|---|---|---|
| 6 | **Alembic migrations** replacing `create_all` | planned |
| 7 | **Import batches**: track each upload as a batch, list upload history, allow deleting a single batch instead of only "delete everything" | planned |
| 8 | **Trades table sorting & date-range filter** in the UI | planned |
| 9 | **CI**: GitHub Actions running backend pytest + frontend typecheck/build on push | planned |

### Tier 3 — polish

| # | Feature | Status |
|---|---|---|
| 10 | Light theme toggle (dark exists today) | planned |
| 11 | Docker Compose healthchecks for backend/frontend, runtime-configurable frontend API URL (currently baked in at image build time) | planned |
| 12 | Mobile-responsive layout pass | planned |

## 8. Changelog

- 2026-08-30 — Backlog #2 done: trade notes & tags (`trade_notes` table,
  `PUT /api/trades/round-trips/{id}/notes`, inline editor in the Round
  Trips table). 5 new backend tests, including an HTTP-level integration
  test via FastAPI's TestClient against SQLite (29 total passing).
  Verified against real Postgres and in-browser, including persistence
  across a page reload. Also modernized the deprecated `@app.on_event`
  startup hook to a `lifespan` handler while in `main.py`.
- 2026-08-30 — Backlog #1 done: round-trip trade view (FIFO fill matching,
  `services/round_trips.py`, `GET /api/trades/round-trips`, Trades page
  toggle). 7 new backend unit tests (24 total passing). Verified against
  real Postgres and in-browser.
- 2026-08-30 — Spec created, capturing state after IBKR import + calendar/aggregation/summary + live portfolio/FX features. Backlog drafted.
