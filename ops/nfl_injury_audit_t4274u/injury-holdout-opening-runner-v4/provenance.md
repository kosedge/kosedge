# Provenance — holdout opening runner v4 (not opened)

No secrets. Paths are package-relative unless noted.
- IMV RETURN `4fd6cfbe0adeaa7ff0152d8833e15d6b4e49a64cf47350fe595f3d35acef2867`
- Erratum `b746e5eba9c781f5f0586161b42d942a546b94224c24be8253f9cdd6a6d9ccf0`
- Prior RETURN `77d9c00a` / `a8958e85`
- Ryan CLEAR `t4335s14919` / `fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0`
- Request v3.1 `35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b`
- Active scorer `ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6`
- Scorer v6.2 DRAFT `1129354a06c7c747d7021e1448ff028163314c81c3eee35cc0fb6345deddb9be` **PENDING_RYAN**
- Writer `9947b880bc789192a26b850ee53dc89d4c43a4c107bdf3fc549c65730739d58f`
- Fit `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657`
- Frozen export `d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8`
- Frozen script `8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c`
- Null contract `ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2`
- Record baseline CSV `502110cfc9293d96fd5635fbfdd3fad2c19367fa043ce3770cfbae05f2cdbe12`
- nflverse close le2023 `634d8e730b20c31cafe925ab674a38076d124d619242efdfae140347ff212fc9`
- Baseline method `record_hfa_baseline_method.py` sha `76aac887eddc67f19aaa3236d89fbcd51d2f1675e1416761dd70756df5d1a311`
- Delta producer `holdout_delta_producer.py` sha `43d80936225e97eb201eee814531b65423a69121f7f98b59611abbef4067bbe4`
- Expected answers file `a4f23cbd1efbaf336ecdb5d7b2f7abd469a08d94c2d814053e87e10869d7340c`
- Expected answers commit `74c8028b20ba24d62e995b28a1d51f237ef70ecc` (before runner `57453a0e`)
- Seed 20261023. Sigma 13.5 / 14.0. QB1_INDEX_UNITS 0.12.
- NFL_TOTALS_*: unset. Real lock: not written. Tokens: none.
- 2024/25: not opened. `opening_runner_pass_sha`: null.

Institutional memory: **no prior grades** (`notes/no-prior-grades.md`).

All lines below are `run_injury_holdout_opening.py` unless noted.

---

## Adversarial self-review (required before deposit)

### Production `main()` — ALL pins and B-13 inputs before lock write (B-1 / B-13)

```
1260 def main
1266 assert_env_clean()
1267 if args.refit: die  # no lock
1269 if args.mode == "holdout":
1270     if not args.workspace: die "O-1 opening blocked"  # no lock
1274     run_holdout_workspace(workspace)   # ONLY production/fixture holdout path
```

There is no `write_lock` in `main`.

```
1223 def run_holdout_workspace
1226 assert_pins_before_lock()                 # FIRST
1227 if lock exists: die                       # before inputs / write
1229 assert_workspace_inputs_pre_lock()        # B-13: existence, headers, no-open size
1231 try:
1232     write_lock(workspace, state)          # AFTER pins and inputs
1233–1252 export → .v2 → TZ → incomplete → join → score → week1 → consumed → receipt
1255 except BaseException:
1256     _cleanup_after_lock(...)              # consume + receipt if not already 0444
1257     raise
```

`assert_pins_before_lock` (412–474) hashes every pin (fit, writer, script, contract, **ca98ae0e**, **v6.2 draft**, D-2, v1/v2/v3 RETURNS + v3 erratum, decision, readiness, erratum, spec, acceptance, request, expected, baseline CSV, nflverse close), the expected-answers commit `74c8028b`, method/producer sha vs expected **before import**, B-9 method-vs-CSV, week-1 identity, request fold parse, and `PENDING_RYAN` / active pin `ca98ae0e`. Only then does it log `pins ok before lock`.

`assert_workspace_inputs_pre_lock` (494–545): production workspace uses exact audit-dir paths (`games.json`, `close.csv`, `schedule.csv`, `listings/`). Missing file → `B-13 production input: missing` **before** `write_lock`. CSV header-only; JSON first-4096-byte probe (no data rows); size via `stat`. Holdout-named listings are stat-only and not opened.

F-PRODUCTION-INPUTS-MISSING (`1301`): `main(['--mode','holdout','--workspace', REAL_LOCK.parent])`. Log contains `pins ok before lock` then `STOP: B-13 production input: missing`. Real lock was not written. No receipt in the audit dir.

