# REQUEST v3.1 — 2024 / 2025 holdout score (does not open)

**Kind:** REQUEST v3.1. Filing this file **opens nothing**.  
**Authorized to file by:** IMV ruling
`/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v5.txt`
sha256 `e7a0d737ab6116f40884115b667aa0abda671c29cdeaf7ac3ccf8c0940abb3c4`
(sha8 `e7a0d737`): request v3 may go to Ryan for CLEAR once D-1, D-3 and D-4
are folded into a v3.1. **D-2 runner is not in this filing.** Opening still
needs IMV review of **this v3.1 sha256** and Ryan’s explicit CLEAR.  
**Cites IMV originals (D-1: full IMV path + package byte copy):**

| sha8 | IMV original path | sha256 | package copy |
|---|---|---|---|
| `e7a0d737` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v5.txt` | `e7a0d737ab6116f40884115b667aa0abda671c29cdeaf7ac3ccf8c0940abb3c4` | `seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v5.txt` |
| `1ef1f0a7` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v4.txt` | `1ef1f0a7ead7cb9397f7849785b6d3a0fa286526d1770f260c10062083afd083` | `seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v4.txt` |
| `d18ebf22` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_B3_PATH1_EXPORT_v1.txt` | `d18ebf22454073817d21b217b98cd9210a481369dbce7694929ac95114866d65` | `seeded/IMV_RULING_NFL_INJURY_B3_PATH1_EXPORT_v1.txt` |
| `501e8a99` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_B3_PATH1_EXPORT_v1_ERRATUM_v1.txt` | `501e8a99dcb1a6553a3d8e40dc76918cc015705bcd336d0e50ac397a07662477` | `seeded/IMV_RULING_NFL_INJURY_B3_PATH1_EXPORT_v1_ERRATUM_v1.txt` |

Store copies: `/cursor/stores/self/imv-inputs/<name>`. See
`notes/d1-imv-original-paths.md`. Copy `0e0d54bc` is **NON-AUTHORITATIVE**
and is not cited.

**Supersedes for review:** request v3 sha `4c40a0e7` (file left unchanged in
this package). Earlier unmerged
`ops/nfl_injury_audit_t4274u/injury-holdout-request-2024-2025-v3/` draft
unchanged. v2 `0594a893` and runner `4f937c50` unchanged. v1 `f74b3029`
unchanged.  
**Governs besides the originals:** SoT spec `a156459b`; acceptance `54bc78ec`;
Ryan Path 1 `1298bddb` (pre-2024 frozen rerun only — does **not** CLEAR the
holdout); holdout STOP `d6fca6f0` remains in force until CLEAR.  
**Protocol:** `injury-residual-cal-v2`. Scorer: this package
`run_injury_residual_evaluator.py` sha256
`ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6`.  
**Expected answers:** `1358bc64a4e83fc5d56426eecb4245a346f3f2a4b7e0443072dc019b9bd65d9f`
(successor of `a70edde2`; filed in commit `74662be2` before the v6.1 scorer).  
**Status:** **NOT RUN.** No 2024/2025 listing, roster, schedule, outcome, close,
or holdout export was opened to write this. No runner that can read 2024/25 is
attached (D-2 waits for Ryan’s CLEAR). `NFL_TOTALS_*` unset. No tokens.
Overlays stay off.

This document may be scored **only after** (1) IMV review of **this v3.1
sha256** **and** (2) Ryan’s **explicit CLEAR**, cited by **message id** and
**decision-file sha**. An agent’s claim of approval is not Ryan’s CLEAR. The
D-2 runner, if CLEARed, still needs its own IMV review before any 2024/25 read.

**Once-only / abort:** the holdout may be opened **once**. A lock must be written
before any 2024/2025 read. An abort after that lock consumes the holdout.
Filing this request is not an opening.

