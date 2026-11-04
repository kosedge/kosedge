# t5344u R7_RECORD_DATE_RETRO_C1 RECEIPT (CERT=0)

Worker A · DESIGN 25194 / HISTORY 47316 · Cos ACCEPT `c14c3bd6`
Isolated RECORDED_DATE_RETRO profile + guarded synthetic executor.
IMPLEMENTED ≠ VERIFIED ≠ ACCEPTED. DRAFT ≠ merge. Real EXEC HOLD.

- GATE0: PASS · `START_PREFLIGHT_RETRO_C1_A.md` · 2026-11-04T00:12:19Z · HEAD `e290ff3b`
- spec `@7cb4fcef` SHA256 `3394663e41183de255e641ffbfc2e321bb7266fd3e27d984f7f350db6f5e3110` MATCH
- clarifications `@cc5ce256` SHA256 `dd2fa8d041b652324c07b77aea2f2b589146213342a414b98e8bcc629d5bc3e8` MATCH
- nominal 528 `@7a668db` SHA256 `0d072469faa78898419e4cf8a3042ca5bdf2e673636c84aa581d9db4d1392306` MATCH
- rest meta `@c1f2dca` SHA256 `96f3ffb3408120c6e7bf2bddef6eac8f5b97a012ce63f2cf3b163af9773f5466` MATCH
- identity 2320 `@eaf22ee3` SHA256 `ca6d2c84a879062080d38940d5a70360c6fb4a825df9d0d26bf393652e036c26` MATCH
- rest recomputed from nominal 528 dates: **496/496**
- identity columns only · scores unopened · 1792 REG 2013–19 + 528 REG 2020/21
- synthetic executor: authority ISSUED→readers→IF/Q2/C→score y=3.0→SPENT
- synthetic C `1.6645744773174405` (cal=False) · IF/Q2 pair preserved
- invalid/absent/REAL/R5/spent: **zero** model/outcome reads
- strict live-causal `REST_ACTUAL_ET_CALENDAR_V1`: still DATA_HOLD
- NTBB-K: RETURN 58427 · `a807af22` held **not final** · `d0bb6bef` refused · wait B log-PMF/tail delta · **not** an R7 model arm
- package **not accepted** while direct paths open · producer→capability/gate = A
- ready_for_real_exec: **false**
- N1–N3: NON-BLOCKING → Codex

## Executable command (synthetic / current machine)

```
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_r7_record_date_retro_c1.py
```

Current machine: **NOT_EXECUTABLE** for real data.

## Future real command (not a grant)

```
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_r7_record_date_retro_c1.py --claim <ROOT_CLAIM> --context <ROOT_CONTEXT_HASH>
```

Requires a distinct matching Root GO after final pins + independent preflight. No ENV / REAL / ENABLE shortcut.

## Raw-source pins (unopened except bound metadata)

| pin | sha256 | status |
|---|---|---|
| games | `4fe1cdd7…1abef8` | UNOPENED |
| outcomes | `50bda875…7dc081` | UNOPENED (no scores) |
| identity 2320 | `ca6d2c84…036c26` | BOUND |
| nominal 528 | `0d072469…392306` | BOUND |
| rest meta 496 | `96f3ffb3…3f5466` | BOUND |
| market-point digest | `072e99e0…ae70df` | SPEC_NAMED · ABSENT working-tree |
| archived R5 | `df24500e…77a5a0` | REFERENCE_ONLY · never regenerate |

## Residuals

- actual clocks UNKNOWN · strict REST blocked
- SciPy ABSENT · no install · science EXEC HOLD
- CERT=0 · Cos-host unused
