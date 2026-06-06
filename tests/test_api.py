from __future__ import annotations

import unittest
from unittest import mock

import requests

from nba_ingestion.api import (
    ApiShapeError,
    NbaStatsClient,
    find_result_set,
    http_error_message,
    result_set_rows,
    validate_result_set,
)
from nba_ingestion.constants import ALL_PLAYERS_RESULT_SET, CAREER_TOTALS_RESULT_SET
from nba_ingestion.schema import (
    CAREER_TOTAL_COLUMNS,
    REQUIRED_PLAYER_COLUMNS,
)


PLAYER_VALUES = [
    201142,
    "Kevin Durant",
    "Durant, Kevin",
    1,
    "2007",
    "2024",
    1610612756,
    "Phoenix",
    "Suns",
    "PHX",
    "Y",
]

CAREER_VALUES = [
    201142,
    "00",
    0,
    1000,
    1000,
    36000.5,
    9000,
    18000,
    0.5,
    2000,
    5000,
    0.4,
    7000,
    8000,
    0.875,
    700,
    6500,
    7200,
    4500,
    1000,
    1100,
    3000,
    2000,
    29000,
]


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        payload: object | None = None,
        json_error: Exception | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = {} if payload is None else payload
        self.json_error = json_error
        self.headers = headers or {}

    def json(self) -> object:
        if self.json_error is not None:
            raise self.json_error
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}",
                response=self,
            )


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def get(self, url: str, params: dict[str, str], timeout: float) -> FakeResponse:
        self.calls.append((url, params, timeout))
        return self.responses.pop(0)


def result_set_payload(name: str, headers: list[str], rows: list[list[object]]) -> dict[str, object]:
    return {
        "resultSets": [
            {
                "name": name,
                "headers": headers,
                "rowSet": rows,
            }
        ]
    }


class ResultSetParsingTests(unittest.TestCase):
    def test_find_result_set_from_result_sets(self) -> None:
        payload = result_set_payload("CommonAllPlayers", ["PERSON_ID"], [[201142]])

        result_set = find_result_set(payload, "CommonAllPlayers")

        self.assertEqual(result_set["name"], "CommonAllPlayers")

    def test_find_result_set_supports_single_result_set_dict(self) -> None:
        payload = {
            "resultSet": {
                "name": "CareerTotalsRegularSeason",
                "headers": ["PLAYER_ID"],
                "rowSet": [[201142]],
            }
        }

        result_set = find_result_set(payload, "CareerTotalsRegularSeason")

        self.assertEqual(result_set["name"], "CareerTotalsRegularSeason")

    def test_find_result_set_requires_result_sets(self) -> None:
        with self.assertRaisesRegex(ApiShapeError, "resultSets/resultSet"):
            find_result_set({}, "CommonAllPlayers")

    def test_find_result_set_requires_expected_name(self) -> None:
        payload = result_set_payload("OtherDataset", ["PERSON_ID"], [[201142]])

        with self.assertRaisesRegex(ApiShapeError, "Missing expected result set"):
            find_result_set(payload, "CommonAllPlayers")


class ResultSetValidationTests(unittest.TestCase):
    def test_missing_required_columns_raise(self) -> None:
        result_set = {"headers": ["PERSON_ID"], "rowSet": [[201142]]}

        with self.assertRaisesRegex(ApiShapeError, "missing expected columns"):
            validate_result_set(
                result_set=result_set,
                required_columns=["PERSON_ID", "DISPLAY_FIRST_LAST"],
                known_columns=["PERSON_ID", "DISPLAY_FIRST_LAST"],
                dataset_name="CommonAllPlayers",
            )

    def test_extra_columns_warn_but_do_not_fail(self) -> None:
        result_set = {
            "headers": ["PERSON_ID", "DISPLAY_FIRST_LAST", "EXTRA"],
            "rowSet": [[201142, "Kevin Durant", "ignored"]],
        }

        with self.assertLogs("nba_ingestion.api", level="WARNING") as logs:
            validate_result_set(
                result_set=result_set,
                required_columns=["PERSON_ID", "DISPLAY_FIRST_LAST"],
                known_columns=["PERSON_ID", "DISPLAY_FIRST_LAST"],
                dataset_name="CommonAllPlayers",
            )

        self.assertIn("unexpected extra columns", "\n".join(logs.output))

    def test_non_list_headers_fail(self) -> None:
        result_set = {"headers": "PERSON_ID", "rowSet": []}

        with self.assertRaisesRegex(ApiShapeError, "headers list"):
            validate_result_set(result_set, [], [], "BadDataset")

    def test_non_list_row_set_fails(self) -> None:
        result_set = {"headers": [], "rowSet": "not rows"}

        with self.assertRaisesRegex(ApiShapeError, "rowSet list"):
            validate_result_set(result_set, [], [], "BadDataset")

    def test_row_length_mismatch_fails(self) -> None:
        result_set = {"headers": ["PERSON_ID", "DISPLAY_FIRST_LAST"], "rowSet": [[201142]]}

        with self.assertRaisesRegex(ApiShapeError, "had 1 values for 2 headers"):
            result_set_rows(result_set)

    def test_non_list_row_fails(self) -> None:
        result_set = {"headers": ["PERSON_ID"], "rowSet": [{"PERSON_ID": 201142}]}

        with self.assertRaisesRegex(ApiShapeError, "was not a list"):
            result_set_rows(result_set)


