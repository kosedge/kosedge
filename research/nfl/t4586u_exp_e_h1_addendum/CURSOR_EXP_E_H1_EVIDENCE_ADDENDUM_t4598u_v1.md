# CURSOR EXP E — H1 EVIDENCE ADDENDUM t4598u v1

**SEALED ADDENDUM · CERT=0 · NFL NO-GO · F2 FROZEN · #648 DRAFT · do not merge**

Does **not** rewrite sealed PASS artifacts:

| sealed | sha8 | sha256 |
|---|---|---|
| `research/nfl/t4586u_exp_e_kickoff_asof/counts.json` | **b0365365** | `b0365365251400715144ff5fdb3ddeae68024a33efccade044249e2e1fceeec2` |
| `research/nfl/t4586u_exp_e_kickoff_asof/REPORT.md` | **1d7f5c78** | `1d7f5c78bd8870790e98de0487e626ba0032230fb19b6ec41bb3af7c158dbc5b` |
| `research/nfl/t4586u_exp_e_kickoff_asof/manifest.json` | **aa9d37e0** | `aa9d37e0dfca5ed472df0e4c17e075531028c33ba2d3b763f19cc77f527276d5` |

Authority: IMV_GRADE t4598u **06bc86e2** (IMV_RETURN) · CoS order **5cce88e4** · CoS ACCEPT **3f21d445** · Ryan CLEAR **5bb608d0** (Exp E ONLY). IMV §G shortest path. No Exp A. No Odds. No merge. No F2. No re-run (input hashes identical).

Parent tip when this addendum was authored: **d7cc7d9513b2**. This commit is a successor on the same DRAFT branch.

---

## 1) SHA256SUMS-listed pins now on the PR tip

