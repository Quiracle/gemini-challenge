from __future__ import annotations

import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import duckdb

from nba_ingestion.api import NbaStatsClient
from nba_ingestion.models import DataQualityError, DqmCheck, PipelineConfig, PipelineResult
from nba_ingestion.schema import (
    CAREER_DB_COLUMNS,
    CAREER_FLOAT_COLUMNS,
    CAREER_INTEGER_COLUMNS,
    CAREER_TOTAL_COLUMNS,
    PLAYER_DB_COLUMNS,
    TEAM_DB_COLUMNS,
)
from nba_ingestion.utils import clean_string, to_float, to_int, to_league_id

LOGGER = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = REPO_ROOT / "sql" / "001_create_tables.sql"


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    client = NbaStatsClient(
        timeout_seconds=config.timeout_seconds,
        retries=config.retries,
        backoff_seconds=config.backoff_seconds,
    )

    LOGGER.info(
        "Fetching %s current players for season %s",
        config.league_id,
        config.season,
    )
    raw_player_rows = client.fetch_players(
        season=config.season,
        league_id=config.league_id,
    )
    if config.max_players is not None:
        raw_player_rows = raw_player_rows[: config.max_players]
        LOGGER.info("Limited run to first %s players", config.max_players)

    players = [normalize_player(row, config.season) for row in raw_player_rows]
    validate_source_rows(players, PLAYER_DB_COLUMNS, ["player_id"], "players")
    if not players:
        raise DataQualityError("Player endpoint returned zero rows")

    player_ids = [row["player_id"] for row in players]
    career_results = fetch_career_totals_parallel(
        client=client,
        player_ids=player_ids,
        league_id=config.league_id,
        workers=config.workers,
    )

    warnings: list[str] = []
    missing_career_player_ids: list[int] = []
    career_rows: list[dict[str, Any]] = []
    for player_id in player_ids:
        rows = career_results.get(player_id, [])
        if not rows:
            missing_career_player_ids.append(player_id)
            continue
        for row in rows:
            normalized = normalize_career_total(row)
            if normalized["player_id"] != player_id:
                warning = (
                    f"career endpoint for player_id={player_id} returned "
                    f"PLAYER_ID={normalized['player_id']}"
                )
                warnings.append(warning)
                LOGGER.warning(warning)
            career_rows.append(normalized)

    validate_source_rows(
        career_rows,
        CAREER_DB_COLUMNS,
        ["player_id", "league_id", "team_id"],
        "career_totals_regular_season",
    )
    teams = build_teams(raw_player_rows, career_rows)
    validate_source_rows(teams, TEAM_DB_COLUMNS, ["team_id"], "teams")

    with duckdb.connect(str(config.db_path)) as connection:
        replace_database_contents(connection, players, teams, career_rows)
        dqm_checks = run_dqm_checks(connection, players, teams, career_rows)
        failed_checks = [check for check in dqm_checks if not check.passed]
        if failed_checks:
            details = "; ".join(f"{check.name}: {check.detail}" for check in failed_checks)
            raise DataQualityError(f"DQM checks failed: {details}")

        loaded_player_count = table_count(connection, "players")
        loaded_team_count = table_count(connection, "teams")
        loaded_career_count = table_count(connection, "career_totals_regular_season")

    return PipelineResult(
        db_path=config.db_path,
        source_player_count=len(players),
        loaded_player_count=loaded_player_count,
        loaded_team_count=loaded_team_count,
        source_career_row_count=len(career_rows),
        loaded_career_row_count=loaded_career_count,
        missing_career_player_ids=tuple(missing_career_player_ids),
        dqm_checks=tuple(dqm_checks),
        warnings=tuple(warnings),
    )


def fetch_career_totals_parallel(
    client: NbaStatsClient,
    player_ids: list[int],
    league_id: str,
    workers: int,
) -> dict[int, list[dict[str, Any]]]:
    bounded_workers = max(1, min(workers, len(player_ids)))
    results: dict[int, list[dict[str, Any]]] = {}
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=bounded_workers) as executor:
        future_to_player_id = {
            executor.submit(client.fetch_career_totals, player_id, league_id): player_id
            for player_id in player_ids
        }

        for completed_count, future in enumerate(as_completed(future_to_player_id), start=1):
            player_id = future_to_player_id[future]
            try:
                results[player_id] = future.result()
            except Exception as exc:  # noqa: BLE001 - report all worker failures together.
                errors.append(f"{player_id}: {exc}")

            if completed_count % 50 == 0:
                LOGGER.info(
                    "Fetched career totals for %s/%s players",
                    completed_count,
                    len(player_ids),
                )

    if errors:
        sample = "; ".join(errors[:5])
        raise RuntimeError(
            f"Failed fetching career totals for {len(errors)} players. First errors: {sample}"
        )

    return results


