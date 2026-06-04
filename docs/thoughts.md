## Initial thoughts

The problem talks about getting the current player and then says season 2022-23. Let's interpret it as it wanting us to take 2022-23 as the current season.

we only need 2 queries:

- all players to get all the ids
- player data for all the Careen regular season totals.

player data returns a lot of stats, depending on regular/post/allstart season. Then there are total aggregates. We only need to take the CareerTotalsRegularSeason.

At a first glance there is a weird behaviour. player with PERSON_ID 201571 is listed on the season 2022-23 query but on their stats query they don't have any entrie with SEASON_ID 2022-23, only 2021-22. TODO: Check if there is documentation and it makes sense.

Query is for common all players but anyways check if it's only active players just in case.

With this definition we have these fields, with codex explanations and types: 
| Field | Type | Meaning |
|---|---:|---|
| `PLAYER_ID` | `int` | Unique NBA player identifier. |
| `LEAGUE_ID` | `string` | League code, usually `00` for the NBA. |
| `TEAM_ID` | `int` | Team identifier associated with the stats row. |
| `GP` | `int` | Games played. |
| `GS` | `int` | Games started. |
| `MIN` | `float` | Total minutes played. |
| `FGM` | `int` | Field goals made. |
| `FGA` | `int` | Field goals attempted. |
| `FG_PCT` | `float` | Field goal percentage: `FGM / FGA`. |
| `FG3M` | `int` | 3-point field goals made. |
| `FG3A` | `int` | 3-point field goals attempted. |
| `FG3_PCT` | `float` | 3-point percentage: `FG3M / FG3A`. |
| `FTM` | `int` | Free throws made. |
| `FTA` | `int` | Free throws attempted. |
| `FT_PCT` | `float` | Free throw percentage: `FTM / FTA`. |
| `OREB` | `int` | Offensive rebounds. |
| `DREB` | `int` | Defensive rebounds. |
| `REB` | `int` | Total rebounds: `OREB + DREB`. |
| `AST` | `int` | Assists. |
| `STL` | `int` | Steals. |
| `BLK` | `int` | Blocks. |
| `TOV` | `int` | Turnovers. |
| `PF` | `int` | Personal fouls. |
| `PTS` | `int` | Total points scored. |

Since its OLAP, a star schema would be fine to query this stats. It's historic so it's not that important because we won't be doing heavy operations but anyways.

We will use dimension tables for player, league, team.

The fact table will contain all the rest of the information. We don't really need the dimension tables with this specifications, but not even having the name of the player or team is uninformative.

We could ignore league id, this will be decided later. I don't like losing information.

