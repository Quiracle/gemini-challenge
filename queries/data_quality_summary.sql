SELECT
    'players.row_count' AS metric,
    COUNT(*) AS value
FROM players

UNION ALL

SELECT
    'players.distinct_player_ids' AS metric,
    COUNT(DISTINCT player_id) AS value
FROM players

UNION ALL

SELECT
    'players.null_key_rows' AS metric,
    COUNT(*) AS value
FROM players
WHERE player_id IS NULL

UNION ALL

SELECT
    'teams.row_count' AS metric,
    COUNT(*) AS value
FROM teams

UNION ALL

SELECT
    'teams.distinct_team_ids' AS metric,
    COUNT(DISTINCT team_id) AS value
FROM teams

UNION ALL

SELECT
    'teams.null_key_rows' AS metric,
    COUNT(*) AS value
FROM teams
WHERE team_id IS NULL

UNION ALL

SELECT
    'career_totals_regular_season.row_count' AS metric,
    COUNT(*) AS value
FROM career_totals_regular_season

UNION ALL

SELECT
    'career_totals_regular_season.distinct_keys' AS metric,
    COUNT(DISTINCT (player_id, league_id, team_id)) AS value
FROM career_totals_regular_season

UNION ALL

SELECT
    'career_totals_regular_season.null_key_rows' AS metric,
    COUNT(*) AS value
FROM career_totals_regular_season
WHERE player_id IS NULL
    OR league_id IS NULL
    OR team_id IS NULL

UNION ALL

SELECT
    'players_without_career_totals' AS metric,
    COUNT(*) AS value
FROM players AS p
LEFT JOIN career_totals_regular_season AS c
    ON p.player_id = c.player_id
WHERE c.player_id IS NULL
ORDER BY metric;
