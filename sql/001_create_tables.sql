CREATE TABLE IF NOT EXISTS teams (
    team_id BIGINT PRIMARY KEY,
    team_abbreviation VARCHAR,
    team_city VARCHAR,
    team_name VARCHAR
);

CREATE TABLE IF NOT EXISTS players (
    player_id BIGINT PRIMARY KEY,
    display_first_last VARCHAR NOT NULL,
    display_last_comma_first VARCHAR,
    roster_status INTEGER,
    from_year INTEGER,
    to_year INTEGER,
    current_team_id BIGINT,
    games_played_flag VARCHAR,
    source_season VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS career_totals_regular_season (
    player_id BIGINT NOT NULL,
    league_id VARCHAR NOT NULL,
    team_id BIGINT NOT NULL,
    gp INTEGER,
    gs INTEGER,
    min DOUBLE,
    fgm INTEGER,
    fga INTEGER,
    fg_pct DOUBLE,
    fg3m INTEGER,
    fg3a INTEGER,
    fg3_pct DOUBLE,
    ftm INTEGER,
    fta INTEGER,
    ft_pct DOUBLE,
    oreb INTEGER,
    dreb INTEGER,
    reb INTEGER,
    ast INTEGER,
    stl INTEGER,
    blk INTEGER,
    tov INTEGER,
    pf INTEGER,
    pts INTEGER,
    PRIMARY KEY (player_id, league_id, team_id)
);
