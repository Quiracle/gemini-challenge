from __future__ import annotations

REQUIRED_PLAYER_COLUMNS = [
    "PERSON_ID",
    "DISPLAY_FIRST_LAST",
    "DISPLAY_LAST_COMMA_FIRST",
    "ROSTERSTATUS",
    "FROM_YEAR",
    "TO_YEAR",
    "TEAM_ID",
    "TEAM_CITY",
    "TEAM_NAME",
    "TEAM_ABBREVIATION",
    "GAMES_PLAYED_FLAG",
]

KNOWN_PLAYER_COLUMNS = REQUIRED_PLAYER_COLUMNS + [
    "PLAYERCODE",
    "PLAYER_SLUG",
    "TEAM_CODE",
    "TEAM_SLUG",
    "OTHERLEAGUE_EXPERIENCE_CH",
]

CAREER_TOTAL_COLUMNS = [
    "PLAYER_ID",
    "LEAGUE_ID",
    "TEAM_ID",
    "GP",
    "GS",
    "MIN",
    "FGM",
    "FGA",
    "FG_PCT",
    "FG3M",
    "FG3A",
    "FG3_PCT",
    "FTM",
    "FTA",
    "FT_PCT",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "PTS",
]

CAREER_INTEGER_COLUMNS = {
    "PLAYER_ID",
    "TEAM_ID",
    "GP",
    "GS",
    "FGM",
    "FGA",
    "FG3M",
    "FG3A",
    "FTM",
    "FTA",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "PTS",
}

CAREER_FLOAT_COLUMNS = {"MIN", "FG_PCT", "FG3_PCT", "FT_PCT"}

PLAYER_DB_COLUMNS = [
    "player_id",
    "display_first_last",
    "display_last_comma_first",
    "roster_status",
    "from_year",
    "to_year",
    "current_team_id",
    "games_played_flag",
    "source_season",
]

TEAM_DB_COLUMNS = ["team_id", "team_abbreviation", "team_city", "team_name"]

CAREER_DB_COLUMNS = [
    "player_id",
    "league_id",
    "team_id",
    "gp",
    "gs",
    "min",
    "fgm",
    "fga",
    "fg_pct",
    "fg3m",
    "fg3a",
    "fg3_pct",
    "ftm",
    "fta",
    "ft_pct",
    "oreb",
    "dreb",
    "reb",
    "ast",
    "stl",
    "blk",
    "tov",
    "pf",
    "pts",
]
