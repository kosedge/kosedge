# CURSOR ADDENDUM t5155u — R5 Phase 1 (Worker B + A combine)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5155u **659cd7d9** · Cos ORDER **3e14602b**
RETURN-FIX Cos ORDER **b51a9a10** · Alex RETURN **9332de97** ACCEPTED
**c5574733**. HARD END 02:30 EST / 07:30Z.

Closed quality (do not re-review): #700 tip **12ccc482** · Cos ACCEPT
**4b23584a** · Alex **f4147e76**. Preserve RETURN **7057e5a9**.
Reuse: #699 Package A **42ff285c** / stamp **f7ec09ee** · #700 RETURN-FIX
**12ccc482**. Worker A freeze combined here — same draft PR **#701**.
Do not open a third PR. A PR **#702** is the source tip only.

No merge. No prod default. No real EVAL. No GREEN. No self-ACCEPT.
No Cos bind. No live `--score` until Alex re-PREFLIGHT.
CERT=0. STOP for Alex re-PREFLIGHT.

Worker A implementation tip **661df712a804bc1d9662f77008af28f8418cd0a1** ·
stamp **3fbf5999360433ca46cbe77688daedaedd6a9c9b**. Combine implementation
tip **581493080881d6363935f41c70236b5cb070b401**. RETURN-FIX
implementation tip **255adf7802830bc25814a739d62f65f095216203**. Merge conflict: only
`.prettierignore` (kept both hashed-dir ignores). N1 + market∩96 bytes
**072e99e0** unchanged. One-command:
`CHECKS_PASSED_AWAITING_ALEX_PREFLIGHT` · `verified: false` · focused
tests **87 passed**. Worker A forecast freeze **PINNED**. Q2 **HOLD**.
Phase 2 **READINESS_ONLY**.

## Exact offline commands

```
python3 scripts/nfl/freeze_nfl_t5155u_market_arm.py
PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_496_freeze_t5155u.py
PYTHONPATH=services/model-service python scripts/nfl/run_nfl_t5155u_r5_phase2_one_exec.py
python3 scripts/nfl/run_nfl_t5151u_verify_integrate.py
```

A command is read-only pin after tip — do not re-run produce-μ to rewrite
frozen A bytes. Receipt: `data/ops/nfl-t5151u-verify-integrate/RECEIPT.json`
(copy under `data/ops/nfl-t5155u-r5-phase1/RECEIPT.json`).
Freeze: `data/ops/nfl-t5155u-r5-phase1/MARKET_ARM_FREEZE.json`.

## N1 — required successor (not a #700 review loop)

`output_sha256` is the stable semantic receipt digest. Pytest elapsed
strings (`18 passed in 4.86s`) are stripped from `tests.commands[*]`
before the hash. Timing is kept only as non-semantic `runtime.pytest_elapsed`
/ `side_metadata`. Interpreter path and HEAD remain excluded.

Proofs: same digest across two elapsed values; cross-root `hash_file_list`
identity; re-run identity. Focused identity tests live in
`test_nfl_t5155u_n1_output_hash.py`.

## Market arm freeze (metadata-only BEFORE scoring)

B1 universe (immutable):
`data/ops/nfl-t5119u-r2-owned-coverage/t5136u_B1/ADMISSIBLE_QUOTES_B1.jsonl`
sha256 **b4a3a4dbb8c5404d095b8095ec4018b96ceae532a50600d6d7f29f9d8fe950e6**.

