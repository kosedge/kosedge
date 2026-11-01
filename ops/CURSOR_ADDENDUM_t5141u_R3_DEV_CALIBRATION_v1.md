# CURSOR ADDENDUM t5141u — R3-DEV-CALIBRATION (pre-fit freeze + STOP) · tip `acffed20`

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5141u **714ced10** · Cos ORDER **1155f43f** · PREFLIGHT **a23e01dd**
Parent #693 HEAD **316345fa**. Isolated new directory. No EVAL EXEC. No claim.
**STOP — awaiting Alex pre-computation GO.** Diagnostic not executed.

## What this is

Bounded exploratory DEV calibration experiment on the existing 437 REG DEV
rows. Implementation + meaningful tests + frozen pre-fit artifacts.
**Not EVAL. Not clean confirmation. Not a winner. Not a gate waiver.**

DEV outcomes on these rows are **ALREADY CONSUMED**. RETRO_FIT /
forecast-vintage limitations remain. Calibration cannot repair them.

## Preserve (byte-immutable — unchanged)

| Artifact | sha256 (unchanged) |
| -------- | ------------------ |
| DEV437 `DEV_RESEARCH_t5125u_R2B2_437.json` | file `66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50` · record `0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637` |
| First-case DEV_RESEARCH (CIN_CLE) | file `8cb9a2a1…` · record `621f0f84…` |
| matched72 IDs `DEV_MATCHED_GAME_IDS.json` | `9f754b0e1c7680a0051b119ec59e2f0603236be447c483491b90a70af61b81e6` |
| ADMISSIBLE_QUOTES / COVERAGE_MANIFEST | `75c0b14c…` / `bfcf8ff4…` |
| `MARKET_E2E_R2B_CONSUME.json` | `380d5300…` |
| `DEV_RESEARCH_t5137u_MATCHED72.json` | `88d63eb7…` |
| `ONE_RUN.json` / `ONE_EXEC_RESULT_t5116u.json` | `96478f6b…` / `91324259…` |

R2-C remains **DATA_COVERAGE_BLOCKED**. G5 unchanged. Normalized 94 (`0a49afa3`)
was not substituted. No parent file rewritten.

## Inputs frozen before any C2/C3 fit

- Existing 437 REG DEV rows only (2020 n=210, 2021 n=227). Fields used:
  `game_id`, `season`, `week`, `actual_margin`, `m_if`, `m_challenger`.
- No new PBP / outcomes / sources / pulls. No 2022–26 scoring. No original
  Q2 / 2017 look. No IF/Q2 refit. No extra HFA.

## Q2 lineage

JSON has **no** `m_q2` column. `m_challenger` is the frozen 50/50
`x(0.5)=(1-0.5)*IF + 0.5*Q2` from prior R2-B2.

Algebraic recovery `Q2=2*m_challenger−m_if` is used **only** after that
lineage is documented. Recovered Q2 is **not** a newly generated forecast.

1e-9 check on all 437 identities: max abs reconstructed-blend residual **0.0**.
Missing / nonfinite / mismatched identities refuse; no imputation.

## Arms (code + tests; not fitted on real 2020 yet)

- **C0** unchanged IF
- **C1** unchanged frozen 50/50
- **C2** `x(0.5)+b` with `b=median(actual−x(0.5))` on 2020 only
- **C3** `w∈{0,0.01,…,1}`; `b(w)=median(actual−x(w))` on 2020 only; min
  unrounded 2020 MAE; ties → `w` closest to 0.5 then smaller `w`

C3 selection + all candidate training losses are frozen **before** 2021 in
code (tested). Real C2/C3 fit is **not** run until Alex GO.

## Market n=37 identity (selection-limited; IDs frozen before fit)

2021 ∩ OLD matched72 = **37** IDs (`2021_02_NYG_WAS` … `2021_18_DAL_PHI`).
IDs sha `54c8f5facb275e8084aaa6a07d457e7da2189e13270224d6343ee53491543113`.
Quote join used sealed ADMISSIBLE_QUOTES / manifest, same KO−60 / ≤24h /
DK-FD / sign rules as market E2E. **No outcomes scored. No probabilities
invented.** n=37 is selection-limited ≠ representative market validation.

## Isolated freeze package

`data/ops/nfl-t5141u-r3-dev-calibration/`

| File | sha256 |
| ---- | ------ |
| `FREEZE_MANIFEST.json` | `999c9ece9bde222e23103b7d683d7603388f6677d7c94262701310d055c50d20` |
| `PROTOCOL.json` | `46e10a0a408c201ffafce39618af2b6290fd01fb4baab8b75aaa12930a8b75cc` |
| `INPUT_PINS.json` | `6c816b2bad56dbfe89b03f2159bfa2b5f2d22a15d106476df23194f540a72204` |
| `IDENTITY_FREEZE.json` | `5b2369cbe9092372c2bc1b7bcf5cbd3e940a3ea9a9eb4690e8dc36f7afd64533` |
| `Q2_LINEAGE.json` | `fc23f94253accb92080319869d588196fb7719ae01c4e0e11cc80f188c9d75c4` |
| `MARKET_N37_IDENTITY.json` | `c91cd2c6665a3f80ad5f682f22938d99dc24f6f011db68aebffdbf4b60c17fc8` |
| `STOP_AWAITING_ALEX_PRECOMP_GO.json` | `f6eef77f32f0bd9fa351c3c904aad4bf2cf286640587da2f0dbb4834ccc54b57` |

Canonical protocol sha `e3c8f2df…`. Code sha
`8b9ebc68f71dca033c1813e7099abb63d38b712a45ece8b42aa10c2e369c4e88`.

**Not written:** `C3_SELECTION_FREEZE.json`,
`DEV_RESEARCH_t5141u_R3_DEV_CALIBRATION.json`.

## Tests

```
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_t5141u_r3_dev_calibration.py \
  tests/test_nfl_t5137u_matched72_dev_research.py \
  tests/test_nfl_t5119u_r2b_market_e2e.py \
  tests/test_nfl_t5125u_r2b2_dev_cohort.py \
  tests/test_nfl_t5129u_r2_byte_rehash.py
# 71 passed
```

Covered: refusal (missing/nonfinite, extra HFA, EVAL bind, 94-sub, parent
overwrite, no GO), 1e-9 blend identity, C3 tie-break, freeze-before-2021,
seed 20261101 / B=10000, no imputation, repo freeze is pre-fit + STOP.

## After Alex pre-computation GO (not done)

One diagnostic execution only:

```
python3 scripts/nfl/run_nfl_r3_dev_calibration_t5141u.py --go t5141u-alex-precomp-go
```

Then: persist isolated DEV_RESEARCH record (2020 training + 2021 n=227 +
market n=37); tip CURSOR_ADDENDUM sha8. No winner. No 2021/market retune.
No EVAL bind. Intervals are conditional on fitted parameters.

## Labels

`DEV_RESEARCH` · exploratory calibration · outcomes already consumed ·
RETRO_FIT vintage limitations · `eval=null` · CERT=0 ·
G5 `DATA_COVERAGE_BLOCKED`

## Hashes

| Artifact | sha256 / tip |
| -------- | ------------ |
| OWNER CLEAR t5141u | `714ced10` |
| Cos ORDER | `1155f43f` |
| PREFLIGHT | `a23e01dd` |
| uploaded/on-branch DEV437 file | `66c3bde1` |
| DEV437 record | `0550ef9b` |
| parent #693 HEAD | `316345fa` |
| this implementation tip | `acffed2057a937a8bbd8ee3bba7c88eaa358ebcb` |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC · STOP for Alex precomp.
