# C-4 — commit `852fe21c` preceded the v5 run

IMV `1ef1f0a7` classified the order as secondhand because the v5 run log does
not print the commit id. The git first-parent order and timestamps on this
branch are inspectable.

## First-parent order (`cursor/nfl-injury-evaluator-v5-1a07`)

```
852fe21c638532f45fd57ea55668716b49266e49  2026-10-24 13:23:02 +0000
  File v5 expected answers, W-1/W-4 notes, and a38a55bb export before any scorer run.

c3bc0165e428d60cab09b98cf2b8ceba8df196b6  2026-10-24 13:24:36 +0000
  Add v5 scorer P-1/P-2/P-4 pin, C-5 exclude, and naive-timestamp STOP.

548b2e18fae9216b03f4559b387b07da66f2a4c1  2026-10-24 13:27:06 +0000
  Add v5 F1/F2/pooled outputs, checker green, and package MANIFEST.
```

Author and committer dates are identical (`%ci` = `%ai`).

## Run-log / output timestamps vs the commit

| object | time (UTC) |
|---|---|
| `t_expected/T1_T10_EXPECTED.json` mtime | 2026-10-24 13:22:57 |
| commit `852fe21c` | 2026-10-24 13:23:02 |
| commit `c3bc0165` (scorer exists) | 2026-10-24 13:24:36 |
| `out/evaluator_results.json` mtime | 2026-10-24 13:25:04 |
| `out-rerun/evaluator.log` mtime | 2026-10-24 13:25:36 |
| commit `548b2e18` (outputs) | 2026-10-24 13:27:06 |

`inputs/expected_answers_commit.txt` contains `852fe21c638532f45fd57ea55668716b49266e49`.
v5 `provenance.md` and `out/evaluator_results.json` field `expected_answers_commit`
cite that same hash. The evaluator log body does **not** print `852fe21c`
(IMV’s log-channel finding stands). The commit timestamp is earlier than the
run-log file.

## Label

- **Inspectable on this branch:** `852fe21c` before `c3bc0165` before the run
  outputs.
- **Log channel:** still secondhand (the log text does not embed the commit).
- Holdout request records both.
