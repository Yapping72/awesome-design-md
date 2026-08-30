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

- **Database**: PostgreSQL. Tables: `executions`, `trade_notes`. Schema is
  managed by **Alembic** migrations (`backend/alembic/versions/`); the app
  runs `alembic upgrade head` itself in its lifespan handler on startup, so
  no manual migration step is needed to bring up a fresh deployment.
- **Auth**: none. Single-user, self-hosted, no login. Out of scope unless
  requested.
- **Market data**: `yfinance` (Yahoo Finance) for equity quotes and the
  USD/SGD FX rate, in-process cached 30s, degrades to `null` on failure
  rather than erroring.
- **CI**: `.github/workflows/trade-journal-ci.yml` runs on push/PR when
  `trade-journal/**` changes — backend job runs pytest against a real
  Postgres service container plus a smoke test of the running app
  (health check, upload, summary); frontend job runs `tsc` + `vite build`.

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

### `upload_batches` (one row per CSV upload)

| Column | Type | Notes |
|---|---|---|
| `id` | int, PK | |
| `filename` | string | |
| `row_count` | int | count of *newly inserted* fills from this upload (0 if every fill was a duplicate already imported) |
| `uploaded_at` | datetime | |

`executions.batch_id` (nullable FK → `upload_batches.id`) records which
upload first inserted each fill. A duplicate fill (skipped on re-upload)
keeps belonging to whichever batch inserted it originally — it's never
reattributed to a later, overlapping upload.

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
- **Import history**: every upload is tracked as a batch
  (`GET /api/uploads`) with filename, upload time, and how many fills it
  actually added. A single batch can be undone
  (`DELETE /api/uploads/{batch_id}`) without wiping the rest of the
  journal — shown as a "Remove" action per import in the upload panel.
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
  with a toggle back to the raw fills blotter for auditing. Both tables
  support a symbol filter, a date-range filter (round trips filter on
  exit date), and click-to-sort column headers (`SortableTh`), all
  server-side.
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
- **Equity curve**: cumulative realized net P&L over time as an area
  chart on the dashboard (`GET /api/pnl/equity-curve`), a running sum
  over the same daily P&L used by the calendar view.
- **Symbol performance**: round trips grouped by symbol — trade count,
  win/loss split, win rate, avg P&L, total P&L — ranked by total P&L
  (`GET /api/trades/by-symbol`), shown as a table on the dashboard.
- **CSV export**: raw fills, round trips (with notes/tags), and daily P&L
  can each be downloaded as CSV (`services/csv_export.py`), respecting
  the same filters as their JSON counterparts. Linked from the Trades
  page (toggles between fills/round-trips export) and the dashboard's
  aggregation panel.

## 5. API reference

| Method | Path | Description |
|---|---|---|
| POST | `/api/upload` | Upload an IBKR Activity Statement CSV (`multipart/form-data`, field `file`) |
| GET | `/api/uploads` | List import batches (filename, row count, timestamp), newest first |
| DELETE | `/api/uploads/{batch_id}` | Remove one import batch's fills (404 if the batch doesn't exist) |
| GET | `/api/pnl/calendar` | Daily P&L for `year`/`month` |
| GET | `/api/pnl/aggregate` | P&L by `period=day\|week\|month`, optional `start`/`end` |
| GET | `/api/pnl/summary` | Overall summary stats |
| GET | `/api/pnl/equity-curve` | Cumulative realized P&L over time, optional `start`/`end` |
| GET | `/api/trades` | Paginated fills (`page`, `page_size`, `symbol`, `start`, `end`, `sort_by`, `sort_dir`) |
| GET | `/api/trades/round-trips` | Paginated FIFO-matched round-trip trades (`page`, `page_size`, `symbol`, `start`, `end`, `sort_by`, `sort_dir`) |
| PUT | `/api/trades/round-trips/{round_trip_id}/notes` | Upsert notes/tags for a round-trip trade |
| GET | `/api/trades/by-symbol` | Round trips grouped by symbol, ranked by total P&L |
| GET | `/api/trades/export` | Raw fills as CSV (`symbol`, `start`, `end`) |
| GET | `/api/trades/round-trips/export` | Round trips as CSV, with notes/tags (`symbol`) |
| GET | `/api/pnl/export` | Daily P&L as CSV (`start`, `end`) |
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
- Only USD→SGD FX conversion; other currencies pass through unconverted.

## 7. Backlog

Status: `planned` → `in progress` → `done`. Ordered by priority within
each tier.

### Tier 1 — journal-core value

| # | Feature | Status |
|---|---|---|
| 1 | **Round-trip trade view**: FIFO-match opening/closing fills per symbol into discrete entry→exit trades (side, quantity, entry/exit price & time, hold duration, P&L), as a new view alongside the raw fills blotter | done |
| 2 | **Trade notes & tags**: free-text notes + strategy/setup tags attached to a round-trip trade, editable in the UI | done |
| 3 | **Equity curve**: cumulative realized P&L over time as a line chart on the dashboard | done |
| 4 | **Symbol performance breakdown**: P&L, win rate, trade count grouped by symbol | done |
| 5 | **CSV export**: download trades / round-trips / daily P&L as CSV | done |

### Tier 2 — robustness & operability

| # | Feature | Status |
|---|---|---|
| 6 | **Alembic migrations** replacing `create_all` | done |
| 7 | **Import batches**: track each upload as a batch, list upload history, allow deleting a single batch instead of only "delete everything" | done |
| 8 | **Trades table sorting & date-range filter** in the UI | done |
| 9 | **CI**: GitHub Actions running backend pytest + frontend typecheck/build on push | done |