def normalize_player(row: dict[str, Any], source_season: str) -> dict[str, Any]:
    player_id = to_int(row.get("PERSON_ID"), "PERSON_ID", allow_none=False)
    display_first_last = clean_string(row.get("DISPLAY_FIRST_LAST"))
    display_last_comma_first = clean_string(row.get("DISPLAY_LAST_COMMA_FIRST"))

    return {
        "player_id": player_id,
        "display_first_last": display_first_last
        or display_last_comma_first
        or str(player_id),
        "display_last_comma_first": display_last_comma_first,
        "roster_status": to_int(row.get("ROSTERSTATUS"), "ROSTERSTATUS"),
        "from_year": to_int(row.get("FROM_YEAR"), "FROM_YEAR"),
        "to_year": to_int(row.get("TO_YEAR"), "TO_YEAR"),
        "current_team_id": to_int(row.get("TEAM_ID"), "TEAM_ID"),
        "games_played_flag": clean_string(row.get("GAMES_PLAYED_FLAG")),
        "source_season": source_season,
    }


def normalize_career_total(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for api_column in CAREER_TOTAL_COLUMNS:
        db_column = api_column.lower()
        value = row.get(api_column)
        if api_column == "LEAGUE_ID":
            normalized[db_column] = to_league_id(value)
        elif api_column in CAREER_INTEGER_COLUMNS:
            normalized[db_column] = to_int(
                value,
                api_column,
                allow_none=api_column not in {"PLAYER_ID", "TEAM_ID"},
            )
        elif api_column in CAREER_FLOAT_COLUMNS:
            normalized[db_column] = to_float(value, api_column)
        else:
            normalized[db_column] = value
    return normalized


def build_teams(
    raw_player_rows: list[dict[str, Any]],
    career_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    teams: dict[int, dict[str, Any]] = {}

    def merge_team(
        team_id: int | None,
        abbreviation: str | None = None,
        city: str | None = None,
        name: str | None = None,
    ) -> None:
        if team_id is None:
            return
        existing = teams.setdefault(
            team_id,
            {
                "team_id": team_id,
                "team_abbreviation": None,
                "team_city": None,
                "team_name": None,
            },
        )
        if abbreviation and not existing["team_abbreviation"]:
            existing["team_abbreviation"] = abbreviation
        if city and not existing["team_city"]:
            existing["team_city"] = city
        if name and not existing["team_name"]:
            existing["team_name"] = name

    for row in raw_player_rows:
        merge_team(
            team_id=to_int(row.get("TEAM_ID"), "TEAM_ID"),
            abbreviation=clean_string(row.get("TEAM_ABBREVIATION")),
            city=clean_string(row.get("TEAM_CITY")),
            name=clean_string(row.get("TEAM_NAME")),
        )

    for row in career_rows:
        merge_team(team_id=row["team_id"])

    return [teams[team_id] for team_id in sorted(teams)]


def replace_database_contents(
    connection: duckdb.DuckDBPyConnection,
    players: list[dict[str, Any]],
    teams: list[dict[str, Any]],
    career_rows: list[dict[str, Any]],
) -> None:
    ddl = DDL_PATH.read_text(encoding="utf-8")
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute("DROP TABLE IF EXISTS career_totals_regular_season")
        connection.execute("DROP TABLE IF EXISTS players")
        connection.execute("DROP TABLE IF EXISTS teams")
        connection.execute(ddl)

        insert_rows(connection, "teams", TEAM_DB_COLUMNS, teams)
        insert_rows(connection, "players", PLAYER_DB_COLUMNS, players)
        insert_rows(
            connection,
            "career_totals_regular_season",
            CAREER_DB_COLUMNS,
            career_rows,
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def insert_rows(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    column_sql = ", ".join(columns)
    placeholder_sql = ", ".join(["?"] * len(columns))
    values = [tuple(row[column] for column in columns) for row in rows]
    connection.executemany(
        f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholder_sql})",
        values,
    )


def run_dqm_checks(
    connection: duckdb.DuckDBPyConnection,
    players: list[dict[str, Any]],
    teams: list[dict[str, Any]],
    career_rows: list[dict[str, Any]],
) -> list[DqmCheck]:
    checks = [
        row_count_check(connection, "players", len(players)),
        row_count_check(connection, "teams", len(teams)),
        row_count_check(connection, "career_totals_regular_season", len(career_rows)),
        duplicate_key_check(connection, "players", ["player_id"]),
        duplicate_key_check(connection, "teams", ["team_id"]),
        duplicate_key_check(
            connection,
            "career_totals_regular_season",
            ["player_id", "league_id", "team_id"],
        ),
        null_key_check(connection, "players", ["player_id"]),
        null_key_check(connection, "teams", ["team_id"]),
        null_key_check(
            connection,
            "career_totals_regular_season",
            ["player_id", "league_id", "team_id"],
        ),
        source_key_reconciliation_check(connection, "players", ["player_id"], players),
        source_key_reconciliation_check(connection, "teams", ["team_id"], teams),
        source_key_reconciliation_check(
            connection,
            "career_totals_regular_season",
            ["player_id", "league_id", "team_id"],
            career_rows,
        ),
        relationship_check(
            connection,
            child_table="players",
            child_column="current_team_id",
            parent_table="teams",
            parent_column="team_id",
            allow_null=True,
        ),
        relationship_check(
            connection,
            child_table="career_totals_regular_season",
            child_column="player_id",
            parent_table="players",
            parent_column="player_id",
        ),
        relationship_check(
            connection,
            child_table="career_totals_regular_season",
            child_column="team_id",
            parent_table="teams",
            parent_column="team_id",
        ),
    ]
    return checks


def row_count_check(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    expected_count: int,
) -> DqmCheck:
    actual_count = table_count(connection, table_name)
    return DqmCheck(
        name=f"{table_name}.row_count",
        passed=actual_count == expected_count,
        detail=f"expected={expected_count}, actual={actual_count}",
    )


def duplicate_key_check(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    key_columns: list[str],
) -> DqmCheck:
    key_sql = ", ".join(key_columns)
    duplicate_count = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {key_sql}, COUNT(*) AS row_count
            FROM {table_name}
            GROUP BY {key_sql}
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
    return DqmCheck(
        name=f"{table_name}.duplicate_keys",
        passed=duplicate_count == 0,
        detail=f"duplicate_key_groups={duplicate_count}",
    )


def null_key_check(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    key_columns: list[str],
) -> DqmCheck:
    predicate_sql = " OR ".join(f"{column} IS NULL" for column in key_columns)
    null_count = connection.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE {predicate_sql}"
    ).fetchone()[0]
    return DqmCheck(
        name=f"{table_name}.null_keys",
        passed=null_count == 0,
        detail=f"null_key_rows={null_count}",
    )


def source_key_reconciliation_check(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    key_columns: list[str],
    source_rows: list[dict[str, Any]],
) -> DqmCheck:
    key_sql = ", ".join(key_columns)
    loaded_keys = set(connection.execute(f"SELECT {key_sql} FROM {table_name}").fetchall())
    source_keys = {tuple(row[column] for column in key_columns) for row in source_rows}
    missing_in_db = source_keys - loaded_keys
    extra_in_db = loaded_keys - source_keys

    return DqmCheck(
        name=f"{table_name}.source_key_reconciliation",
        passed=not missing_in_db and not extra_in_db,
        detail=f"missing_in_db={len(missing_in_db)}, extra_in_db={len(extra_in_db)}",
    )


def relationship_check(
    connection: duckdb.DuckDBPyConnection,
    child_table: str,
    child_column: str,
    parent_table: str,
    parent_column: str,
    allow_null: bool = False,
) -> DqmCheck:
    null_filter = f"AND child.{child_column} IS NOT NULL" if allow_null else ""
    missing_count = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {child_table} AS child
        LEFT JOIN {parent_table} AS parent
            ON child.{child_column} = parent.{parent_column}
        WHERE parent.{parent_column} IS NULL
        {null_filter}
        """
    ).fetchone()[0]
    return DqmCheck(
        name=f"{child_table}.{child_column}_relationship",
        passed=missing_count == 0,
        detail=f"missing_parent_rows={missing_count}",
    )


def table_count(connection: duckdb.DuckDBPyConnection, table_name: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def validate_source_rows(
    rows: list[dict[str, Any]],
    columns: list[str],
    key_columns: list[str],
    dataset_name: str,
) -> None:
    missing_columns = [
        column
        for column in columns
        if any(column not in row for row in rows)
    ]
    if missing_columns:
        raise DataQualityError(f"{dataset_name} missing transformed columns: {missing_columns}")

    null_key_rows = [
        index
        for index, row in enumerate(rows, start=1)
        if any(row.get(column) is None for column in key_columns)
    ]
    if null_key_rows:
        sample = null_key_rows[:5]
        raise DataQualityError(
            f"{dataset_name} has null key values in source rows: {sample}"
        )

    keys = [tuple(row[column] for column in key_columns) for row in rows]
    duplicate_keys = [
        key
        for key, count in Counter(keys).items()
        if count > 1
    ]
    if duplicate_keys:
        sample = duplicate_keys[:5]
        raise DataQualityError(
            f"{dataset_name} has duplicate source keys for {key_columns}: {sample}"
        )
