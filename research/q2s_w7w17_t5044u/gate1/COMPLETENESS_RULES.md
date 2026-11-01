# Completeness rules — sealed before PBP (t5044u Gate 1)

Deterministic. Fail-closed. No last-played substitution, fills, replacement
games, or outcome-based exclusion.

## Universe

Every `games.csv` **4fe1cdd7** row with `season=2017` and `week∈[7,17]`.
`N=165` (W7=15, W8=13, W9=13, W10=14, W11=14, W12–17=16). Week ≤ 17.
Season ≥ 2024 aborts. Missing `kickoff_utc` is a refuse (do not impute).

Identity columns read: `season,week,game_id,home,away,kickoff_utc` only.

## Rules (apply later at recon; identity does not drop)

1. **Zero completed as-of.** If either side has 0 completed same-season games
   with kickoff strictly before the candidate (`cf514078`), mark
   ineligible/MISSING and **retain**. Expected **0** in W7–W17. Count source
   is **unresolved** at this seal (not `1ee90fac`). `50bda875` may supply
   counts only after independent parity to sealed input matrices.
2. **T2 exact week.** `lookup_t2(rating_week=week-1)` only. Bye-return sides
   keep `MISSING_RECORD` on T2 cells (5 side fields + 6 matchup diffs).
   **No last-played-week fill.** The 24 listed risks are sealed in
   `T2_BYE_RETURN_RISKS.json`. They stay in the 165.
3. **Complete for later IF (phase 4, not this run).** 27/27
   `DERIVED_PREGAME` under contract **b41f4b43** (20 efficiency + 7 context).
   Partial games remain visible.
4. **No new index formula.** T5 / offense-defense index reused from Stage B
   method **7e77c57f** only.
5. **Do not add** W1, the examined 70 (W2–W6 / `2b9f302e`), Irma/W6-bye
   excluded ids, postseason, EVAL 2018–22, 2023 reserve, or 2024–25.

## 27 fields

Context: `game_id, home_team, away_team, matchup_season, matchup_week,
rest_days_home, rest_days_away`.

Efficiency: `offense_index_*`, `defense_index_*`, 5g EPA/success/pass_rate
home/away, six `matchup_diff_*`.