### Tier 3 — polish

| # | Feature | Status |
|---|---|---|
| 10 | Light theme toggle (dark exists today) | planned |
| 11 | Docker Compose healthchecks for backend/frontend, runtime-configurable frontend API URL (currently baked in at image build time) | planned |
| 12 | Mobile-responsive layout pass | planned |

## 8. Changelog

- 2026-08-30 — Backlog #7 done, completing Tier 2: import batches. New
  `upload_batches` table and a nullable `executions.batch_id` FK — the
  first real schema change to go through Alembic (migration
  `0002_add_upload_batches.py`, autogenerated then hand-fixed to give the
  FK constraint an explicit name so `downgrade()` doesn't reference a
  `None` constraint name). The upload endpoint creates a batch row and
  stamps its id onto newly-inserted fills only; `ON CONFLICT DO NOTHING`
  means a duplicate fill's row (batch_id included) is never touched, so
  it stays attributed to whichever earlier batch first inserted it. New
  endpoints `GET /api/uploads` and `DELETE /api/uploads/{batch_id}`;
  `DELETE /api/trades` (clear everything) now also clears batch rows so
  the two stay consistent. Frontend: an "Import History" list in the
  upload panel with a per-batch Remove action (confirm dialog first).
  6 new tests (50 total passing) covering batch creation, that a
  re-upload's duplicates don't steal batch ownership, that deleting one
  batch only removes its own fills, and that clearing everything also
  clears batches. Verified against real Postgres end-to-end (upload two
  overlapping/non-overlapping statements, delete one batch via the API,
  confirm only its fills disappeared) and visually in the browser via a
  real click-through of the Remove flow.
- 2026-08-30 — Backlog #6 done: Alembic migrations replacing
  `Base.metadata.create_all()`. Motivation: `create_all` only creates
  tables that don't exist yet — it silently no-ops on a column added to an
  existing table, which matters once backlog #7 (import batches) needs a
  real schema change against deployments that already have data. Set up
  `alembic/env.py` to import `Base.metadata` from the app and read the
  same `DATABASE_URL` env var as the app (one source of truth, no
  duplicated config); autogenerated the baseline migration
  (`0001_initial_schema.py`) capturing the current `executions` and
  `trade_notes` tables, then verified `alembic check` reports zero drift
  against the models. `main.py`'s lifespan handler now runs
  `alembic upgrade head` instead of `create_all` (same retry-on-not-ready
  loop as before). Docker: the backend image now also copies `alembic/`
  and `alembic.ini`. Verified against a real, freshly-created Postgres
  database — starting the actual app (not just running `alembic upgrade`
  by hand) correctly created both tables, a second restart on the
  already-migrated database was a clean no-op, and the full upload ->
  summary flow worked afterward. All 44 backend tests still pass
  (they build their own SQLite schema directly and don't go through the
  app's lifespan, so this was a compatibility check, not a rewrite).
- 2026-08-30 — Backlog #8 done: sorting & date-range filter for both the
  Trades and Round Trips tables. Backend: whitelisted `sort_by`/`sort_dir`
  query params (SQL `ORDER BY` for fills, in-memory sort for round trips
  since those are computed, not queried) plus an exit-date range filter
  on round trips (fills already had one). Frontend: a shared `SortableTh`
  component (click a header to sort, click again to flip direction) and
  date-range `<input type="date">` pairs on both tables. 7 new tests
  (44 total passing). Verified against real Postgres and in-browser —
  sort direction toggling and the date filter narrowing to the expected
  single row both confirmed visually.
- 2026-08-30 — Backlog #9 done: CI
  (`.github/workflows/trade-journal-ci.yml`), path-scoped to
  `trade-journal/**` so it doesn't run on unrelated changes to this
  repo's original curated-list content. Backend job runs pytest against a
  real Postgres service container, then smoke-tests the running app
  (health, upload, summary) the same way this session validated each
  feature manually. Frontend job runs `npm ci` + `tsc` + `vite build`.
  Validated the exact job steps locally (pytest, `npm ci`, the smoke-test
  curl sequence) before committing, plus a YAML syntax check.
- 2026-08-30 — Backlog #5 done, completing Tier 1: CSV export
  (`services/csv_export.py`; `GET /api/trades/export`,
  `GET /api/trades/round-trips/export`, `GET /api/pnl/export`; export
  links on the Trades page and dashboard aggregation panel using plain
  `<a href>` downloads via the server's `Content-Disposition` header, no
  client-side blob handling needed). 4 new tests (37 total passing).
  Verified against real Postgres and via real browser downloads
  (Playwright), confirming correct filenames and CSV content for all
  three exports.
- 2026-08-30 — Backlog #4 done: symbol performance breakdown
  (`services/round_trips.aggregate_by_symbol`, a pure function grouping
  already-computed round trips so callers don't recompute them; new
  endpoint `GET /api/trades/by-symbol`; `SymbolPerformanceTable` on the
  dashboard). 2 new unit tests (33 total passing). Verified against real
  Postgres and in-browser — ranking matches expected total P&L order.
- 2026-08-30 — Backlog #3 done: equity curve (`services/pnl.equity_curve`,
  `GET /api/pnl/equity-curve`, `EquityCurveChart` area chart on the
  dashboard). 3 new tests via TestClient+SQLite covering the cumulative
  sum and date-range filtering (31 total passing). Verified against real
  Postgres and in-browser — the rendered curve traces the exact daily P&L
  path.
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
