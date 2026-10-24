# Provenance — holdout opening runner v3 (not opened)

No secrets. Paths are package-relative unless noted.
- IMV RETURN `77d9c00a306d1399aeeab6558a522182aa52d63c42c0b1f8cc4d350c1b0c3d0d`
- Prior RETURN `a8958e850cd75cce5a24feda95a865e86ca39a2afaff5144748f70cfe4dcbeaa`
- Ryan CLEAR `t4335s14919` / `fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0`
- IMV D-2 ruling `b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8`
- Request v3.1 `35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b`
- Scorer `ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6`
- Writer `9947b880bc789192a26b850ee53dc89d4c43a4c107bdf3fc549c65730739d58f`
- Fit `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657`
- Frozen export `d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8`
- Frozen script `8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c`
- Null contract `ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2`
- Record baseline CSV `502110cfc9293d96fd5635fbfdd3fad2c19367fa043ce3770cfbae05f2cdbe12`
- nflverse close le2023 `634d8e730b20c31cafe925ab674a38076d124d619242efdfae140347ff212fc9`
- Baseline method `record_hfa_baseline_method.py` sha `76aac887eddc67f19aaa3236d89fbcd51d2f1675e1416761dd70756df5d1a311`
- Delta producer `holdout_delta_producer.py` sha `57df9a50a64493c2f89b37480164852653318abadff5cec1871b7c360a9daed0`
- Expected answers file `1cffb97927095930f675963a9656524435f36bd1d79077ab3245d403f6cd2fcd`
- Expected answers commit `fd2ed658166c068c088bb8d971e899da87017ab9` (before runner `7a4171e9`, file sha `e6e103de`)
- Seed 20261023. Sigma 13.5 / 14.0.
- NFL_TOTALS_*: unset. Real lock: not written. Tokens: none.
- 2024/25: not opened. `opening_runner_pass_sha`: null.

Institutional memory: **no prior grades** (`notes/no-prior-grades.md`).

All lines below are `run_injury_holdout_opening.py` unless noted.

---

## Adversarial self-review (required before deposit)

### Production `main()` line by line — ALL pins before lock write (B-1)

```
1030 def main
1037 assert_env_clean()
1038 if args.refit: die  # no lock
1040 if args.mode == "holdout":
1041     if not args.workspace: die "O-1 opening blocked"  # no lock
1044     workspace = resolve
1045     run_holdout_workspace(workspace)   # ONLY production/fixture holdout path
```

There is no `write_lock` in `main`. The v2 defect (`write_lock(REAL_LOCK.parent)` before pins) is gone.

```
987 def run_holdout_workspace
989 state = {lock_written: False, lock_is_production: False}
990 assert_pins_before_lock()          # FIRST
991 if lock exists: die
993 write_lock(workspace, state)       # AFTER pins
995–1014 export → .v2 → TZ → incomplete → join → score → consumed → receipt
```

`assert_pins_before_lock` (338–388) hashes every pin (fit, writer, script, contract, scorer, D-2, v1/v2 RETURNS, decision, readiness, erratum, spec, acceptance, request, expected, baseline CSV, nflverse close), the expected-answers commit, **method sha vs expected before import** (368–374), **producer sha vs expected before import** (371–375), B-9 method-vs-CSV, week-1 identity, and request fold parse. Only then does it log `pins ok before lock`.

F-PRODUCTION (`1072`) calls `main(['--mode','holdout','--workspace', REAL_LOCK.parent])`. Log contains `pins ok before lock` then `STOP: O-3 lock: production lock requires verified IMV opening-runner PASS sha`. Real lock was not written. No receipt was written into the audit dir (`1082–1083`).

### No fixture marker can reach a 2024/25 path (B-2)

```
219 holdout_season_allowed
223 if year in request_holdout_years():   # parsed 2024/2025
225     return lock_is_production AND verified_opening_pass_sha()
227 if year in synthetic_holdout_years(): # 2098/2099 from expected
229     return lock_written
233 may_open_holdout_listings
235     return lock_written AND lock_is_production AND verified_opening_pass_sha()
```

`workspace_is_review_fixture` / `FIXTURE_MARKER` (38, 283–286) only authorizes writing a **fixture** lock. They are not consulted by `holdout_season_allowed` or `may_open_holdout_listings`. F-MARKER-NO-2024 (`1144–1149`): `lock_written=True`, `lock_is_production=False` → 2024/2025 False; 2098/2099 True; listings_2024/2025 False.

No `listings_2024.csv` / `listings_2025.csv` exists in this package.

### Every value comes from a pinned, sha-verified source (B-4/B-5/B-10)

- Deltas: `holdout_delta_producer.produce_deltas` (`563`) after sha `57df9a50` (`323–335`). That calls `apply_params` from frozen script `8d188da2` with `selected_params` from fit `6a5490db` under contract `ff8e6527`. `games.json` raw `delta_margin`/`delta_total` are refused (`holdout_delta_producer.py` `_refuse_raw_deltas`).
- Baseline: method `76aac887` asserted vs expected **before import** (`308–320`, `368–374`). Built from prior-week W-L; no `-3.0`/`45.0`.
- Timestamps / `.v2`: writer `9947b880` `timestamps_for_game` + `write_sidecar_chain` (`527–537`, `575`, `596`). `writer.main()` is logged as present and not invoked (`534–535`).
- Folds: request parse `season ∈ {2024, 2025}` (`167–176`, `385–387`); fixture years from expected `synthetic_holdout_years` (`802–807`). E2E used F1=2098 / F2=2099.
- Scorer: sha `ca98ae0e` before exec (`790–798`).

