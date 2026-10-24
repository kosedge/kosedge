# B-items contract (`0505e492`) — expected before the runner

Quoted remaining defects from IMV RETURN v4. Accepted items
(B-1, B-2, B-3, B-5, B-6 mechanics, B-7, B-8a, B-9, B-10, B-13)
need no re-review. B-12 is closed by Ryan t4340s14953 / `592e0bb9`
plus the single pinned scorer sha `755d30a8` (IMV re-checks the
S-2-changed diff).

## B-14

Remove the runtime scorer switch. Pin exactly ONE scorer sha in
code. The constant is set only after Ryan's decision file exists at
`/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt`
sha `592e0bb9`. That path and sha are in these expected answers.
Final scorer sha `755d30a8` (v6.2 + S-2). No `ryan_scorer_v62_authorized`.

## B-4b

Pinned frozen row builder `aa9d512b` + raw-input pins. Player value
and x_continuity come from `8d188da2.precompute_games` /
`_structural_index` / `continuity_for_team` under HEAD `8e2a15ac`
`QB1_INDEX_UNITS = 0.12`. `games.json` values forbidden. le2023
rebuilt deltas = `a38a55bb` 0-diff (2863).

## B-4c

A timestamp with no zone STOPs. Producer `_parse_iso_or_stop` and
builder `_refuse_naive_timestamp` do not coerce naive→UTC.

## B-15

S-2 L1663 text in v6.2: "2026 is never scored. 2024/2025 are scored
only after a production lock and a verified opening-runner PASS."
Receipt field renamed `i3_holm_scorer` (holds raw p + thresholds,
not adjusted p).

## QB1 0.12 source

`seeded/injury_paths_8e2a15ac.py` `ebd3dac0` (HEAD `8e2a15ac`):
`QB1_INDEX_UNITS = 0.12`.
