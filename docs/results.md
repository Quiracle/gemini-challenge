# Results

These results were generated from a full ingestion run into `data/nba_gleague.duckdb` using the default 2022-23 player-list endpoint.

The queries live in `queries/`.

## Data Quality Summary

Query: `queries/data_quality_summary.sql`

| Metric | Value |
|---|---:|
| `career_totals_regular_season.distinct_keys` | 94 |
| `career_totals_regular_season.null_key_rows` | 0 |
| `career_totals_regular_season.row_count` | 94 |
| `players.distinct_player_ids` | 99 |
| `players.null_key_rows` | 0 |
| `players.row_count` | 99 |
| `players_without_career_totals` | 5 |
| `teams.distinct_team_ids` | 28 |
| `teams.null_key_rows` | 0 |
| `teams.row_count` | 28 |

The loaded tables reconcile cleanly: no duplicate keys and no null key rows were found in the generated database. Five players from the 2022-23 player-list population did not have a `CareerTotalsRegularSeason` row.

## Players Without Career Totals

Query: `queries/players_without_career_totals.sql`

| Player ID | Player | Current Team ID | Source Season |
|---:|---|---:|---|
| 1628435 | Chance Comanche | 0 | 2022-23 |
| 1629714 | Jarrell Brantley | 0 | 2022-23 |
| 1631160 | Jordan Hall | 0 | 2022-23 |
| 1631171 | Justin Lewis | 1610612741 | 2022-23 |
| 1630701 | Michael Foster Jr. | 0 | 2022-23 |

This matches the documented API caveat: a player can appear in the current-player endpoint while their career endpoint returns no usable career-total row.

## Career Team ID Distribution

Query: `queries/career_team_id_distribution.sql`

| Career Team ID | Team Abbreviation | Career Rows | Career Games Played | Career Points |
|---:|---|---:|---:|---:|
| 0 | UNKNOWN | 94 | 29,744 | 282,247 |

All loaded `CareerTotalsRegularSeason` rows have `TEAM_ID = 0`. This indicates the career endpoint is returning aggregate career totals rather than team-split career totals. For that reason, team summaries below use the current team from the player-list endpoint, not `career_totals_regular_season.team_id`.

## Top Career Scorers

Query: `queries/top_career_scorers.sql`

| Player ID | Player | Current Team | GP | PTS | REB | AST |
|---:|---|---|---:|---:|---:|---:|
| 200752 | Rudy Gay | UTA | 1,120 | 17,642 | 6,283 | 2,280 |
| 201933 | Blake Griffin | BOS | 765 | 14,513 | 6,109 | 3,055 |
| 202689 | Kemba Walker | 0 | 750 | 14,486 | 2,831 | 3,938 |
| 2738 | Andre Iguodala | GSW | 1,231 | 13,968 | 6,047 | 5,147 |
| 201609 | Goran Dragic | MIL | 946 | 12,568 | 2,816 | 4,405 |
| 202322 | John Wall | 0 | 647 | 12,088 | 2,704 | 5,735 |
| 201586 | Serge Ibaka | 0 | 919 | 11,028 | 6,513 | 749 |
| 201588 | George Hill | IND | 915 | 9,545 | 2,731 | 2,807 |
| 201571 | D.J. Augustin | HOU | 976 | 9,259 | 1,805 | 3,761 |
| 203506 | Victor Oladipo | MIA | 504 | 8,503 | 2,245 | 1,970 |

## Top Career Games Played

Query: `queries/top_career_games_played.sql`

| Player ID | Player | Current Team | GP | Minutes | PTS |
|---:|---|---|---:|---:|---:|
| 2738 | Andre Iguodala | GSW | 1,231 | 39,505.0 | 13,968 |
| 200752 | Rudy Gay | UTA | 1,120 | 34,560.0 | 17,642 |
| 201577 | Robin Lopez | CLE | 992 | 20,935.0 | 8,326 |
| 201571 | D.J. Augustin | HOU | 976 | 22,852.0 | 9,259 |
| 201609 | Goran Dragic | MIL | 946 | 25,602.0 | 12,568 |
| 201586 | Serge Ibaka | 0 | 919 | 25,127.0 | 11,028 |
| 201588 | George Hill | IND | 915 | 24,500.0 | 9,545 |
| 2617 | Udonis Haslem | MIA | 879 | 21,721.0 | 6,586 |
| 201980 | Danny Green | CLE | 832 | 20,898.0 | 7,204 |
| 202397 | Ish Smith | DEN | 805 | 15,492.0 | 5,712 |

## Current-Team Career Summary

Query: `queries/current_team_career_summary.sql`

| Current Team | Players | With Career Totals | Without Career Totals | Career PTS | Career REB | Career AST |
|---|---:|---:|---:|---:|---:|---:|
| UNKNOWN_OR_UNASSIGNED | 28 | 24 | 4 | 58,005 | 23,128 | 14,175 |
| HOU | 5 | 5 | 0 | 16,588 | 5,860 | 5,014 |
| PHI | 5 | 5 | 0 | 14,003 | 7,127 | 1,784 |
| CHA | 4 | 4 | 0 | 1,999 | 694 | 682 |
| CHI | 4 | 3 | 1 | 500 | 277 | 74 |
| CLE | 4 | 4 | 0 | 25,570 | 10,975 | 8,169 |
| DAL | 3 | 3 | 0 | 2,000 | 789 | 895 |
| DET | 3 | 3 | 0 | 5,252 | 2,360 | 971 |
| GSW | 3 | 3 | 0 | 18,724 | 9,319 | 5,764 |
| MIL | 3 | 3 | 0 | 15,249 | 4,619 | 4,838 |
| MIN | 3 | 3 | 0 | 8,212 | 2,100 | 1,936 |
| SAS | 3 | 3 | 0 | 6,643 | 5,073 | 1,208 |
| TOR | 3 | 3 | 0 | 13,114 | 5,409 | 2,612 |
| UTA | 3 | 3 | 0 | 18,544 | 6,934 | 2,657 |
| WAS | 3 | 3 | 0 | 2,403 | 530 | 472 |
| BKN | 2 | 2 | 0 | 6,182 | 1,765 | 972 |
| BOS | 2 | 2 | 0 | 14,656 | 6,190 | 3,074 |
| DEN | 2 | 2 | 0 | 5,739 | 1,949 | 3,049 |
| IND | 2 | 2 | 0 | 9,577 | 2,739 | 2,816 |
| LAL | 2 | 2 | 0 | 1,623 | 959 | 373 |
| MIA | 2 | 2 | 0 | 15,089 | 8,036 | 2,703 |
| NYK | 2 | 2 | 0 | 1,876 | 786 | 364 |
| POR | 2 | 2 | 0 | 2,874 | 1,777 | 901 |
| SAC | 2 | 2 | 0 | 3,210 | 1,148 | 1,894 |
| ATL | 1 | 1 | 0 | 4 | 2 | 0 |
| NOP | 1 | 1 | 0 | 2,524 | 1,982 | 364 |
| ORL | 1 | 1 | 0 | 4,040 | 1,718 | 1,708 |
| PHX | 1 | 1 | 0 | 8,047 | 2,061 | 936 |