F-PRODUCTION-LOCK-BLOCKED (`1316`): `write_lock(REAL_LOCK.parent)` after pins. `STOP: O-3 lock: production lock requires verified IMV opening-runner PASS sha`. Real lock not written.

### Every exception path after the lock is written (B-1)

`write_lock` is inside the `try` (1232). Anything after that file exists is a post-lock path.

| After lock, who raises | Type | Handler |
|---|---|---|
| `write_holdout_export_path1` / producer `AssertionError` (raw deltas, extra keys, as_of>kickoff, pin drift) | AssertionError ⊂ BaseException | `_cleanup_after_lock` 1187–1209 |
| `pin_export_v2` / TZ / incomplete / join `die` | SystemExit ⊂ BaseException | same |
| `score_folds` / scorer `die` (incl. ca98ae0e FORBIDDEN on 2024/25) | SystemExit | same |
| `score_folds` KeyError / ValueError / PermissionError | BaseException | same |
| `assert_week1_identity` `die` (1248, **before** receipt) | SystemExit | same; receipt not yet 0444 |
| `mark_lock_consumed` / log write / `write_receipt` | BaseException | cleanup: consume skip if 0444; receipt skip if 0444 |
| KeyboardInterrupt / other BaseException | BaseException | same, then re-raise |

`_cleanup_after_lock` (1187):
- if lock missing: return
- `mark_lock_consumed` — if sidecar already 0444, log and return (644–646); lock file stays 0444 (never rewritten)
- `write_receipt` only if receipt is **not** already 0444 (1196, 1091–1093)
- inner exceptions are logged, not swallowed as success; original exception is re-raised (1257)

F-POST-LOCK-BASEEXCEPTION (`1486`): monkeypatches `score_folds` to raise `ValueError` after lock. Consumed 0444, receipt 0444, lock left 0444. Second `_cleanup_after_lock` does not rewrite the 0444 receipt.

Week-1 identity (`1212`, called `1248`) runs **before** `write_receipt` (`1252`). Success path logs `week1 identity ok before receipt`. A STOP there cannot rewrite a 0444 receipt because the receipt does not exist yet.

### No fixture marker can reach a 2024/25 path (B-2, accepted)

```
289 holdout_season_allowed
293 if year in request_holdout_years():   # parsed 2024/2025
294     return lock_is_production AND verified_opening_pass_sha()
296 if year in synthetic_holdout_years(): # 2098/2099
297     return lock_written
303 may_open_holdout_listings
305     return lock_written AND lock_is_production AND verified_opening_pass_sha()
```

`FIXTURE_MARKER` (353–356) only authorizes a **fixture** lock. F-MARKER-NO-2024 (`1407`): `lock_written=True`, `lock_is_production=False` → 2024/2025 False; 2098/2099 True.

### Every scorer guard against 2024/2025 inputs (B-12 / PENDING_RYAN)

Active pin remains `ca98ae0e` (`62`, `279–282`, `964`). Switch only if `DECISION_RYAN_SCORER_V6_2.txt` is 0444 + `.abs.sha256` + line `AUTHORIZE: scorer v6.2` + sha `1129354a` (`268–276`). File is absent → `F-SCORER-STILL-CA98AE0E` (`1417`).

**ca98ae0e** (no allowance; production would lock then die at score):

| Site | File | What dies |
|---|---|---|
| L86 | `seeded/ca98ae0e/run_injury_residual_evaluator.py` | `FORBIDDEN = {2024, 2025, 2026}` |
| L507 | `score_universe` | `if season in FORBIDDEN: die` |
| L1390 | `load_nflverse_close` | same |
| L1466 | `load_export_games` | same |
| L1553 | `attach_record_baseline` | same |

**v6.2 draft `1129354a`** (IMV diff only; default closed = ca98ae0e):

| Site | File | What dies |
|---|---|---|
| L89 | `seeded/v6.2-draft/run_injury_residual_evaluator.py` | `FORBIDDEN` kept as documentation |
| L94 | `permit_holdout_scoring` | both flags required |
| L100 | `_season_blocked` | 2026 always; 2024/2025 blocked unless lock+PASS |
| L529 | `score_universe` | `if _season_blocked(season)` |
| L1412 | `load_nflverse_close` | same |
| L1488 | `load_export_games` | same |
| L1575 | `attach_record_baseline` | same |