**Research-only:** no product claim, no certification claim, no “improves
accuracy” copy. Even a later VALUE PROVEN result is research-grade until a
timestamped close source replicates it. Close label:
**comparative research, not certified CLV**. Metric name: **close vs outcome**.

---

## 0. C-1..C-4 (met in this package; required by `1ef1f0a7`)

### C-1 — originals re-seeded; provenance ruling field fixed

Byte copies of `d18ebf22`, `501e8a99`, and `1ef1f0a7` are in `seeded/`.
Provenance / scorer `REQUIRED_RULING` is `1ef1f0a7…`. The `_v4_CITED` copy
`0e0d54bc` is labeled non-authoritative
(`seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v4_CITED.NON_AUTHORITATIVE.md`).
DELETE NOTHING.

### C-2 — 11-row identity pin; holdout incomplete-row rule

le2023 pin (export `a38a55bb`, before any close/outcome join):

```
2013_1_CIN_CHI
2013_1_NYG_DAL
2014_15_SF_SEA
2015_1_NO_ARI
2017_1_IND_LA
2020_1_GB_MIN
2020_6_KC_BUF
2022_2_IND_JAX
2022_7_CHI_NE
2022_12_BAL_JAX
2023_5_HOU_ATL
```

Counts from the export: 11 total; 2013:2, 2014:1, 2015:1, 2017:1, 2020:2,
2022:3, 2023:1. Each pinned row: `complete=false`; `delta_margin` =
`delta_total` = null; `source_ts` = `as_of_ts` = `kickoff_utc` =
`source_ts_home` = `source_ts_away` = null. Unexpected incomplete id, or a
non-null delta / per-side timestamp on a pinned row → STOP.
**D-5:** a pinned `game_id` that is `complete=true` → STOP on set mismatch
(T-9 fixture; the other 10 pinned rows stay incomplete).

**Holdout incomplete-row rule (pre-declared; no 2024/25 count):** after CLEAR,
from the **holdout export**, **before any outcome or close join**:

1. incomplete iff `complete=false`;
2. require all five timestamps null and both deltas null;
3. complete + null timestamp → STOP; incomplete + timestamp or non-null delta → STOP;
4. exclude identically in both arms;
5. record `n_incomplete` total and by season, and pin the observed `game_id` set.

See `notes/c2-holdout-incomplete-row-rule.md`.

### C-3 — raw report-time format; holdout check

`8e2a15ac` listings (`/tmp/injury-fit-raw-le2023/listings/`, seasons 2013–2023
only): **58653 / 58653** `date_modified` values end in `Z`. Naive count = 0.
**D-3:** 58653 raw rows vs Path 1 `n_listing_rows=56537` is **2116** playoff
rows dropped by frozen `load_listings()` (`game_type != REG`): WC 1010, DIV
669, CON 324, SB 113. REG kept = 56537. Week-parse / year / holdout skips = 0.
See `notes/d3-listing-row-reconcile.md`.
The 4 games with recorded kickoff − as_of < 5 h
(`2023_15_LAC_LV`, `2022_10_CLE_MIA`, `2023_12_MIA_NYJ`, `2023_14_HOU_NYJ`)
have matching raw `…Z` strings. They are zone-bearing UTC. The frozen helper’s
naive-as-UTC branch is unused. **No export correction. Those 4 games are not
excluded.** Evidence: `notes/c3-raw-report-time-format.md`,
`notes/c3-raw-short-lead-rows.csv`, `notes/c3-listings-sha256.txt`.

**Holdout export — same check:** census `date_modified` on holdout listings
before join. All zone-bearing (`Z` or numeric offset) → proceed. Any naive /
zoneless → STOP, then correct the export or exclude recorded gap < 5 h by this
same pre-declared rule, identically in both arms.

### C-4 — `852fe21c` before the v5 run

Inspectable first-parent order on `cursor/nfl-injury-evaluator-v5-1a07`:

