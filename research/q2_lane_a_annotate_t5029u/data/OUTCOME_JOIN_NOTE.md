# OUTCOME_JOIN_NOTE — DEV_RESEARCH · CERT=0

`games.csv` sha256 prefix **4fe1cdd7** (n=2992, REG+post 2013–2023) is the
primary Phase B input. Columns include `season,week,game_id,home,away,kickoff_utc,record_entering_* ,market_spread_home`.
There is **no** `home_score`, `away_score`, `margin`, or `wl_diff` column.

The gated hist index `historical_oos_games.csv` tip **1ee90fac** was **not**
used as the scored experiment frame. A six-column extract for seasons
**2013–2022 only** was written:

`season,week,home,away,home_score,away_score`

- 2023 reserve / 2024–25 sealed / 2026 rows dropped (871 rows skipped)
- every `trailing_*`, `packaged_*`, `*_err`, EPA column dropped
- identity keys join 2707/2707 onto `games.csv` 2013–2022

Extract sha256: `50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081`

This is documented for Alex RO / CoS under gate **83646d78**. If CoS rules the
score-only extract is still “scored reuse,” discard EVAL numbers and keep only
the code + FROZEN_CONFIG process.

Do not acquire new data. Do not load PBP.
