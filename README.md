# Gemini Data Engineering Challenge

This repository contains a lean Python ingestion pipeline for the Gemini NBA data engineering challenge. It fetches the 2022-23 current-player population from the NBA/G League stats API, fetches each player's career stats, extracts only `CareerTotalsRegularSeason`, and loads the result into DuckDB.

## Architecture

The project is intentionally script-based and small:

- `nba_ingestion/api.py`: NBA stats API client with retry/backoff, realistic request headers, and result-set schema validation.
- `nba_ingestion/pipeline.py`: transforms API rows, fetches per-player career totals with bounded concurrency, loads DuckDB transactionally, and runs DQM checks.
- `nba_ingestion/schema.py`: expected API columns, DuckDB insert column order, and stat type groupings.
- `nba_ingestion/models.py`: small runtime dataclasses and pipeline/DQM error type.
- `nba_ingestion/utils.py`: small value-cleaning and type-coercion helpers.
- `nba_ingestion/__main__.py`: CLI entry point.
- `sql/001_create_tables.sql`: DuckDB DDL for the normalized tables.
- `tests/test_pipeline.py`: local unit tests for transformations, idempotent loading, and DQM checks.

## Schema

The DuckDB schema uses the requested practical three-table design:

- `players`: one row per player from the 2022-23 `commonallplayers` endpoint.
- `teams`: team IDs and team metadata observed in the player-list endpoint, plus any career-total `TEAM_ID` values that are not otherwise described.
- `career_totals_regular_season`: one or more `CareerTotalsRegularSeason` rows per returned player, keyed by `player_id`, `league_id`, and `team_id`.

`LEAGUE_ID` is preserved as a code column in `career_totals_regular_season`; it is not modeled as a separate dimension table.

The schema also defines foreign keys from `players.current_team_id` to `teams.team_id`, and from `career_totals_regular_season.player_id`/`team_id` to `players`/`teams`.

## How To Run

Install or sync dependencies with uv:

```powershell
uv sync
```

Run the full ingestion:

```powershell
uv run python -m nba_ingestion
```

By default this writes `data/nba_gleague.duckdb`. You can choose another path:

```powershell
uv run python -m nba_ingestion --db-path data/challenge.duckdb
```

For a quick smoke test against only a few players:

```powershell
uv run python -m nba_ingestion --max-players 5 --db-path data/smoke.duckdb
```

Run local tests:

```powershell
uv run python -m unittest discover -s tests
```

## Data Quality And Idempotence

Each run performs a full refresh inside a DuckDB transaction by recreating the three tables and loading fresh rows. This keeps reruns idempotent and prevents duplicate rows while preserving physical foreign-key constraints.

The pipeline includes lightweight checks for:

- loaded row counts versus transformed source rows
- duplicate primary keys
- null key identifiers
- relationship checks matching the foreign-key structure
- source key reconciliation against loaded DuckDB rows

The API parsing also validates the expected NBA result-set columns. Missing expected columns fail clearly. Extra columns are logged as warnings so schema drift is visible without blocking the known required fields.

## Assumptions And Caveats

- The 2022-23 `commonallplayers` endpoint is treated as the operational definition of the player population, per the prompt.
- The pipeline stores only the `CareerTotalsRegularSeason` result set from `playercareerstats`.
- A player can appear in the 2022-23 player-list endpoint even if their career response does not contain 2022-23 season detail. This pipeline does not require season-by-season agreement; it loads returned career totals when present and reports players with no `CareerTotalsRegularSeason` rows.
- Some player career endpoints may return an empty JSON object (`{}`) with HTTP 200. This is treated as no available `CareerTotalsRegularSeason` rows for that player and is reported in the run summary.
- `TEAM_ID` from career totals is preserved exactly. Career-total rows may use aggregate or otherwise undescribed team IDs, so the `teams` table allows nullable descriptive fields.
- NBA stats endpoints can be sensitive to headers, rate limits, or transient failures. The client uses browser-like headers, bounded concurrency, request timeouts, and exponential retry/backoff. If the API returns HTTP 403 `Access Denied`, wait before rerunning and consider lowering `--workers` or using `--max-players` for smoke tests.