### Nothing in the receipt is hardcoded (B-6)

```
907 opening_permitted = opening_permitted_computed(state)          # 238
908 holdout_years_opened = holdout_years_opened_computed(state, tz) # 242
909 runner_sha = runner_sha()
910 scorer_sha = REQUIRED_SCORER
936 folds = fold_slim(scorer result)  # I-1, 9 Holm p, K-2
940 RECEIPT_MANIFEST / RECEIPT_SHA256SUMS
946 chmod 0444
```

E2E receipt: `opening_permitted=false` (computed: not production+PASS), `holdout_years_opened=false` (computed: years opened were 2098/2099, not request years), I-1/Holm/K-2 present, mode 0444.

### PASS check reads the exact IMV path in B-8

```
39  IMV_RULING_DIR = Path("/workspace/fg-repair/imv-gate1-review-2026-10-02")
40  IMV_OPENING_RULING_GLOB = "IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v*.txt"
189 verified_opening_pass_sha
194 if not IMV_RULING_DIR.is_dir(): return None
197 for path in IMV_RULING_DIR.glob(...)
    sidecar .abs.sha256; mode 0444; listed sha == file sha
    text contains "VERDICT: PASS" and this runner_sha()
```

No `REQUIRED_OPENING_PASS` constant. Does not read `seeded/`. This checkout has no `fg-repair` dir → returns `None` → production lock STOP.

---

## B-item file:line

### B-1 production sequence

- `1030` `def main` — holdout mode only calls `run_holdout_workspace`
- `1045` `run_holdout_workspace(workspace)`
- `987` `def run_holdout_workspace`
- `990` `assert_pins_before_lock()` before `993` `write_lock`
- `1072` F-PRODUCTION uses `main`, not a bare `write_lock`
- `1076` requires log `pins ok before lock`

### B-2 allowance; marker cannot admit 2024/25

- `219` `holdout_season_allowed` — 2024/25 = production AND PASS
- `233` `may_open_holdout_listings` — same; marker unused
- `248` `assert_path_not_holdout` — path parts `2024`/`2025` gated
- `1144–1149` F-MARKER-NO-2024

### B-3 fold years from request

- `167` `parse_request_fold_years` — `season ∈ {YYYY, YYYY}` on sha-verified request
- `802` `fold_year_map` — production+PASS → request years; else expected 2098/2099
- `850` `score_folds` — no 2022/2023 literals
- E2E recorded `fold_years F1=2098 F2=2099`

### B-4 delta producer

- `holdout_delta_producer.py` sha `57df9a50` (filed with expected answers)
- `323` `import_producer` — sha vs expected before import
- `563` `producer.produce_deltas`
- Producer pins fit `6a5490db`, script `8d188da2`, contract `ff8e6527`
- Raw `games.json` deltas refused

### B-5 method pin before import

- `308` `import_baseline_method` — sha vs expected first
- `368–374` same assert inside `assert_pins_before_lock`
- `record_hfa_baseline_method.py:76aac887`

### B-6 receipt

- `238` / `242` computed flags
- `810` `fold_slim` — I-1, `i3_holm_adjusted_p` (9), K-2 Brier/LL/reliability
- `890` `write_receipt` — top-level runner/scorer sha
- `866` receipt MANIFEST/SUMS
- `946` chmod 0444

### B-7 synthetic holdout-season E2E

- `fixtures/e2e/` seasons 2098/2099, no delta fields
- `1085–1142` F-E2E lock → export → guards → join → score → receipt (receipt copy `1131–1136`)
- Recorded n_incomplete=1, i4=INCONCLUSIVE, producer+writer invoked

### B-8 PASS path

- `39–40` exact dir + glob
- `189–216` sidecar, 0444, `VERDICT: PASS`, `runner_sha()`
- No constant; no `seeded/` PASS read

### B-9 rounding

- `record_hfa_baseline_method.py` `ROUND_HALF_UP` (`round4`)
- `assert_reproduces_le2023_csv` — 2992 rows, 1e-4 tolerance, DAL-CAR 45.3563
- `376–381` invoked inside `assert_pins_before_lock`

### B-10 Path 1 composition

- Expected `path1_export_composition.statement`
- `540` export = `produce_deltas` + `timestamps_for_game` + `write_sidecar_chain`
- `534–535` `writer.main()` not invoked
- Lock and receipt carry the composition statement (`427`, `917`)

---

## Run evidence (this package)

- `--mode all` exit 0. Real lock absent.
- F-DEFAULT / F-PRODUCTION / F-LOCK-PRESENT / F-DOUBLE-OPEN / F-REFIT / F-PER-SIDE STOP.
- F-E2E + F-MARKER-NO-2024 recorded.
- le2023: 58653 Z, n_incomplete=11, pinned IDs.
- No 2024/25 path. No merge.
