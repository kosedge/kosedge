# Verified vs claimed — Phase 0

## Verified (file opened or command output)

- Ryan decision bytes hash sha256
  `47afd7f631bb1685c2768f95720656d4d9442835274f90c7731afd3028605098`
  (sha8 `47afd7f6`). File:
  `evidence/DECISION_RYAN_t4344u_OPTION_B_WEEK_AWARE_ROSTERS_v1_a03c.txt`.
- Frozen script on v6 branch hashes `8d188da2…`. `def load_rosters`
  (L289–314) does not contain the substring `week`. Collapse key is
  `(year, team, pid)`. Starter rule is `slot in STARTER_SLOTS`.
- Builder `load_rosters_dir` L267–302 is the same collapse. Week is
  read for schedule and listings, not for rosters.
- Writer L338–345 calls `fit.load_rosters()` then `precompute_games`.
- `resolve_fit_player_identity` (`ff8e6527` L658–688) uses the team
  book and season book it is given; it has no week key.
- Producer `_assert_as_of_before_kickoff` checks `listing_as_of` only.
- `roster_YYYY.csv` header includes `week`, `game_type`, `status`,
  `depth_chart_position`. Sample 2023 row: PHI / week 11 / REG / CUT.
- 2013–2023 files: one row per `(team, gsis_id)` every year. Totals in
  `evidence/empirical-lookahead-le2023.json`. Source shas match v6
  `REQUIRED_ROSTERS` / MANIFEST for 2013–2021; 2022=`86471959`,
  2023=`f98283e6` from the files themselves.
- 2023 PIT QBs are week 19 WC. 2019 PIT QBs are week 17 REG with Ben
  `RES` and Hodges `ACT`. 2022 PIT QBs are week 18 REG.
- `holdout-once.lock` is absent. 2024 / 2025 / 2026 roster files were
  not read.
- Production `injury_paths.py` has no `load_rosters` / `STARTER_SLOTS` /
  `_structural_index`.
- Current branch is off `deploy-vercel` `20d51f22`. Residual-fit
  scripts are not on this HEAD; line numbers are from the pinned v6
  copies.

## Claimed (inference, labeled)

- IMV ruling text `0feec57e` was not in this checkout. The defect id
  B-4b(n)-PIT and the season-level / week-ignored description are
  taken from Ryan's decision file (opened) and from the code (opened).
  This package does not quote a ruling file it did not hash.
- "le2023 fit evidence invalidated" is a consequence claim: the
  selected Spec C, `6a5490db`, and `a38a55bb` were produced by
  `load_rosters` → `precompute_games` → `apply_params`. The bytes of
  those artifacts were not re-read in this pass; the pins are from
  the already-filed v6 package.
- Listing as-of / `n_lag_out` remain "judged safe by IMV" per Ryan's
  decision text, not re-audited here.
- `materialize_depth_chart_weekly` using season-level `nfl_dp_rosters`
  is adjacent, not a residual-fit feeder.

## Not done (on purpose)

- No week-aware rebuild
- No refit
- No holdout open
- No lock
- No merge / deploy / publish