Intersection with REG496 (#699 identity **6429f859**):

- KO−60 cutoff; latest observation ≤24h
- deterministic latest-per-(game, book, spread)
- median eligible DK/FD mainline home spread → home margin by negation
- disclose one-book + per-season / missing counts
- no odds pulls, late quotes, or outcome-based selection
- selection-limited DEV (2020–21 REG496 only; no 2022–23)
- R2-C HOLD threshold **0.30** vs declared PBP REG 256/272 — unchanged
- no ML / Brier / log-loss

#699/#700 guards are reused at the real writer / loader / receipt
boundary. Refusal paths read **zero** target scoring labels. A valid
positive `invoke_outcome_after_gates` invokes the loader once (Phase 2
readiness only). Normal command leaves that flag false.

### Intersection result (B1 ∩ REG496)

|                         |                                                                    |
| ----------------------- | ------------------------------------------------------------------ |
| n                       | **96** (41 / 55)                                                   |
| missing vs REG496       | **400** (199 / 201)                                                |
| one-book / two-book     | **5 / 91**                                                         |
| vs B1 DEV437 matched 94 | +2 REG496-only: `2020_05_BUF_TEN`, `2021_15_WAS_PHI`               |
| intersection bytes      | `072e99e0c984fbd5ef87a2b419344c89148952a06b9185f52556147caeae70df` |
| intersection identity   | `558fbfe5de0344925e389650c28b8c0c42546cd98013c0a55968f67de6e7242e` |
| R2-C HOLD 2020          | 215/256 = 83.98% · HOLD · threshold 0.30 unchanged                 |
| R2-C HOLD 2021          | 217/272 = 79.78% · HOLD · threshold 0.30 unchanged                 |

Not a 94 substitution. Not EVAL. Not scoring.

## Worker A forecast freeze (PINNED)

Read-only bind. No produce-μ rewrite. Q2/candidate stay **HOLD**.

| Item                          | Value                                                              |
| ----------------------------- | ------------------------------------------------------------------ |
| A tip                         | `661df712a804bc1d9662f77008af28f8418cd0a1`                         |
| A stamp                       | `3fbf5999360433ca46cbe77688daedaedd6a9c9b`                         |
| FEATURE_RECON_REG496 identity | `6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640` |
| Feature JSON                  | `282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c` |
| Forecasts                     | `96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407` |
| Q2 history freeze (R3)        | `07bbc340223976ff4d832bb02bce9cae40b2febe3b226f619913241300ec6966` |
| Freeze manifest (R3 rewrite)  | `36f051c4f0ecb96abac973f3e43bfc157a1f632e65d5d8b1de7991495eff7f38` |
| IF finite                     | **496**                                                            |
| Q2 HOLD                       | **496** · 2013–19 REG unproven · do not invent Q2                  |
| Candidate finite              | **0** (HOLD)                                                       |
| common437 IF replay           | **437 / 437** · **0 BLOCKER**                                      |

Phase 2 one-exec runner is implemented and tested. Default command
refuses labels (`outcome_loader_reads=0`). Tests may invoke the loader
once after gates. Live `--score` refused until Cos bind. STOP for Alex
re-PREFLIGHT.

R3 env-hash: `Q2_HISTORY_FREEZE` / `FREEZE_MANIFEST` carry sha pins +
repo-relative/role labels only. No `/tmp` paths, no host `present`.
Drifted on-box `0dba03ee` / `1f4f0537` replaced by env-stable
`07bbc340` / `36f051c4`. Forecasts `96d3aa6f` unchanged.

## Forbidden (honored)

Paid pulls · 2024–26 · 2022–23 scoring · merge/deploy · secrets ·
invented history · Stage C / R2-C / R3 changes · Cos bind · `--score` ·
target scoring loader · ONE DEV diagnostic.

## Pins

| Item                   | Value                                                                     |
| ---------------------- | ------------------------------------------------------------------------- |
| OWNER CLEAR t5155u     | `659cd7d9`                                                                |
| Cos ORDER              | `3e14602b`                                                                |
| #700 tip               | `12ccc482db54dd53bc6d79cea5f4af01c5540950`                                |
| Cos ACCEPT #700        | `4b23584a`                                                                |
| Alex #700              | `f4147e76`                                                                |
| RETURN                 | `7057e5a9`                                                                |
| B1 universe            | `b4a3a4dbb8c5404d095b8095ec4018b96ceae532a50600d6d7f29f9d8fe950e6`        |
| Intersection n / bytes | `96` / `072e99e0c984fbd5ef87a2b419344c89148952a06b9185f52556147caeae70df` |
| Intersection identity  | `558fbfe5de0344925e389650c28b8c0c42546cd98013c0a55968f67de6e7242e`        |
| REG496 identity        | `6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640`        |
| Package A tip          | `42ff285cc1be2459512af4761651ba6dfe17dc75`                                |
| Worker A tip / stamp   | `661df712a` / `3fbf59993`                                                 |
| Combine implementation | `581493080881d6363935f41c70236b5cb070b401`                                |
| RETURN-FIX tip         | `255adf7802830bc25814a739d62f65f095216203`                                |
| RETURN-FIX Cos / Alex  | `b51a9a10` / `9332de97` ACCEPTED `c5574733`                               |
| R2-C HOLD threshold    | `0.30` unchanged                                                          |