F-SCORER-GUARDS-CLOSED (`1435–1448`) uses **in-memory season integers only**. No 2024/25 byte is read. Default: 2024/2025/2026 blocked; 2023/2098 open. After `permit_holdout_scoring(True, True)`: 2024/2025 admitted, **2026 never**.

`score_folds` (`1033–1036`) calls `permit_holdout_scoring` only if the imported scorer has it. On the active `ca98ae0e` pin that attribute is absent, so the four FORBIDDEN sites still die.

### B-8a anchored PASS (not a substring)

```
78  VERDICT_ANCHORED = ^VERDICT: (PASS|RETURN|PASS WITH CONDITIONS|FAIL)$
79  RUNNER_SHA_ANCHORED = ^RUNNER_SHA: ([0-9a-f]{64})$
215 opening_pass_text_ok — exactly one VERDICT line equal to "VERDICT: PASS"
                     plus exactly one RUNNER_SHA line equal to runner_sha()
228 verified_opening_pass_sha — IMV dir only; sidecar + 0444; then opening_pass_text_ok
```

No `REQUIRED_OPENING_PASS`. Does not read `seeded/` for PASS. F-B8A-SUBSTRING-REJECT (`1421`): RETURN v2 text (quotes `VERDICT: PASS`) rejected; two VERDICT lines rejected; mismatched sha rejected; well-formed pair accepted.

### B-4 producer (filed with expected answers)

`holdout_delta_producer.py` `43d80936`:
- `PINNED_QB1_INDEX_UNITS = 0.12` from fit floor 1.5 / ppu 12.5 (`37`, `75–83`)
- extra player keys refused (`162–171`)
- `as_of <= kickoff` on ok rows (`143–159`)
- raw `games.json` deltas forbidden (`112`)
- invoked `733` after sha vs expected (`397–407`)

### B-6 receipt

- `fold_slim` `985`: scorer holm list only; `i3_holm_source = "scorer holm list only"`; no `p*(9-rank+1)` / no `p_holm_adj`
- `write_receipt` `1087`: write receipt, chmod 0444, **then** `write_receipt_manifest` `1052`
- MANIFEST hashes the 0444 receipt; receipt is **not** rewritten (`1145` after chmod)
- SUMS = MANIFEST lines + `MANIFEST` file hash (`1078`); files must differ (`1082`)
- both 0444 (`1080`)

### B-7 E2E 2098/2099

F-E2E (`1327`): pins → B-13 inputs → lock → producer → writer → guards → join → score → week-1 → consumed → receipt. Folds 2098/2099. Scorer sha `ca98ae0e`. MANIFEST ≠ SUMS, both 0444.

---

## B-item file:line (remaining + accepted)

### B-1

- `1260` `main` → `1274` `run_holdout_workspace` only
- `1226` pins, `1229` B-13 inputs, `1232` lock
- `1255` `except BaseException`
- `1248` week-1 before `1252` receipt
- `1091` / `644` do not rewrite 0444

### B-4

- producer `43d80936` (`397`, `733`)
- QB1 0.12 (`holdout_delta_producer.py:37`, runner `739`)
- extra keys / as_of (`162`, `143`)

### B-6

- `985` scorer holm only
- `1143` receipt 0444 first; `1145` MANIFEST after; not rewritten
- `1078` SUMS extra line; `1082` not identical

### B-8a

- `215` / `228` anchored VERDICT + RUNNER_SHA
- `1421` substring reject

### B-13

- `40–44` exact production paths
- `494` pre-lock existence / headers / no-open size
- `1301` missing production inputs STOP before lock

### Accepted (unchanged contract)

- B-2 `289` / `303` / `1407`
- B-3 `193` / `977`
- B-5 `382` / `445`
- B-7 `1327`
- B-9 pins `459–467`
- B-10 `712` + writer `705` not invoked

---

## Run evidence (this package)

- `--mode fixtures` exit 0. `--mode le2023` exit 0. `--mode holdout` STOP `O-1 opening blocked`.
- Real lock absent.
- F-DEFAULT / F-PRODUCTION-INPUTS-MISSING / F-PRODUCTION-LOCK-BLOCKED / F-LOCK-PRESENT / F-DOUBLE-OPEN / F-REFIT / F-PER-SIDE / F-POST-LOCK-BASEEXCEPTION STOP.
- F-E2E + F-MARKER-NO-2024 + F-SCORER-STILL-CA98AE0E + F-B8A-SUBSTRING-REJECT + F-SCORER-GUARDS-CLOSED recorded.
- le2023: 58653 Z, n_incomplete=11, pinned IDs.
- No 2024/25 path. No merge.