| commit | time UTC | role |
|---|---|---|
| `852fe21c` | 2026-10-24 13:23:02 | v5 expected answers |
| `c3bc0165` | 2026-10-24 13:24:36 | v5 scorer |
| (run) `out/evaluator_results.json` mtime | 2026-10-24 13:25:04 | v5 run |
| `548b2e18` | 2026-10-24 13:27:06 | v5 outputs |

The v5 run **log text** does not print `852fe21c` (IMV log-channel:
secondhand). Commit timestamp vs run-log file: 13:23:02 before 13:25:36.

**D-4 — v6 commit order** (also in `notes/c4-expected-answers-commit-order.md`):

| commit | time UTC | role |
|---|---|---|
| `967ec5d7` | 2026-10-24 13:36:02 | v6 expected answers |
| `2bf6e90c` | 2026-10-24 13:36:05 | record that hash |
| `6af27a22` | 2026-10-24 13:37:16 | v6 scorer |
| `d4138ed6` | 2026-10-24 13:40:06 | v6 outputs + request v3 |

`967ec5d7` before `6af27a22`. Git order stays secondhand for IMV.

Carried from `1ef1f0a7`: M-4 open correlation stays NOT RUN until a verified
timestamped open exists. M-5 deferred. Holdout export must use the same writer
(frozen helpers) and the a38a55bb-style sidecar (on-disk `.sha256.v2` is the
pin; blob hash is not).

---

## 1. Frozen record

| Object | Frozen value |
|---|---|
| HEAD / code sha | `8e2a15ac581277ecda71ea745c3b3477185d733b` |
| Config hash (`NFL_TOTALS_*` unset) | `0d491abef53cb67e82106dda184fb40fbe21fc3883afd8313fd87108cf40d6cb` |
| Bound hash | `049f97d679968165506fa71cdcf98038a65196ca52fa824a689742bd56b3e0dc` |
| Spec C | `theta=0.80`, D/Q/L `0.15/0.60/0.75`, caps `2.0/2.0` |
| Fit object | `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657` |
| Fit script | `8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c` |
| le2023 export pin (on-disk) | `a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8` |
| le2023 export blob (not a pin) | `46d2a5657d1b5a5eb1af03f4d643afbfaa4762f31260daff439b5df1ac1456eb` |
| Frozen historical export (untouched) | `d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8` |
| Null contract | `ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2` |
| v6.1 scorer | `ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6` |
| Expected answers | `1358bc64a4e83fc5d56426eecb4245a346f3f2a4b7e0443072dc019b9bd65d9f` |
| Seed | `20261023` (`numpy.default_rng`) n_boot=10000 |
| σ_margin / σ_total | 13.5 / 14.0 (no √2 rescale) |

The holdout export does not exist yet and is **not** produced by this filing.
After CLEAR it must be written by the same Path 1 writer (frozen helpers),
le2023-style timestamps, on-disk `.sha256.v2` pin. That on-disk sha becomes
the holdout `REQUIRED_EXPORT`. The blob hash is not the pin.

---

## 2. Universe and join (after CLEAR only)

- NFL **REG** `season ∈ {2024, 2025}`. POST dropped. 2026 excluded. Both
  seasons are the two full sealed seasons (weeks 1–18). A season may not be
  dropped after seeing close-vs-outcome.
- Join `(season, week, home, away)` with aliases `LAR`/`STL`→`LA`, `SD`→`LAC`,
  `OAK`→`LV`, `WSH`→`WAS`, `JAC`→`JAX`.
- Base: record/HFA as in the v6 scorer (`inputs/record_baseline_le2023.csv`
  method; holdout baseline built the same way after CLEAR). Injury residual
  from the holdout export. Incomplete rows never scored.
- Pooled: one holdout on the two full seasons.
- Close exclusion decided **before** either arm is scored, never by edge.

---

## 3. Close (research-only paired delta)

