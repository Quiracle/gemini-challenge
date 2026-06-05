from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from nba_ingestion.models import DataQualityError, PipelineConfig
from nba_ingestion.pipeline import (
    build_teams,
    duplicate_key_check,
    fetch_career_totals_parallel,
    normalize_career_total,
    normalize_player,
    null_key_check,
    relationship_check,
    replace_database_contents,
    run_dqm_checks,
    run_pipeline,
    source_key_reconciliation_check,
    table_count,
)


def raw_player(
    player_id: int = 201142,
    display_name: str = "Kevin Durant",
    team_id: int = 1610612756,
    team_city: str = "Phoenix",
    team_name: str = "Suns",
    team_abbreviation: str = "PHX",
) -> dict[str, object]:
    return {
        "PERSON_ID": player_id,
        "DISPLAY_FIRST_LAST": display_name,
        "DISPLAY_LAST_COMMA_FIRST": ", ".join(reversed(display_name.split(" ", 1))),
        "ROSTERSTATUS": 1,
        "FROM_YEAR": "2007",
        "TO_YEAR": "2024",
        "TEAM_ID": team_id,
        "TEAM_CITY": team_city,
        "TEAM_NAME": team_name,
        "TEAM_ABBREVIATION": team_abbreviation,
        "GAMES_PLAYED_FLAG": "Y",
    }


def career_total(
    player_id: int = 201142,
    league_id: str | None = "00",
    team_id: int | None = 0,
) -> dict[str, object]:
    return {
        "PLAYER_ID": player_id,
        "LEAGUE_ID": league_id,
        "TEAM_ID": team_id,
        "GP": 1000,
        "GS": 1000,
        "MIN": 36000.5,
        "FGM": 9000,
        "FGA": 18000,
        "FG_PCT": 0.5,
        "FG3M": 2000,
        "FG3A": 5000,
        "FG3_PCT": 0.4,
        "FTM": 7000,
        "FTA": 8000,
        "FT_PCT": 0.875,
        "OREB": 700,
        "DREB": 6500,
        "REB": 7200,
        "AST": 4500,
        "STL": 1000,
        "BLK": 1100,
        "TOV": 3000,
        "PF": 2000,
        "PTS": 29000,
    }


class FakeClient:
    def __init__(
        self,
        players: list[dict[str, object]],
        career_rows_by_player: dict[int, list[dict[str, object]]],
        failing_player_ids: set[int] | None = None,
    ) -> None:
        self.players = players
        self.career_rows_by_player = career_rows_by_player
        self.failing_player_ids = failing_player_ids or set()

    def fetch_players(self, season: str, league_id: str) -> list[dict[str, object]]:
        return self.players

    def fetch_career_totals(
        self,
        player_id: int,
        league_id: str,
    ) -> list[dict[str, object]]:
        if player_id in self.failing_player_ids:
            raise RuntimeError("boom")
        return self.career_rows_by_player.get(player_id, [])


class PipelineTransformTests(unittest.TestCase):
    def test_normalizes_player_and_career_total_types(self) -> None:
        player = normalize_player(raw_player(), "2022-23")
        career = normalize_career_total(career_total())

        self.assertEqual(player["player_id"], 201142)
        self.assertEqual(player["current_team_id"], 1610612756)
        self.assertEqual(player["source_season"], "2022-23")
        self.assertEqual(career["league_id"], "00")
        self.assertEqual(career["team_id"], 0)
        self.assertIsInstance(career["gp"], int)
        self.assertIsInstance(career["min"], float)

    def test_builds_teams_from_player_and_career_rows(self) -> None:
        career = normalize_career_total(career_total())
        teams = build_teams([raw_player()], [career])

        self.assertEqual({team["team_id"] for team in teams}, {0, 1610612756})
        phoenix = next(team for team in teams if team["team_id"] == 1610612756)
        self.assertEqual(phoenix["team_abbreviation"], "PHX")


class DuckDbLoadTests(unittest.TestCase):
    def test_replace_load_is_idempotent_and_passes_dqm(self) -> None:
        player = normalize_player(raw_player(), "2022-23")
        career = normalize_career_total(career_total())
        teams = build_teams([raw_player()], [career])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            with duckdb.connect(str(db_path)) as connection:
                replace_database_contents(connection, [player], teams, [career])
                replace_database_contents(connection, [player], teams, [career])
                checks = run_dqm_checks(connection, [player], teams, [career])

                self.assertEqual(table_count(connection, "players"), 1)
                self.assertEqual(table_count(connection, "career_totals_regular_season"), 1)
                self.assertTrue(all(check.passed for check in checks))


