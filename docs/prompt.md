You are implementing a small data engineering challenge in this repository.

Read these files first and use them as source-of-truth context before making changes:
- `docs/Gemini Data Engineering Technical Challenge.pdf`
- `docs/thoughts.md`
- `README.md`

Your job is to implement the challenge end-to-end in code, but keep the solution lean and easy to run locally.

## Objective
Build a Python-based data ingestion project that:

1. Calls the NBA players endpoint for the 2022-23 season:
   `https://stats.gleague.nba.com/stats/commonallplayers/?leagueId=00&season=2022-23&isOnlyCurrentSeason=1`

2. For each returned player, calls the player career stats endpoint:
   `https://stats.gleague.nba.com/stats/playercareerstats/?perMode=Totals&playerId={person_id}&leagueId=00`

3. Extracts and stores only the `CareerTotalsRegularSeason` dataset from the career stats response.

4. Stores the data in a normalized database schema.

5. Includes all code, SQL DDL for dependent objects, and a short architecture/project explanation.

## Required implementation choices
Use these choices unless the repository clearly forces a different shape:

- Language: Python
- Database: DuckDB
- Delivery style: script-based project, not notebook-first
- Schema shape: practical normalized 3-table design
  - `players`
  - `teams`
  - `career_totals_regular_season`
- Keep `LEAGUE_ID` as a preserved code column, not a separate dimension table unless truly necessary.

## Guardrails
- Do not overengineer the project.
- Optimize for local simplicity and reviewer ergonomics.
- The solution should be runnable with minimal setup.
- Keep the implementation aligned tightly to the brief.
- Do not fetch or model unrelated NBA datasets.

## Data handling rules
- The player list is defined by the provided 2022-23 endpoint. Treat that as the challenge’s operational definition of “current players.”
- From the player career endpoint, store only `CareerTotalsRegularSeason`.
- Preserve the stat fields discussed in `docs/thoughts.md`.
- Use appropriate types:
  - `PLAYER_ID`: int
  - `LEAGUE_ID`: string
  - remaining stat fields: int or float as appropriate
- Preserve `TEAM_ID` from the career totals row.
- If the API returns oddities or inconsistencies, do not silently discard them. Load the best valid data available and document the behavior.

## Engineering depth to include
Add a small but meaningful amount of stronger DE practice:

- Parallelize per-player career-stat API calls with bounded concurrency.
- Make the pipeline idempotent so reruns do not duplicate rows.
- Add lightweight DQM checks:
  - row-count checks
  - duplicate-key checks
  - null checks on key identifiers
  - source vs loaded reconciliation
- Add lightweight schema-drift protection:
  - validate expected columns from the API
  - fail clearly or warn clearly when the response shape changes
- Add reasonable retry/backoff behavior for API calls.

## Expected outputs
Create the implementation artifacts needed for a complete submission, including:

- Python ingestion/orchestration code
- SQL DDL scripts
- dependency file(s)
- a README or short project description explaining:
  - architecture
  - design choices
  - assumptions
  - how to run it
  - any notable API caveats

## Behavior expectations
- Explore the repo first before editing.
- Reuse and respect anything already present.
- Keep the code clean and readable.
- Prefer a small number of clear modules over a large framework.
- Include brief comments only where they help.
- Verify your work with tests or runnable checks where practical.
- If you make an assumption, state it explicitly in the documentation.

## Important caveat already identified
One known issue from `docs/thoughts.md` is that a player may appear in the 2022-23 player-list endpoint but not have matching 2022-23 season detail in the career response. Handle this pragmatically:
- still load the returned career totals if present
- do not require season-by-season agreement to accept the record
- document the inconsistency

## What I want from you
1. Inspect the repository and summarize the current starting point.
2. Propose a compact implementation structure.
3. Implement the solution.
4. Run relevant checks/tests.
5. Summarize what you changed, how to run it, and any assumptions or limitations.

Do not ask broad open-ended questions unless blocked by a real decision that cannot be inferred from the repo or this prompt.