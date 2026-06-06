from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from nba_ingestion.constants import DEFAULT_DB_PATH, DEFAULT_LEAGUE_ID, DEFAULT_SEASON
from nba_ingestion.models import DataQualityError, PipelineConfig
from nba_ingestion.pipeline import run_pipeline

LOGGER = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest NBA/G League 2022-23 current-player career totals into DuckDB."
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB output path.")
    parser.add_argument("--season", default=DEFAULT_SEASON, help="Player-list season.")
    parser.add_argument("--league-id", default=DEFAULT_LEAGUE_ID, help="NBA league code.")
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Maximum concurrent player career-stat API calls.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Per-request timeout.",
    )
    parser.add_argument("--retries", type=int, default=3, help="API retry attempts.")
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=1.0,
        help="Initial exponential-backoff delay.",
    )
    parser.add_argument(
        "--max-players",
        type=int,
        default=None,
        help="Optional smoke-test limit; omit for the full challenge run.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    try:
        result = run_pipeline(
            PipelineConfig(
                db_path=Path(args.db_path),
                season=args.season,
                league_id=args.league_id,
                workers=args.workers,
                timeout_seconds=args.timeout_seconds,
                retries=args.retries,
                backoff_seconds=args.backoff_seconds,
                max_players=args.max_players,
            )
        )
    except (RuntimeError, DataQualityError) as exc:
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            LOGGER.exception("Pipeline failed")
        else:
            LOGGER.error("Pipeline failed: %s", exc)
            LOGGER.error("Rerun with --log-level DEBUG for the full traceback.")
        sys.exit(1)

    print(f"DuckDB database: {result.db_path}")
    print(
        "Loaded "
        f"{result.loaded_player_count} players, "
        f"{result.loaded_team_count} teams, "
        f"{result.loaded_career_row_count} career total rows."
    )
    if result.missing_career_player_ids:
        sample = ", ".join(str(player_id) for player_id in result.missing_career_player_ids[:10])
        print(
            "Players without CareerTotalsRegularSeason rows: "
            f"{len(result.missing_career_player_ids)}"
            f" (sample: {sample})"
        )
    if result.warnings:
        print(f"Warnings: {len(result.warnings)}")
    print("DQM checks:")
    for check in result.dqm_checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.name}: {check.detail}")


if __name__ == "__main__":
    main()
