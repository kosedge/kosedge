# SportsData.io API Replay – Capture Plan

Use Replay to **grab as much data as possible** across all sports we cover and save it for future models.

**Quick start:** 1) Start a Replay in the [Replay Dashboard](https://sportsdata.io/members/replays) (pick league + package). 2) Copy the replay API key. 3) Run: `export SPORTSDATA_REPLAY_KEY="key"` then `pnpm run capture:replay -- --league nfl --package nfl_week1` (from `apps/web`). 4) Check `data/raw/sportsdata_replay/nfl/nfl_week1/` (season/week/date JSONs and `by_game/{id}/` for play-by-play, box score, etc.). 5) Repeat for other leagues/packages; add endpoint paths from each package detail page to `data/raw/sportsdata_replay_endpoints.json`.

**Segment levels (most granular first):** play-by-play / pitch-by-pitch (MLB) → box score, score summary (game) → games by date, odds by date → scores by week, odds by week (NFL/CFB) → standings, current season/week. Replay is free and unlimited; each “replay” is a fixed recording (e.g. NFL Week 1, NBA Playoffs). You run one replay per package, capture every endpoint that package recorded, then start the next replay.

## Sports we cover (priority)

| Our sport | SportsData.io league | Replay packages to use                                  |
| --------- | -------------------- | ------------------------------------------------------- |
| NCAAM     | NCAA Basketball      | Regular season + conference + March Madness if separate |
| NBA       | NBA                  | Regular season, Playoffs                                |
| NFL       | NFL                  | Regular season weeks, Playoffs                          |
| MLB       | MLB                  | Regular season, Playoffs                                |
| NHL       | NHL                  | Regular season, Playoffs                                |
| CFB       | NCAA Football        | Regular season (excl. bowls if separate package)        |
| WNBA      | WNBA                 | Regular season, Playoffs                                |

**Extra:** Grab **all College Basketball** replay packages you see (multiple conferences, women’s, etc.) even if we don’t surface them yet.

---

## Step-by-step (per replay)

### 1. Create a replay (Replay Dashboard)

1. Go to [Replay Dashboard](https://sportsdata.io/members/replays?launch_window=0) (log in if needed).
2. Click **Start a Replay**.
3. Select **league** (e.g. NFL, NBA, NCAA Basketball).
4. Select **recording package** (e.g. “NFL Week 1”, “NBA Playoffs 2023”). Prefer packages that cover full seasons or big events.
5. Choose **start time** in the recording (e.g. start of day 1).
6. Create the replay → you get a **replay-specific API key**. Copy it.

### 2. Get package context (metadata + package detail)

- **Metadata (current “time” inside the replay):**  
  `GET https://replay.sportsdata.io/api/metadata?key=YOUR_REPLAY_KEY`  
  Use the returned date/time for any date-specific endpoints (e.g. scores by date).
- **Package detail page:** From the Replay UI, open the **package detail** for this recording. Note:
  - Which **endpoints** were recorded (e.g. scores, play-by-play, odds, standings).
  - Which **parameters** were recorded (e.g. season `2023reg`, week `1`, or dates).

### 3. Run the capture script

From repo root (or `apps/web`):

```bash
export SPORTSDATA_REPLAY_KEY="your_replay_key_from_step_1"
# Optional: override package name for folder (defaults to "default")
export REPLAY_PACKAGE_NAME="nfl_2023_week1"

# Capture all endpoints in the config for this league (or use --league nfl, nba, ncaab, etc.)
.venv/bin/python apps/web/scripts/capture_sportsdata_replay.py --league nfl --package "nfl_2023_week1"
```

The script will:

- Call the **metadata** endpoint and use the replay “current” date/time.
- For the chosen league, request every configured endpoint (scores, standings, box scores, play-by-play, odds, etc.) with the right season/week/date from metadata (or from config).
- Save each response under `apps/web/data/raw/sportsdata_replay/{league}/{package_name}/` so you keep one folder per replay package.

### 4. Repeat for every package you want

- Create the next replay (e.g. NBA Playoffs, then NCAA Basketball full season, etc.).
- Set `SPORTSDATA_REPLAY_KEY` and `REPLAY_PACKAGE_NAME`, run the script with the matching `--league`.
- Keep the replay key valid for the duration of the run (don’t delete the replay until capture is done).

---

## What to capture (endpoints to aim for)

For each league, try to hit every endpoint type the package actually recorded. Typical categories:

- **Scores** – by week, by date, by season.
- **Standings** – current standings at that replay “time”.
- **Schedules** – full season or by week.
- **Box scores** – per game (if you have game IDs from scores/schedule).
- **Play-by-play** – if recorded (often per game or delta).
- **Odds** – game odds, lines by week/date (if in the package).
- **Injuries / rosters / depth charts** – if available in the package.

The script uses a **config file** of endpoint paths per league: `apps/web/data/raw/sportsdata_replay_endpoints.json`. After you open a package’s “package detail” page, **copy the exact paths** from that page and add them to the config (paths can differ by API version, e.g. v3 vs v4). Use placeholders `{season}`, `{week}`, `{date}` so the script can fill them from metadata or from `package_defaults`. Example paths:

- `api/v3/nfl/scores/json/ScoresByWeek/{season}/{week}`
- `api/v3/nfl/odds/json/GameOddsByWeek/{season}/{week}`
- `api/v3/ncaab/scores/json/GamesByDate/{date}`

---

## Where data is saved

- **Base dir:** `apps/web/data/raw/sportsdata_replay/`
- **Season / week / date level:** `{league}/{package_name}/{slug}.json`  
  e.g. `nfl/nfl_2023_week1/standings.json`, `scores_by_week.json`, `odds_by_week.json`
- **Game level (play-by-play, pitch-by-pitch, box score):** `{league}/{package_name}/by_game/{gameid}/{slug}.json`  
  e.g. `nfl/.../by_game/12345/playbyplay.json`, `mlb/.../by_game/67890/pitch_by_pitch.json`

Data is segmented as: **play-by-play (and pitch-by-pitch for MLB) → game → date → week → season**. The script first fetches week/date feeds to get game IDs, then requests every game-level endpoint for each game.

You can later:

- Point model/training code at these JSONs.
- Normalize them into Parquet or your DB for backtests and “future models” across all sports.

---

## Tips

1. **One replay at a time** – each key is tied to one recording; run the script to completion for that key, then create the next replay and repeat.
2. **CBB first** – we want “more college basketball data”; prioritize every NCAA Basketball (and women’s if available) package.
3. **Don’t skip “we might not use it”** – capture odds, play-by-play, injuries, etc. even if we don’t use them yet; the script is built to grab everything in the config.
4. **Package names** – use clear, stable names for `REPLAY_PACKAGE_NAME` (e.g. `nfl_2023_reg_week1`, `ncaab_2024_march_madness`) so folders are easy to find later.

---

## SportsData.io Free Trial (NCAAB)

With a **free trial key** you get **1,000 API calls/month** and ~100 calls/min. Data is scrambled but structure matches production — ideal for testing the pipeline, filling backtest margin gaps, and trying live odds/props.

**Script:** `apps/web/scripts/pull_sportsdata_cbb.py`

- **Key:** `SPORTSDATA_API_KEY` or `SPORTSDATA_REPLAY_KEY` in `.env.local`.
- **Results (backtest):** `pnpm run pull:cbb -- --results` → 2016–2025 season games (~10 calls), writes `data/processed/sportsdata_games_{season}.parquet` and `all_sportsdata_results_2016-2025.parquet`.
- **Today’s lines:** `pnpm run pull:cbb -- --today` → games + odds for today (2 calls), writes `data/raw/sportsdata_cbb/games_by_date_*.json`, `game_odds_by_date_*.json`.
- **Props:** `pnpm run pull:cbb -- --props --season 2025` → player season stats + projections (2 calls).

If you get 404s, set `SPORTSDATA_CBB_SLUG=ncaab` (default is `cbb`). Merge SportsData results into your backtest on date + teams; use today’s odds for a KosEdge board proof-of-concept.
