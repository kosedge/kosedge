# CURSOR ADDENDUM t5155u — R5 Phase 1 (Worker B)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5155u **659cd7d9** · Cos ORDER **3e14602b**
HARD END 02:30 EST / 07:30Z.

Closed quality (do not re-review): #700 tip **12ccc482** · Cos ACCEPT
**4b23584a** · Alex **f4147e76**. Preserve RETURN **7057e5a9**.
Reuse: #699 Package A **42ff285c** / stamp **f7ec09ee** · #700 RETURN-FIX
**12ccc482**. Worker A owns forecast/identity freeze — not raced here.

No merge. No prod default. No real EVAL. No GREEN. No self-ACCEPT.
No target scoring loader / ONE DEV diagnostic. CERT=0.

## Exact offline commands

```
python3 scripts/nfl/freeze_nfl_t5155u_market_arm.py
python3 scripts/nfl/run_nfl_t5151u_verify_integrate.py
```

Receipt: `data/ops/nfl-t5151u-verify-integrate/RECEIPT.json` (copy under
`data/ops/nfl-t5155u-r5-phase1/RECEIPT.json`).
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

Worker A forecast freeze slot: **PENDING** — combine after A tips.

### Intersection result (B1 ∩ REG496)

| | |
|---|---|
| n | **96** (41 / 55) |
| missing vs REG496 | **400** (199 / 201) |
| one-book / two-book | **5 / 91** |
| vs B1 DEV437 matched 94 | +2 REG496-only: `2020_05_BUF_TEN`, `2021_15_WAS_PHI` |
| intersection bytes | `072e99e0c984fbd5ef87a2b419344c89148952a06b9185f52556147caeae70df` |
| intersection identity | `558fbfe5de0344925e389650c28b8c0c42546cd98013c0a55968f67de6e7242e` |
| R2-C HOLD 2020 | 215/256 = 83.98% · HOLD · threshold 0.30 unchanged |
| R2-C HOLD 2021 | 217/272 = 79.78% · HOLD · threshold 0.30 unchanged |

Not a 94 substitution. Not EVAL. Not scoring.

## Forbidden (honored)

Paid pulls · 2024–26 · 2022–23 scoring · merge/deploy · secrets ·
invented history · Stage C / R2-C / R3 changes.

## Pins

| Item                    | Value                                                              |
| ----------------------- | ------------------------------------------------------------------ |
| OWNER CLEAR t5155u      | `659cd7d9`                                                         |
| Cos ORDER               | `3e14602b`                                                         |
| #700 tip                | `12ccc482db54dd53bc6d79cea5f4af01c5540950`                         |
| Cos ACCEPT #700         | `4b23584a`                                                         |
| Alex #700               | `f4147e76`                                                         |
| RETURN                  | `7057e5a9`                                                         |
| B1 universe             | `b4a3a4dbb8c5404d095b8095ec4018b96ceae532a50600d6d7f29f9d8fe950e6` |
| Intersection n / bytes  | `96` / `072e99e0c984fbd5ef87a2b419344c89148952a06b9185f52556147caeae70df` |
| Intersection identity   | `558fbfe5de0344925e389650c28b8c0c42546cd98013c0a55968f67de6e7242e` |
| REG496 identity         | `6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640` |
| Package A tip           | `42ff285cc1be2459512af4761651ba6dfe17dc75`                         |
| R2-C HOLD threshold     | `0.30` unchanged                                                   |
