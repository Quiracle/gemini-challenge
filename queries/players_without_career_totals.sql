SELECT
    p.player_id,
    p.display_first_last,
    p.current_team_id,
    p.source_season
FROM players AS p
LEFT JOIN career_totals_regular_season AS c
    ON p.player_id = c.player_id
WHERE c.player_id IS NULL
ORDER BY p.display_first_last;