| Item | Pre-registered rule |
|---|---|
| **Declaration** | provider close (nflverse schedule `spread_line`), book/consensus and capture time UNSPECIFIED |
| **As-of** | provider-defined close, timing unknown |
| **Totals close** | same-row nflverse `total_line` |
| **Benchmark 5a653f63** | no comparison, no claim |
| **Missing close** | no impute, no 0; exclude from both arms; report `n_missing_close` overall and per season |
| **Claim** | no product or cert claim |

---

## 4. I-1..I-5 verbatim from a156459b s7

Quoted exactly from `seeded/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt` sha
`a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881`.

```
I-1  Paired comparison, adjusted vs base, same games, priced at the same as_of_ts, against
     the CLOSING line: CLV (points and implied-prob), ATS win rate, log-loss delta.
I-2  Minimum sample: >= 500 games with a non-zero adjustment in the sealed holdout and
     >= 2 full seasons; below that the result is INCONCLUSIVE (no claim).
I-3  Multiple comparisons: 3 markets x 3 metrics = 9 tests; Holm-Bonferroni at family
     alpha 0.05. Primary endpoint = mean CLV delta (spread) - stated now, not chosen later.
I-4  Decision rule: VALUE PROVEN only if primary endpoint significant after Holm, its 95%
     block-bootstrap CI excludes 0, and K-4 passes. Anything else = NO CLAIM.
I-5  Soft, borderline or insignificant results cannot become a product claim, marketing
     copy, or a "improves accuracy" statement. Report them as null results.
```

Non-zero adjustment = `Δmargin ≠ 0` or `Δtotal ≠ 0` (not `edge ≠ 0`).
Full season: weeks 1–18 for 2024 and 2025. I-1 “CLV” is scored as
**close vs outcome**. VALUE PROVEN also requires primary CI **lo > 0**.
ATS on no-pick (model==close or p==0.5) is **None**, not a loss.

---

## 5. K-2..K-4 verbatim from a156459b s6

```
K-2  Metrics, base vs adjusted on the same games: Brier and log loss (win prob);
     cover reliability for spread and total (predicted cover prob vs actual);
     reliability diagram in 10 bins with counts.
K-3  CIs: block bootstrap by NFL week, 10,000 resamples, 95% percentile CI, paired.
K-4  Gate: adjusted must not be worse than base: upper 95% CI of (adj - base) log loss
     <= 0.002 and Brier <= 0.0005. Calibration slope of adjusted within [0.9, 1.1].
     Failing = layer stays off.
```

Seed **20261023**, `numpy.default_rng`. Same scorer as the v6 le2023 dry-run.

---

## 6. Tokens

The builder must not create either token. Filing v3 does not create them.

| Token | Who writes it | Required contents |
|---|---|---|
| Ryan CLEAR | Ryan only | recorded words, message id, decision-file sha, plus §1 frozen shas |
| IMV token | IMV only, after a PASS on **this request** | PASS ruling sha and this v3 request sha |

---

## 7. Still forbidden until CLEAR

- Open, read, or join 2024/2025 listings, rosters, depth, outcomes, or closes.
- Build or run the D-2 holdout runner (waits for Ryan’s CLEAR).
- Produce or score a holdout export.
- Set any `NFL_TOTALS_*`.
- Merge this PR, unlock overlays, deploy, or apply on publish.
- Pin a blob hash instead of the on-disk export sha.
- Compare this close to benchmark `5a653f63`.
- Write the Ryan or IMV tokens.
- Make a product or cert claim.
- Reinterpret zone-bearing `Z` as ET.

NO-GO. Coming Soon ON. ELIGIBLE ≠ CLEAR. VALUE PROVEN ≠ product claim.

---

*REQUEST v3.1. IMV review of this sha **and** Ryan CLEAR (message id +
decision-file sha) are both required. Once-only. D-2 runner is not attached.
Cites `e7a0d737`, `1ef1f0a7`, `d18ebf22`, `501e8a99` by full IMV path.
Scorer `ca98ae0e`. Expected answers `1358bc64`.*
