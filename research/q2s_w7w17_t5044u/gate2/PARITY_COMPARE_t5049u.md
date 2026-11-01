# t5049u — W7–W8 compare fix (CERT=0)

Cite **12763c08 · 1114f24e · 7cefecef · 84eacd96**. CoS tip `7cefecef`.

## Before

`compare_w7w8` only failed numeric diffs for `INDEX_FIELDS` (|Δ|≥1e-6),
`EPA_FIELDS` (|Δ|≥1e-9), and `rest_*` (|Δ|≥1e-9). The `else` branch required
`field.startswith("rest_")` before recording a fail. Pass-rate, pressure, RZ,
and `matchup_diff_def_epa_allowed_5g` could differ without failing. A 756-cell
PASS did not prove full-field numeric parity.

## After

All **27** contract fields are asserted. Tolerances are not loosened:

| Family | Fields | Fail if |
|---|---|---|
| text | game_id, home/away_team, matchup_season/week | string ≠ |
| index | offense/defense_index_* | \|Δ\| ≥ **1e-6** |
| EPA/success (sealed 5g list) | 10 fields | \|Δ\| ≥ **1e-9** |
| rest | rest_days_home/away | \|Δ\| ≥ **1e-9** |
| exact numeric (was unasserted) | pass_rate_*, pressure diffs, RZ diff, matchup_diff_def_epa_allowed_5g | **any** Δ ≠ 0 |

Reconstructed values were **not** edited to obtain PASS.

## Real slice

W7–W8 rebuilt vs Stage B `cd9af285` (28 games × 27 = 756 cells):

| Family | n compared | max \|Δ\| |
|---|---|---|
| text | 140 | n/a (exact) |
| index | 112 | 0 |
| EPA/success | 244 | 0 |
| rest | 56 | 0 |
| exact numeric (was unasserted) | 138 | 0 |

T2 `MISSING_RECORD` cells are status-matched, not numeric-compared.
Full-field compare **PASS**. No reconstructed value was edited. No paper-over.
