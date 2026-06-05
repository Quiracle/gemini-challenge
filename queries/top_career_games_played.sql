SELECT
    p.player_id,
    p.display_first_last,
    COALESCE(t.team_abbreviation, CAST(p.current_team_id AS VARCHAR)) AS current_team,
    c.gp,
    ROUND(c.min, 1) AS minutes,
    c.pts
FROM career_totals_regular_season AS c
INNER JOIN players AS p
    ON c.player_id = p.player_id
LEFT JOIN teams AS t
    ON p.current_team_id = t.team_id
ORDER BY
    c.gp DESC,
    p.display_first_last
LIMIT 10;