class RunPipelineTests(unittest.TestCase):
    def run_with_fake_client(self, fake_client: FakeClient, db_path: Path):
        with mock.patch("nba_ingestion.pipeline.NbaStatsClient", return_value=fake_client):
            return run_pipeline(PipelineConfig(db_path=db_path, workers=2))

    def test_run_pipeline_loads_valid_rows(self) -> None:
        players = [
            raw_player(201142, "Kevin Durant", 1610612756, "Phoenix", "Suns", "PHX"),
            raw_player(2544, "LeBron James", 1610612747, "Los Angeles", "Lakers", "LAL"),
        ]
        fake_client = FakeClient(
            players=players,
            career_rows_by_player={
                201142: [career_total(201142, team_id=0)],
                2544: [career_total(2544, team_id=0)],
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pipeline.duckdb"
            result = self.run_with_fake_client(fake_client, db_path)

            self.assertEqual(result.loaded_player_count, 2)
            self.assertEqual(result.loaded_career_row_count, 2)
            self.assertEqual(result.missing_career_player_ids, ())
            self.assertTrue(all(check.passed for check in result.dqm_checks))

            with duckdb.connect(str(db_path)) as connection:
                self.assertEqual(table_count(connection, "players"), 2)
                self.assertEqual(table_count(connection, "career_totals_regular_season"), 2)

    def test_run_pipeline_reports_players_without_career_totals(self) -> None:
        players = [
            raw_player(201142, "Kevin Durant"),
            raw_player(2544, "LeBron James", 1610612747, "Los Angeles", "Lakers", "LAL"),
        ]
        fake_client = FakeClient(
            players=players,
            career_rows_by_player={201142: [career_total(201142)]},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.run_with_fake_client(fake_client, Path(tmpdir) / "pipeline.duckdb")

        self.assertEqual(result.loaded_player_count, 2)
        self.assertEqual(result.loaded_career_row_count, 1)
        self.assertEqual(result.missing_career_player_ids, (2544,))

    def test_run_pipeline_zero_players_raises(self) -> None:
        fake_client = FakeClient(players=[], career_rows_by_player={})

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(DataQualityError, "zero rows"):
                self.run_with_fake_client(fake_client, Path(tmpdir) / "pipeline.duckdb")

    def test_run_pipeline_duplicate_player_ids_raise(self) -> None:
        fake_client = FakeClient(
            players=[raw_player(201142), raw_player(201142)],
            career_rows_by_player={201142: [career_total(201142)]},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(DataQualityError, "duplicate source keys"):
                self.run_with_fake_client(fake_client, Path(tmpdir) / "pipeline.duckdb")

    def test_run_pipeline_duplicate_career_keys_raise(self) -> None:
        fake_client = FakeClient(
            players=[raw_player(201142)],
            career_rows_by_player={
                201142: [career_total(201142, team_id=0), career_total(201142, team_id=0)]
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(DataQualityError, "duplicate source keys"):
                self.run_with_fake_client(fake_client, Path(tmpdir) / "pipeline.duckdb")

    def test_run_pipeline_null_required_career_key_raises(self) -> None:
        fake_client = FakeClient(
            players=[raw_player(201142)],
            career_rows_by_player={201142: [career_total(201142, team_id=None)]},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(DataQualityError, "TEAM_ID is required"):
                self.run_with_fake_client(fake_client, Path(tmpdir) / "pipeline.duckdb")


class DqmCheckTests(unittest.TestCase):
    def test_duplicate_key_check_detects_duplicate_groups(self) -> None:
        with duckdb.connect(":memory:") as connection:
            connection.execute("CREATE TABLE duplicate_test (id INTEGER)")
            connection.executemany("INSERT INTO duplicate_test VALUES (?)", [(1,), (1,)])

            check = duplicate_key_check(connection, "duplicate_test", ["id"])

        self.assertFalse(check.passed)
        self.assertEqual(check.detail, "duplicate_key_groups=1")

    def test_null_key_check_detects_null_keys(self) -> None:
        with duckdb.connect(":memory:") as connection:
            connection.execute("CREATE TABLE null_test (id INTEGER)")
            connection.executemany("INSERT INTO null_test VALUES (?)", [(None,), (1,)])

            check = null_key_check(connection, "null_test", ["id"])

        self.assertFalse(check.passed)
        self.assertEqual(check.detail, "null_key_rows=1")

    def test_relationship_check_detects_missing_parent_rows(self) -> None:
        with duckdb.connect(":memory:") as connection:
            connection.execute("CREATE TABLE child_test (parent_id INTEGER)")
            connection.execute("CREATE TABLE parent_test (id INTEGER)")
            connection.execute("INSERT INTO child_test VALUES (1)")

            check = relationship_check(
                connection,
                child_table="child_test",
                child_column="parent_id",
                parent_table="parent_test",
                parent_column="id",
            )

        self.assertFalse(check.passed)
        self.assertEqual(check.detail, "missing_parent_rows=1")

    def test_source_key_reconciliation_detects_loaded_source_mismatch(self) -> None:
        with duckdb.connect(":memory:") as connection:
            connection.execute("CREATE TABLE reconciliation_test (id INTEGER)")
            connection.execute("INSERT INTO reconciliation_test VALUES (1)")

            check = source_key_reconciliation_check(
                connection,
                table_name="reconciliation_test",
                key_columns=["id"],
                source_rows=[{"id": 2}],
            )

        self.assertFalse(check.passed)
        self.assertEqual(check.detail, "missing_in_db=1, extra_in_db=1")


class ParallelFetchTests(unittest.TestCase):
    def test_fetch_career_totals_parallel_returns_all_results(self) -> None:
        fake_client = FakeClient(
            players=[],
            career_rows_by_player={
                1: [career_total(1)],
                2: [career_total(2)],
            },
        )

        results = fetch_career_totals_parallel(
            client=fake_client,
            player_ids=[1, 2],
            league_id="00",
            workers=2,
        )

        self.assertEqual(set(results), {1, 2})

    def test_fetch_career_totals_parallel_reports_worker_failures(self) -> None:
        fake_client = FakeClient(
            players=[],
            career_rows_by_player={1: [career_total(1)]},
            failing_player_ids={2},
        )

        with self.assertRaisesRegex(RuntimeError, "2: boom"):
            fetch_career_totals_parallel(
                client=fake_client,
                player_ids=[1, 2],
                league_id="00",
                workers=2,
            )

    def test_fetch_career_totals_parallel_handles_more_workers_than_players(self) -> None:
        fake_client = FakeClient(
            players=[],
            career_rows_by_player={
                1: [career_total(1)],
                2: [career_total(2)],
            },
        )

        results = fetch_career_totals_parallel(
            client=fake_client,
            player_ids=[1, 2],
            league_id="00",
            workers=99,
        )

        self.assertEqual(set(results), {1, 2})


if __name__ == "__main__":
    unittest.main()
