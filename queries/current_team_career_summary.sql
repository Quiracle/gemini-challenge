SELECT
    CASE
        WHEN p.current_team_id = 0 THEN 'UNKNOWN_OR_UNASSIGNED'
        ELSE COALESCE(t.team_abbreviation, CAST(p.current_team_id AS VARCHAR))
    END AS current_team,
    COUNT(*) AS player_count,
    COUNT(c.player_id) AS players_with_career_totals,
    COUNT(*) - COUNT(c.player_id) AS players_without_career_totals,
    SUM(c.pts) AS career_points,
    SUM(c.reb) AS career_rebounds,
    SUM(c.ast) AS career_assists
FROM players AS p
LEFT JOIN career_totals_regular_season AS c
    ON p.player_id = c.player_id
LEFT JOIN teams AS t
    ON p.current_team_id = t.team_id
GROUP BY
    CASE
        WHEN p.current_team_id = 0 THEN 'UNKNOWN_OR_UNASSIGNED'
        ELSE COALESCE(t.team_abbreviation, CAST(p.current_team_id AS VARCHAR))
    END
ORDER BY
    player_count DESC,
    current_team;