Placed under `research/nfl/t4586u_exp_e_inputs/` (downloadable from #648 tip). PBP parquets **not** re-uploaded; attested by both-run logs.

| file | sha256 | sha8 |
|---|---|---|
| `research/nfl/t4586u_exp_e_inputs/games.csv` | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` | **4fe1cdd7** |
| `research/nfl/t4586u_exp_e_inputs/historical_oos_games.csv` | `1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed` | **1ee90fac** |
| `research/nfl/t4586u_exp_e_inputs/rolling_features_weekly_pbp_strict_asof_2013_2023.csv` | `1b07654ea500535ff445e0f3c20acc26a6c3006857951562755e406adff52479` | **1b07654e** |

`historical_oos_games.csv` was already in-tree at `data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv` (same bytes). Copied here so the packet is adjacent.

Audit script already on branch: `research/nfl/t4586u_exp_e_kickoff_asof_audit.py`.

Already on tip from `d7cc7d95` (outputs): inversions, week1_windows, covid_flex_flags, intraweek_conservative, rest_catalog, neutral_catalog, kickoff_unknown, SHA256SUMS, schedule snapshot, weather extract.

---

## 2) BOTH-run hash-before-read logs + timestamps

| run | verbatim log | timestamps |
|---|---|---|
| FAIL | `fail_run/exp-e-audit.log` sha8 **b7ded492** | `hash_before_read_timestamps.md` |
| PASS | `pass_run/exp-e-audit-rerun.log` sha8 **f6b30a18** | same |

Every `[h1] sha256 …` line is emitted **before** the first `[pbp] load` (and before any CSV parse of those inputs). The FAIL log writes `SHA256SUMS n=15 (before any input parse)` then `[pbp] load 2012`. The PASS log does the same after cache-hit re-hash.

FAIL window: games/PBP mtimes **2026-10-28T12:33:56Z–12:33:59Z**; log closed **12:34:01Z**.  
PASS window: same input bytes re-hashed; rolling `git show` mtime **12:35:37Z**; log closed **12:35:40Z**.

---

## 3) First-run FAIL counts + identical input hashes

`fail_run/counts.json` sha256 **55e3430dd317bac35a9a09e5918f8f1b1efa9b6a59ce8280c43c0ddc27e1184e** (sha8 **55e3430d**) — byte-identical to the FAIL-run printed sha8.

| key | FAIL | PASS (sealed) |
|---|---|---|
| verdict | `FAIL` | `PASS` |
| n_kickoff_unknown | **8** | 0 |
| n_kickoff_ok | 5976 | 5984 |
| n_kickoff_fail | 0 | 0 |
| fail_reasons | `["n_kickoff_unknown=8"]` | `[]` |
| games_csv_sha256 | 4fe1cdd7… | 4fe1cdd7… |
| pbp_sha256 2012–2023 | identical map | identical map |
| rolling_csv_sha256 | 1b07654e… | 1b07654e… |
| schedule_2012_sha256 | `69350c2f…` (parse OUTPUT) | `d36bbb12…` (parse OUTPUT) |

FAIL log extract (`fail_run/exp-e-audit.log` tail): `"verdict": "FAIL"`, `"counts.json": "55e3430d"`, input sha8s `4fe1cdd7` / `1ee90fac` / `1b07654e` / PBP 12-season set.

`h1_hash_compare.json` verdict **IDENTICAL_INPUTS**. Derived 2012 schedule snapshot is a **parse output**, not an H1 input. No BLOCKED. No re-run.

Reconstruction note: FAIL `counts.json` was overwritten on disk by the PASS run. The recovered file is `json.dumps(sort_keys=True, indent=2)` of the FAIL-run object (this seat read that file before overwrite). Hash **MATCH 55e3430d**.

---

## 4) Code-only min-ISO fix + the 8 windows

Diff (code only): `min_iso_time_of_day_fix.diff` = `git diff 3abbcb90 c9844c9e -- research/nfl/t4586u_exp_e_kickoff_asof_audit.py`

Nature: first-row `drop_duplicates(game_id)` often hit NaN `time_of_day` and/or `start_time=12/31/69`. Fix takes **min valid ISO `time_of_day` per game**. `12/31/69` sentinels rejected. **No invented noon.** Min/earliest time cannot move a kickoff later → cannot admit a leak.

### 8 unknown windows (FAIL `n_kickoff_unknown=8`)

| panel_game_id | side | franchise | kickoff(G) | unknown contributor (before) | after (min ISO) |
|---|---|---|---|---|---|
| 2013_01_BAL_DEN | home | DEN | 2013-09-06T00:30:00Z | 2012_15_DEN_BAL empty | 2012-12-16T18:03:53Z |
| 2013_01_NYG_DAL | away | NYG | 2013-09-09T00:30:00Z | 2012_16_NYG_BAL empty | 2012-12-23T21:26:50Z |
| 2013_01_TEN_PIT | home | PIT | 2013-09-08T17:00:00Z | 2012_13_PIT_BAL empty | 2012-12-02T21:27:24Z |
| 2013_01_HOU_SD | home | LAC | 2013-09-10T02:15:00Z | 2012_13_CIN_SD empty | 2012-12-02T21:27:51Z |
| 2013_02_DEN_NYG | home | NYG | 2013-09-15T20:25:00Z | 2012_16_NYG_BAL empty | 2012-12-23T21:26:50Z |
| 2013_02_DEN_NYG | away | DEN | 2013-09-15T20:25:00Z | 2012_15_DEN_BAL empty | 2012-12-16T18:03:53Z |
| 2013_03_NYG_CAR | away | NYG | 2013-09-22T17:00:00Z | 2012_16_NYG_BAL empty | 2012-12-23T21:26:50Z |
| 2013_04_NYG_KC | away | NYG | 2013-09-29T17:00:00Z | 2012_16_NYG_BAL empty | 2012-12-23T21:26:50Z |

After fill, each contributor kickoff remains **strictly before** `kickoff(G)` (2013-09+). CSVs: `eight_windows_before_after.csv`, `eight_contributor_kickoffs.csv`.

Ten 2012 games had first-row unknown clocks; six (weeks 4/6/7/12) aged out of the last-5 before any 2013 panel window, so they did not increment `n_kickoff_unknown`.

---

## 5) Script + tip pins

| pin | value |
|---|---|
| FAIL-run script commit | **3abbcb90** (`3abbcb9031146a059ded3cb214be9597b59fb7ac`) |
| FAIL-run script sha256 | **3e71aa00** `3e71aa004f79c16f3db65ed1461148c575984481b2dd0ff62459d55d0f986b60` |
| PASS-run script commit | **c9844c9e** |
| PASS-run / tip script sha256 | **7fb6cf19** `7fb6cf196bf825a3d99370bb2168b88417d8bf7de69173f37eaff2cb99ca0f2d` |
| Sealed-PASS evidence commit (parent) | **d7cc7d9513b2** (`d7cc7d9513b200147561e3ac8b0ae0635e01e7ae`) |

`script_pins.json` carries the same. The addendum commit (this file’s landing commit) is the DRAFT tip successor of `d7cc7d95`.

---

## Explicit non-actions

- Sealed PASS `counts.json` / `REPORT.md` / `manifest.json` **not mutated** (re-verified MATCH after this filing).
- Exp A not run. β not fit. `simulate_nfl_game` not imported.
- Odds off. No merge. F2 frozen. 2024+ untouched. CERT=0.
- No full Exp E re-run (inputs identical → not BLOCKED).

NFL NO-GO · Coming Soon ON · sealed=1 · #648 DRAFT
