from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Iterable
from typing import Any

import requests

from nba_ingestion.constants import (
    ALL_PLAYERS_ENDPOINT,
    ALL_PLAYERS_RESULT_SET,
    CAREER_STATS_ENDPOINT,
    CAREER_TOTALS_RESULT_SET,
    NBA_STATS_HEADERS,
)
from nba_ingestion.schema import (
    CAREER_TOTAL_COLUMNS,
    KNOWN_PLAYER_COLUMNS,
    REQUIRED_PLAYER_COLUMNS,
)

LOGGER = logging.getLogger(__name__)
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class ApiShapeError(RuntimeError):
    """Raised when an NBA API response does not match the expected result shape."""


class NbaStatsClient:
    def __init__(
        self,
        timeout_seconds: float = 30.0,
        retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self._thread_local = threading.local()

    def fetch_players(self, season: str, league_id: str) -> list[dict[str, Any]]:
        payload = self._get_json(
            ALL_PLAYERS_ENDPOINT,
            params={
                "leagueId": league_id,
                "season": season,
                "isOnlyCurrentSeason": "1",
            },
        )
        result_set = find_result_set(payload, ALL_PLAYERS_RESULT_SET)
        validate_result_set(
            result_set=result_set,
            required_columns=REQUIRED_PLAYER_COLUMNS,
            known_columns=KNOWN_PLAYER_COLUMNS,
            dataset_name=ALL_PLAYERS_RESULT_SET,
        )
        return result_set_rows(result_set)

    def fetch_career_totals(
        self,
        player_id: int,
        league_id: str,
    ) -> list[dict[str, Any]]:
        payload = self._get_json(
            CAREER_STATS_ENDPOINT,
            params={
                "perMode": "Totals",
                "playerId": str(player_id),
                "leagueId": league_id,
            },
        )
        if not payload:
            LOGGER.warning(
                "Career stats endpoint returned empty JSON for player_id=%s; "
                "treating as no %s rows",
                player_id,
                CAREER_TOTALS_RESULT_SET,
            )
            return []
        result_set = find_result_set(payload, CAREER_TOTALS_RESULT_SET)
        validate_result_set(
            result_set=result_set,
            required_columns=CAREER_TOTAL_COLUMNS,
            known_columns=CAREER_TOTAL_COLUMNS,
            dataset_name=CAREER_TOTALS_RESULT_SET,
        )
        return result_set_rows(result_set)

    def _session(self) -> requests.Session:
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(NBA_STATS_HEADERS)
            self._thread_local.session = session
        return session

    def _get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            response: requests.Response | None = None
            try:
                response = self._session().get(
                    url,
                    params=params,
                    timeout=self.timeout_seconds,
                )
                if response.status_code in TRANSIENT_STATUSES:
                    raise requests.HTTPError(
                        f"transient HTTP {response.status_code}",
                        response=response,
                    )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ApiShapeError("Expected top-level JSON object from NBA API")
                return payload
            except requests.HTTPError as exc:
                last_error = exc
                status_code = response.status_code if response is not None else None
                if status_code not in TRANSIENT_STATUSES:
                    raise RuntimeError(
                        f"NBA API request failed with HTTP {status_code} for {url}"
                    ) from exc
            except (requests.RequestException, ValueError, ApiShapeError) as exc:
                last_error = exc

            if attempt == self.retries:
                break

            delay = self._retry_delay(attempt, response)
            LOGGER.warning(
                "Retrying NBA API request after attempt %s/%s failed: %s",
                attempt,
                self.retries,
                last_error,
            )
            time.sleep(delay)

        raise RuntimeError(
            f"NBA API request failed after {self.retries} attempts for {url}"
        ) from last_error

    def _retry_delay(
        self,
        attempt: int,
        response: requests.Response | None,
    ) -> float:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

        jitter = random.uniform(0, 0.25)
        return self.backoff_seconds * (2 ** (attempt - 1)) + jitter


def find_result_set(payload: dict[str, Any], name: str) -> dict[str, Any]:
    result_sets = payload.get("resultSets", payload.get("resultSet"))
    if isinstance(result_sets, dict):
        result_sets = [result_sets]
    if not isinstance(result_sets, list):
        raise ApiShapeError("NBA API response did not include resultSets/resultSet")

    for result_set in result_sets:
        if not isinstance(result_set, dict):
            continue
        result_name = result_set.get("name", result_set.get("Name"))
        if str(result_name).lower() == name.lower():
            return result_set

    available = [
        str(result_set.get("name", result_set.get("Name")))
        for result_set in result_sets
        if isinstance(result_set, dict)
    ]
    raise ApiShapeError(f"Missing expected result set {name!r}; available={available}")


def validate_result_set(
    result_set: dict[str, Any],
    required_columns: Iterable[str],
    known_columns: Iterable[str],
    dataset_name: str,
) -> None:
    headers = result_set.get("headers")
    if not isinstance(headers, list) or not all(isinstance(col, str) for col in headers):
        raise ApiShapeError(f"{dataset_name} did not include a valid headers list")

    missing = [column for column in required_columns if column not in headers]
    if missing:
        raise ApiShapeError(f"{dataset_name} is missing expected columns: {missing}")

    known = set(known_columns)
    extra = [column for column in headers if column not in known]
    if extra:
        LOGGER.warning(
            "%s returned unexpected extra columns: %s",
            dataset_name,
            extra,
        )

    row_set = result_set.get("rowSet")
    if not isinstance(row_set, list):
        raise ApiShapeError(f"{dataset_name} did not include a valid rowSet list")


def result_set_rows(result_set: dict[str, Any]) -> list[dict[str, Any]]:
    headers = result_set["headers"]
    rows: list[dict[str, Any]] = []
    for row_index, row in enumerate(result_set["rowSet"], start=1):
        if not isinstance(row, list):
            raise ApiShapeError(f"row {row_index} was not a list")
        if len(row) != len(headers):
            raise ApiShapeError(
                f"row {row_index} had {len(row)} values for {len(headers)} headers"
            )
        rows.append(dict(zip(headers, row, strict=True)))
    return rows
