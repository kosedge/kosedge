# B-items contract (`2c71e4d0`) — expected before the runner

Quoted remaining defects from IMV RETURN v5. Accepted items
(B-1, B-2, B-3, B-5, B-6, B-7, B-8a, B-9, B-10, B-12 logic, B-13,
B-14, B-4c, B-15) need no re-review. The v6.2 **content** PASS
(`V62_DIFF_VERDICT` on `755d30a8`) carries over after IMV confirms
the L-1 change is docstring-only.

## L-1

Relabel only. Active scorer is `8b482cb9` at
`seeded/v6.2/run_injury_residual_evaluator.py`. Baseline
`755d30a8` kept at `seeded/v6.2-755d30a8/`. Deposited
`seeded/v6.2/DIFF_vs_755d30a8.txt` sha `280d9785` is the three
docstring header lines. No `DRAFT` / `PENDING_RYAN`. Draft dir
removed.

## B-4b(R)

`reproduce_le2023_a38a55bb()` was run. Deposited outputs (IMV
reads these; do not take 0-diff from notes):

- `out/le2023/rebuilt_le2023_deltas.json` sha `8af44a7e` — 2863
  rows, fields `game_id, season, week, home, away, delta_margin,
  delta_total`
- `out/le2023/rebuilt_le2023_compare.json` sha `bc89721f` —
  `verdict=0_DIFF`, `n_delta_margin_diff=0`, `n_delta_total_diff=0`,
  `n_missing=0`, export `a38a55bb`

## B-4b(P)

The lock records `raw_input_shas`: sha256 of every
`listings_*.csv`, `schedule.csv`, `roster_*.csv`, `close.csv`,
`games.json`, computed before any data row is parsed. The receipt
repeats them. Whole-file sha256 is not a row parse.

## B-4b(n)

Allowed roster years, declared in expected answers:

- le2023: 2012–2023
- production: 2023, 2024, 2025
- synthetic: 2098, 2099
- 2026: never

`load_rosters_dir` STOPs on a year outside the declared set.

## B-14 (already accepted)

Exactly one scorer sha in code. Decision
`/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt`
sha `592e0bb9`. No `ryan_scorer_v62_authorized`.
