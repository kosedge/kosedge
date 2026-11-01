# CURSOR ADDENDUM t5141u — R3-DEV-CALIBRATION (one diagnostic + STOP for Phase B RO)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5141u **714ced10** · Cos ORDER **1155f43f** · PREFLIGHT **a23e01dd**
Parent #693 HEAD **316345fa**. Isolated new directory. No EVAL EXEC. No claim.
Alex PRECOMP GO tip **51752d97** accepted. **One** diagnostic executed.
**STOP — awaiting Alex Phase B numerical RO.** No retune. No second fit. No winner.

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
# 71 passed pre-GO; re-run after one record + contract tests
```

Covered: refusal (missing/nonfinite, extra HFA, EVAL bind, 94-sub, parent
overwrite, no GO), 1e-9 blend identity, C3 tie-break, freeze-before-2021,
seed 20261101 / B=10000, no imputation, exclusive create, materialized
DEV_RESEARCH contract (`eval=null`, `winner=null`).

## One authorized diagnostic (Alex GO 51752d97)

Exact command run once:

```
python3 scripts/nfl/run_nfl_r3_dev_calibration_t5141u.py --go t5141u-alex-precomp-go
```

C3 frozen before 2021: **w=0.75**, **b=−1.8046804298045456**, 2020 MAE
10.300814509116526, 101 candidate losses persisted. C2: w=0.5,
b=−1.7997529471434337. `winner=null`. `selected_from_2021=false`.
`eval=null`. Intervals conditional on fitted parameters. Negative diffs
favor the calibrated arm. Crossing zero / mixed = INCONCLUSIVE.

### 2020 training (in-sample; reported separately; n=210)

| Arm | MAE | RMSE | bias |
| --- | --- | ---- | ---- |
| C0 | 10.59784751645663 | 13.857689151991654 | +1.4890595938369624 |
| C1 | 10.409584852635769 | 13.53639633770918 | +2.2075173923531795 |
| C2 | 10.313501682098197 | 13.361405787445493 | +0.40776444520974536 |
| C3 | 10.300814509116526 | 13.307471503037403 | +0.7620658618067421 |

Paired mean signed |loss| diffs (B=10000, seed 20261101):

| Compare | mean | game CI95 | week CI95 |
| ------- | ---- | --------- | --------- |
| C2 vs C0 | −0.2843458343584324 | [−0.61842, +0.03722] INCONCLUSIVE | [−0.52702, −0.04001] CI_EXCLUDES_ZERO |
| C2 vs C1 | −0.09608317053757108 | [−0.33704, +0.14019] INCONCLUSIVE | [−0.32228, +0.12045] INCONCLUSIVE |
| C3 vs C0 | −0.29703300734010296 | [−0.74879, +0.14321] INCONCLUSIVE | [−0.61737, +0.03726] INCONCLUSIVE |
| C3 vs C1 | −0.10877034351924164 | [−0.34896, +0.12790] INCONCLUSIVE | [−0.28775, +0.06970] INCONCLUSIVE |

### 2021 diagnostic (n=227; all fixed identities)

| Arm | MAE | RMSE | bias |
| --- | --- | ---- | ---- |
| C0 | 12.072358138517242 | 15.12918462779174 | −0.37797144296101337 |
| C1 | 11.619278251160985 | 14.467722324087264 | +0.19547570238588982 |
| C2 | 11.587351395480002 | 14.55508447157613 | −1.604277244757544 |
| C3 | 11.424322690707815 | 14.362386201990473 | −1.322481154745204 |

| Compare | mean | game CI95 | week CI95 |
| ------- | ---- | --------- | --------- |
| C2 vs C0 | −0.4850067430372398 | [−0.84172, −0.11697] CI_EXCLUDES_ZERO | [−0.81591, −0.16561] CI_EXCLUDES_ZERO |
| C2 vs C1 | −0.03192685568098301 | [−0.26367, +0.20167] INCONCLUSIVE | [−0.26107, +0.22886] INCONCLUSIVE |
| C3 vs C0 | −0.6480354478094289 | [−1.13590, −0.13955] CI_EXCLUDES_ZERO | [−1.10627, −0.20169] CI_EXCLUDES_ZERO |
| C3 vs C1 | −0.19495556045317217 | [−0.44911, +0.06540] INCONCLUSIVE | [−0.45321, +0.07432] INCONCLUSIVE |

C2 vs C1 and C3 vs C1 cross zero — INCONCLUSIVE vs the frozen 50/50.
Unfavorable / mixed results reported unchanged. **No winner selected.**

### Secondary market n=37 (selection-limited ≠ representative)

| Arm | MAE | RMSE | bias |
| --- | --- | ---- | ---- |
| C0 | 10.415547950987794 | 13.939186763559066 | −2.017919813068005 |
| C1 | 9.615512144106612 | 12.758784178402353 | −0.8250746302546401 |
| C2 | 9.758498586145333 | 12.999828667202879 | −2.6248275773980736 |
| C3 | 9.516997422770345 | 12.611114640892874 | −2.0333324686525036 |
| market | 8.614864864864865 | 11.245344382021845 | −1.6689189189189189 |

| Compare | mean | game CI95 | week CI95 |
| ------- | ---- | --------- | --------- |
| C2 vs C0 | −0.6570493648424599 | INCONCLUSIVE | CI_EXCLUDES_ZERO |
| C2 vs C1 | **+0.14298644203872027** | INCONCLUSIVE | INCONCLUSIVE |
| C3 vs C0 | −0.8985505282174489 | INCONCLUSIVE | INCONCLUSIVE |
| C3 vs C1 | −0.09851472133626855 | INCONCLUSIVE | INCONCLUSIVE |
| C0 vs market | +1.8006830861229284 | CI_EXCLUDES_ZERO | CI_EXCLUDES_ZERO |
| C1 vs market | +1.0006472792417482 | INCONCLUSIVE | INCONCLUSIVE |
| C2 vs market | +1.1436337212804686 | INCONCLUSIVE | INCONCLUSIVE |
| C3 vs market | +0.9021325579054796 | INCONCLUSIVE | INCONCLUSIVE |

C2 MAE on n=37 is **worse** than uncalibrated C1 (+0.143 mean signed |loss|).
All four arms have higher MAE than market. Mixed / crossing zero =
INCONCLUSIVE. Not representative market validation. No probabilities
invented. No retune.

## Isolated result files

| File | sha256 |
| ---- | ------ |
| `DEV_RESEARCH_t5141u_R3_DEV_CALIBRATION.json` file | `4dcd7cbccedeb7c4652793ac30b827a67ff07c4a310c7900336e8d3426b2501b` |
| payload `record_sha256` | `8d5e454345ac3c2954932223b3f8fe97547b0f1e079c5d02b0907fa6376b54c0` |
| `C3_SELECTION_FREEZE.json` file | `3792726da7b6fb69b4639521111e3e9054cb6e7de1cec916d8a9c2ba9de48a5f` |
| C3 selection payload | `6efa32a22f97b2de073513a1a67065f65a2b909673f0bcc8e1ede49fc5036b58` |

Pre-fit freeze files are byte-unchanged (`FREEZE_MANIFEST` `999c9ece…`).

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
| Alex PRECOMP GO | `51752d97` |
| uploaded/on-branch DEV437 file | `66c3bde1` |
| DEV437 record | `0550ef9b` |
| parent #693 HEAD | `316345fa` |
| implementation tip | `acffed20` |
| this one-exec result tip | *(stamped after commit)* |

CERT=0 · DRAFT≠merge · no merge/send · no EVAL EXEC · STOP for Alex Phase B RO.
