SELECT
    c.team_id,
    COALESCE(t.team_abbreviation, 'UNKNOWN') AS team_abbreviation,
    COUNT(*) AS career_total_rows,
    SUM(c.gp) AS career_games_played,
    SUM(c.pts) AS career_points
FROM career_totals_regular_season AS c
LEFT JOIN teams AS t
    ON c.team_id = t.team_id
GROUP BY
    c.team_id,
    COALESCE(t.team_abbreviation, 'UNKNOWN')
ORDER BY
    career_total_rows DESC,
    c.team_id;
