from __future__ import annotations

ALL_PLAYERS_ENDPOINT = "https://stats.gleague.nba.com/stats/commonallplayers/"
CAREER_STATS_ENDPOINT = "https://stats.gleague.nba.com/stats/playercareerstats/"

DEFAULT_SEASON = "2022-23"
DEFAULT_LEAGUE_ID = "00"
DEFAULT_DB_PATH = "data/nba_gleague.duckdb"

ALL_PLAYERS_RESULT_SET = "CommonAllPlayers"
CAREER_TOTALS_RESULT_SET = "CareerTotalsRegularSeason"

NBA_STATS_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Origin": "https://gleague.nba.com",
    "Referer": "https://gleague.nba.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}