class NbaStatsClientTests(unittest.TestCase):
    def client_with_responses(self, responses: list[FakeResponse], retries: int = 1) -> NbaStatsClient:
        client = NbaStatsClient(retries=retries, backoff_seconds=0)
        client._thread_local.session = FakeSession(responses)
        return client

    def test_fetch_players_returns_rows(self) -> None:
        client = self.client_with_responses(
            [
                FakeResponse(
                    payload=result_set_payload(
                        ALL_PLAYERS_RESULT_SET,
                        REQUIRED_PLAYER_COLUMNS,
                        [PLAYER_VALUES],
                    )
                )
            ]
        )

        rows = client.fetch_players(season="2022-23", league_id="00")

        self.assertEqual(rows[0]["PERSON_ID"], 201142)
        self.assertEqual(rows[0]["DISPLAY_FIRST_LAST"], "Kevin Durant")

    def test_fetch_career_totals_returns_rows(self) -> None:
        client = self.client_with_responses(
            [
                FakeResponse(
                    payload=result_set_payload(
                        CAREER_TOTALS_RESULT_SET,
                        CAREER_TOTAL_COLUMNS,
                        [CAREER_VALUES],
                    )
                )
            ]
        )

        rows = client.fetch_career_totals(player_id=201142, league_id="00")

        self.assertEqual(rows[0]["PLAYER_ID"], 201142)
        self.assertEqual(rows[0]["PTS"], 29000)

    def test_empty_career_payload_returns_no_rows_and_warns(self) -> None:
        client = self.client_with_responses([FakeResponse(payload={})])

        with self.assertLogs("nba_ingestion.api", level="WARNING") as logs:
            rows = client.fetch_career_totals(player_id=201142, league_id="00")

        self.assertEqual(rows, [])
        self.assertIn("empty JSON", "\n".join(logs.output))

    def test_transient_failure_retries_and_then_succeeds(self) -> None:
        client = self.client_with_responses(
            [
                FakeResponse(status_code=500, payload={"error": "temporary"}),
                FakeResponse(
                    payload=result_set_payload(
                        ALL_PLAYERS_RESULT_SET,
                        REQUIRED_PLAYER_COLUMNS,
                        [PLAYER_VALUES],
                    )
                ),
            ],
            retries=2,
        )

        with (
            mock.patch("nba_ingestion.api.time.sleep"),
            mock.patch("nba_ingestion.api.random.uniform", return_value=0),
            mock.patch("nba_ingestion.api.LOGGER.warning"),
        ):
            rows = client.fetch_players(season="2022-23", league_id="00")

        self.assertEqual(rows[0]["PERSON_ID"], 201142)
        self.assertEqual(len(client._thread_local.session.calls), 2)

    def test_repeated_transient_failures_raise_after_retries(self) -> None:
        client = self.client_with_responses(
            [
                FakeResponse(status_code=500, payload={"error": "temporary"}),
                FakeResponse(status_code=500, payload={"error": "still temporary"}),
            ],
            retries=2,
        )

        with (
            mock.patch("nba_ingestion.api.time.sleep"),
            mock.patch("nba_ingestion.api.random.uniform", return_value=0),
            mock.patch("nba_ingestion.api.LOGGER.warning"),
            self.assertRaisesRegex(RuntimeError, "failed after 2 attempts"),
        ):
            client.fetch_players(season="2022-23", league_id="00")

    def test_non_transient_http_failure_raises_immediately(self) -> None:
        client = self.client_with_responses(
            [FakeResponse(status_code=404, payload={"error": "not found"})],
            retries=3,
        )

        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            client.fetch_players(season="2022-23", league_id="00")

        self.assertEqual(len(client._thread_local.session.calls), 1)

    def test_http_403_message_includes_rate_limit_guidance(self) -> None:
        message = http_error_message(403, "https://stats.gleague.nba.com/stats/test")

        self.assertIn("Access Denied", message)
        self.assertIn("temporary IP blocking", message)
        self.assertIn("--workers", message)

    def test_http_403_failure_raises_with_guidance(self) -> None:
        client = self.client_with_responses(
            [FakeResponse(status_code=403, payload={"error": "forbidden"})],
            retries=3,
        )

        with self.assertRaisesRegex(RuntimeError, "Access Denied"):
            client.fetch_players(season="2022-23", league_id="00")

        self.assertEqual(len(client._thread_local.session.calls), 1)

    def test_invalid_json_raises_after_retries(self) -> None:
        client = self.client_with_responses(
            [
                FakeResponse(json_error=ValueError("bad json")),
                FakeResponse(json_error=ValueError("still bad")),
            ],
            retries=2,
        )

        with (
            mock.patch("nba_ingestion.api.time.sleep"),
            mock.patch("nba_ingestion.api.random.uniform", return_value=0),
            mock.patch("nba_ingestion.api.LOGGER.warning"),
            self.assertRaisesRegex(RuntimeError, "failed after 2 attempts"),
        ):
            client.fetch_players(season="2022-23", league_id="00")

    def test_top_level_non_dict_json_raises_after_retries(self) -> None:
        client = self.client_with_responses([FakeResponse(payload=[])], retries=1)

        with self.assertRaisesRegex(RuntimeError, "failed after 1 attempts"):
            client.fetch_players(season="2022-23", league_id="00")


if __name__ == "__main__":
    unittest.main()
