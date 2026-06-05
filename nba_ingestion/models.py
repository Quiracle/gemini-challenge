from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nba_ingestion.constants import DEFAULT_DB_PATH, DEFAULT_LEAGUE_ID, DEFAULT_SEASON


class DataQualityError(RuntimeError):
    """Raised when source or loaded data fails a required DQM check."""


@dataclass(frozen=True)
class PipelineConfig:
    db_path: Path = Path(DEFAULT_DB_PATH)
    season: str = DEFAULT_SEASON
    league_id: str = DEFAULT_LEAGUE_ID
    workers: int = 8
    timeout_seconds: float = 30.0
    retries: int = 3
    backoff_seconds: float = 1.0
    max_players: int | None = None


@dataclass(frozen=True)
class DqmCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PipelineResult:
    db_path: Path
    source_player_count: int
    loaded_player_count: int
    loaded_team_count: int
    source_career_row_count: int
    loaded_career_row_count: int
    missing_career_player_ids: tuple[int, ...]
    dqm_checks: tuple[DqmCheck, ...]
    warnings: tuple[str, ...]
