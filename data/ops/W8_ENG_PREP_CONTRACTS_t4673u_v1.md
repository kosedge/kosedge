# W8 ENG PREP CONTRACTS — t4673u v1

**Lane:** Cursor / engineering PREPARATION only (paper + stub contract specs).  
**Authority:** DECISION t4673u RESUME NFL MODEL PARALLEL · Ryan.  
**Parent defects:** Codex **88a08cae** · IMV RETURN **75141507** (C1-STDEV etc).  
**Prior PASS_ENG `dd6cba0c`:** **SUPERSEDED** — do not inherit.  
**Institutional memory:** `no prior grades` (`data/knowledge/nfl/` empty of graded cards).

| pin | value |
|---|---|
| This paper | `data/ops/W8_ENG_PREP_CONTRACTS_t4673u_v1.md` |
| Packet dir | `data/ops/nfl-t4673u-w8-eng-prep/` |
| Codex parent | `88a08caee9b076ce99a94cc2f8eba9e63319ffa74ea24c80eebec59658216e65` · #649 · tip challenged `ab7d977d` |
| IMV RETURN parent | **75141507** — cited with 88a08cae as the RETURN that adopted C1-STDEV / bypass / time / invent gaps. Full IMV RETURN body is **not in this checkout** (not on `deploy-vercel`; later papers t4662u / t4668u pair `88a08cae / 75141507`). Mapping below uses Codex gap ids that IMV RETURN named. |
| SUPERSEDED | PASS_ENG **dd6cba0c** — not current authority. Any later grade must re-run the corrected oracles in this paper. |
| Challenged WS-A packet | #645 DRAFT `cursor/w8-full-slate-engine-5bcd` · IMV criteria **062197c0** · consume proof **7c2d9625** / **0be23ede** · completeness **675e1cf7** |
| Path under proof | `scripts/nfl/run_w8_research_forecast_t4564u.py` → `_simulate_one` → `simulate_nfl_game` (exists on #645, **not** on `deploy-vercel`) |
| Prior oracles (vacuous / incomplete) | `services/model-service/tests/test_nfl_w8_forecast_consumption_contracts_t4643u.py` sha256 `4875faeb…` on #645 |
| Verdict of this paper | **PREP_CONTRACTS_FILED** · **NOT** `PASS_ENG_CONTRACT` · **NOT** `FAIL_ENG_CONTRACT` · **NOT** a repair land · **NOT** CERT |

Hard locks honored: **NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen**.  
No B repairs implemented. No merge. No deploy. No paid Odds. No A1 API restore. No CERT. No holdout mutate.

---

## What this filing is / is not

**Is:** bounded repair **plan** + corrected **test contract** specs for four held B items. Each item maps to 88a08cae / 75141507 gap ids. Each acceptance test names a **vacuity mutation** (must FAIL the test if the protection is deleted or the oracle is weakened back to a grep / means-only / pre-injected-dict check).

**Is not:** implementation of those repairs. Not a re-grade of #645. Not a warehouse SELECT. Not Odds fail-closed (that is t4662u / t4668u). Not Exp D-R / #648. Not a W8 official-row invent. Not a season-pack rewrite.

`PASS_ENG dd6cba0c` is **SUPERSEDED**. A later implementer who cites dd6cba0c as already-green has the wrong SoT.

---

## Parent gap map (88a08cae × 75141507 → this prep)

Codex 88a08cae severity labels are preserved. IMV RETURN 75141507 is the grade that treated the BLOCKING / HIGH items as **RETURN** (C1-STDEV etc). This prep covers **only** the four items Ryan ordered.

| this item | Codex 88a08cae id | IMV RETURN 75141507 | Ryan mode | 88a08cae severity | held B? |
|---|---|---|---|---|---|
| 1. Injury-impact market invariance oracle | **G-C1-STDEV** | C1-STDEV (wrong component) | silent fallback · incomplete tests | **BLOCKING** (C1) | **YES — plan only** |
| 2. Fixture / builder pins / bypasses | **G-C1-BYPASS** (+ **G-C1-EPA-PARTIAL**) | C1/C3 bypass | incomplete tests · stale inputs | **HIGH** (C1/C3) | **YES — plan only** |
| 3. Historical EPA as-of cutoff | **G-TIME-EPA** (+ **G-LIVE-DOWNLOAD**, **G-C2-EPA-PRIOR**) | time leakage · stale grain | time leakage | **HIGH** (C2/C3) | **YES — plan only** |
| 4. W8 missingness guarantees | **G-INVENT-W8** (+ **G-DUP-INJURY** writers 1–3) | invent W8 · silent fallback | invent W8 | **HIGH** (C2/G3) | **YES — plan only** |

Related 88a08cae gaps **not** in this prep (do not silently expand B):

| left out | id | why left out |
|---|---|---|
| Odds vacuous test | G-C7-VACUOUS | Separate Odds fail-closed lane (t4662u / t4668u). No paid Odds here. |
| Warehouse CLOSED-as-passed | G-G1-GREP · G-C5-PR-TITLE | Warehouse SELECT is Needs-CLEAR; not a B repair in this order. |
| Season rolling preferred | G-C6-ROLLING | C6b DEFER + Needs-CLEAR stays. |
| Ad-hoc sim third caller | G-DUP-SIM | Named; not this ticket. |
| Copied `as_of` clock | G-VINTAGE-COPY | Adjacent to item 3; not a fourth B land. |
| Calibration overlay | G-CAL-SILENT | LOW; not ordered. |

---

## Current (defective) oracles — why they are vacuous

Facts from #645 test file `4875faeb…` + Codex independent C1 re-run (seed 4643 / 1200 sims). Not a new experiment.

| current test | what it actually executes | why 88a08cae / 75141507 RETURN |
|---|---|---|
| `test_c1_injury_impact_field_consumed_means_gated` | `NflGameInputs(**fx)` → `simulate_nfl_game`; checks `injuries_depth.margin_points==0` and mean points equal | **G-C1-STDEV.** Means match. `markets.spread_home` moved −0.14 → −0.13 via ungated `error_regime`. Codex table: `stdev_widen` 0.2182 → 0.2387. IMV C1: FAIL if wrong component moves. |
| `test_c1_*` helpers | never call `_injury_impacts` / `_build_current_strength` / `_load_canonical_week` / C3 packs | **G-C1-BYPASS.** C3 pins can rot; C1 stays green. |
| `test_c2_epa_missing_refuses_to_sim` | injects `strength={}` into `_simulate_one` | **G-C2-EPA-PRIOR.** Proves the sim gate, not that the builder refuses the 2025 pack. |
| `test_c2_g3_w8_official_missing_not_invented` | injects fixture dicts with `as_of_week` 7/6 | **G-INVENT-W8.** `_injury_impacts` and pack writer never run. |
| `test_c3_g1_no_warehouse_select_in_forecast_path` / `test_c7_*` | substring greps | Vacuous class (88a08cae G-C7-VACUOUS). Out of this prep except as a **forbidden oracle shape**. |

Engine facts (on `deploy-vercel` and on #645; line pins are current trunk):

- Mean injury term is confidence-gated: `nfl_handicapping_framework.py:311–341` (`injury_conf` default 0 → 0 mean points).
- `error_regime` averages **raw** impact without confidence: `framework.py:837–861` → `compute_error_regime_uncertainty(..., injury_impact=injury_impact_avg)` → `nfl_second_order_factors.py:120` (`* 0.15`).
- Totals-overlay stdev **is** confidence-gated: `nfl_simulator.py:438–447`. Error-regime stdev is **not**.
- W8 builder on #645 does not set `injury_nowcast_confidence_*` (`run_w8…:426–432`). Ticket string still `TICKET = "t4605u"`.
- `_build_current_strength` (`run_w8…:249–310`) has no `week <= 7` filter; only `team_df["week"].max() < 7` → exit. Values written to `*_epa_5g` (`:433–436`).
- Pack writer: `"w8_official_report": "PRESENT" if latest_week >= WEEK else "MISSING"` (`:691`). `_injury_impacts` hardcodes MISSING (`:355`) but `as_of_week = max(week)` when a team has no designations (`:325`), which drops `injury_as_of_week8` if `as_of_week == 8` (`:465–468`).

Sealed restore itself is **not** invented (pack week=7, `w8_official_report=MISSING`, n=153, sha256 `0c29ceea…`, 14/14 flags). The hole is **forward / untested writers**.

---

## Item 1 — Injury-impact market invariance oracle

**Gap ids:** 88a08cae **G-C1-STDEV** · IMV RETURN 75141507 **C1-STDEV**.  
**IMV bar:** C1 FAIL if perturbation has no effect, **wrong component moves**, or effect is non-deterministic without declared RNG (`062197c0` §C1).  
**Current contract (SUPERSEDED for this field):** C1-INJ-FIELD (`C0_C7_CONTRACT.md:39`) declares component = `diagnostics.injury_nowcast.home_impact` and **means unchanged**. `must_not_move` = `injuries_depth.margin_points` only.

### Corrected contract (C1-INJ-MARKET)

Two allowed landings — pick **exactly one** before any repair land. Default for this prep is **(a)** because W8 builder does not set confidence and the overlay is not authorized as a mean mover.

| landing | meaning | when allowed |
|---|---|---|
| **(a) INVARIANT** (default) | Hashed C1-INJ pair must leave **markets and uncertainty** unchanged | Current builder (conf=0). Injury overlay may stay labeled CONSUMED-into-`impact_*` identity only. |
| **(b) DECLARED-UNCERTAINTY** | `error_regime.stdev_widen` may move; markets may move only by a **hashed** delta listed in the fixture | Needs CLEAR. C5 must relabel overlay **CONSUMED-into-uncertainty**, not CONSUMED-into-means. |

Landing (a) required fields (C1_base `fc0f79f8…` → C1_inj_impact_only `ef31a571…`, seed 4643, sims 1200):

| field | invariant? |
|---|---|
| `diagnostics.injury_nowcast.home_impact` / `away_impact` | **NO** — these are the labeled identity (0.45 / 0.05) |
| `factor_contributions.injuries_depth.margin_points` / `total_points` | **YES** (0.0 at conf=0) |
| `diagnostics.mean_home_points` / `mean_away_points` | **YES** |
| `markets.spread_home` | **YES** — this is the Codex miss (−0.14 → −0.13 today) |
| `markets.home_win_prob` | **YES** |
| `markets.total` / `diagnostics.mean_total` (whichever the sim emits as the posted total) | **YES** |
| `factor_contributions.error_regime.raw_signals.stdev_widen` | **YES** under (a) |

Codex observed (do not treat as a new run; pin for the implementer to reproduce):

| | `spread_home` | `home_wp` | `mean_home` | `injuries_depth.margin` | `error_regime.stdev_widen` |
|---|---|---|---|---|---|
| C1_base | −0.14 | 0.4892 | 23.175 | 0.0 | 0.2182 |
| C1_inj_impact_only | **−0.13** | 0.4892 | 23.175 | 0.0 | **0.2387** |

### Acceptance tests (must FAIL when protection removed)

**T-C1-STDEV-1 — market equality (landing a).**  
Run the hashed pair. Assert `spread_home`, `home_win_prob`, posted total, and `error_regime.stdev_widen` are **bit-equal** (or equal within the sim’s existing deterministic rounding, same seed).  
**Protection-removed mutation:** delete / comment the confidence gate on `error_regime` (`framework.py:837–861` keep using raw impact) **or** restore today’s builder. Test **must FAIL** (spread and/or stdev_widen move).  
**Vacuity mutation (forbidden):** drop the market / stdev asserts and keep only means. That is the current green test. A later “PASS” that only checks means is **RETURN**.

**T-C1-STDEV-2 — component identity still holds.**  
`injury_nowcast.home_impact == 0.45` and `away_impact == 0.05` still required so the fixture cannot be swapped for a no-op pair.  
**Vacuity mutation:** accept any impact values as long as markets match — FAIL. The pair must be the hashed injury perturbation.

**T-C1-STDEV-3 — totals-overlay stdev stays confidence-gated.**  
`nfl_simulator.py:438–447` already multiplies by `injury_conf`. Assert totals-overlay `stdev_points` is 0.0 on this pair (conf=0).  
**Protection-removed mutation:** feed raw impact into that multiply. Test **must FAIL**.

**T-C1-STDEV-4 — do not count the R1 confidence test as current consume.**  
`test_c1_injury_with_confidence_moves_means_repair_target` already passes because the engine honors **injected** confidence. It is a repair-target, not evidence that today’s builder consumes injury into means. After any B land, this test stays labeled `REPAIR_TARGET` until the **builder** sets confidence.

### Bounded repair plan (not implemented)

1. **Preferred (a):** gate `error_regime` injury term by the same `injury_conf` used for means (`framework.py:311–316`), **or** pass `injury_impact=0.0` into `compute_error_regime_uncertainty` when conf=0. Re-run T-C1-STDEV-1..3.  
2. **Not this ticket:** landing (b) hashed-delta + C5 relabel. Needs CLEAR.  
3. **Not this ticket:** R1 “pass confidence when designations exist” (`BOUNDED_REPAIR_PLAN.md` After ACCEPT). That is a mean-effect change, not the invariance oracle.  
4. Do not “fix” by asserting a spread delta of 0.01 as expected without landing (b) CLEAR.

**Needs CLEAR before land:** none for landing (a) **paper**. CLEAR **is** required before merging any framework change to production, and before landing (b).

---

## Item 2 — Fixture / builder pins / bypasses

**Gap ids:** 88a08cae **G-C1-BYPASS**, **G-C1-EPA-PARTIAL** · IMV RETURN 75141507 C1/C3 bypass.  
**IMV bar:** C1 requires SoT → declared component; C3 requires vintage pin actually enforced.

### Corrected contract (C1-BUILDER-PIN)

At least **one** C1 path per CONSUMED family must start from a **hashed builder input** and execute the named builder, not `NflGameInputs(**json)`.

| family | hashed input | builder that must run | declared component | pin |
|---|---|---|---|---|
| EPA / strength | team-week parquet slice **or** C3 pack `cb1fe8c5…` plus a one-team boost | `_build_current_strength` | `base_efficiency.margin_points` + markets **and** (new) `*_epa_5g` / totals overlay if those fields are written | C3 EPA sha256 `cb1fe8c5e0495c417af3dc70f83cf4c419c1c1761b2dd233bc8546ad3face2c2` |
| Injury overlay | injury parquet slice **or** C3 pack `0c29ceea…` with one team’s impact perturbed | `_injury_impacts` | `impact_*` identity + Item 1 market invariance | C3 injury sha256 `0c29ceea500f34dd326e3b8879372fc6f2b6ea821ac72613ce4e35cadf013a97` |
| Rest | canonical schedule slice | `_load_canonical_week` + `_rest_days` | `rest_travel.margin_points` | schedule sha256 `d88ae73440d3da87198ddb9d8986e0a19773cd3626215e495138907c44ff43fe` |

Direct `simulate_nfl_game(NflGameInputs(**fx))` fixtures may remain as **engine-unit** oracles. They are **not** sufficient for C1 PASS after this prep.

C3 pin enforce (88a08cae G-LIVE-DOWNLOAD, adjacent):

- Before `_simulate_one`, builder compares parquet/pack sha256 to the C3 pin.
- Mismatch → `SystemExit` / `input_sha_mismatch`. No silent continue. No “refresh nflverse and keep the old filename.”

### Acceptance tests (must FAIL when protection removed)

**T-C1-PIN-1 — builder executed.**  
Oracle records `builder_fn` on the artifact (or the test calls the builder directly and asserts a side-effect only the builder can produce — e.g. `source` string `nflverse_stats_team_week_2026_w1_w7_play_weighted` for EPA, or `w8_official_report=MISSING` from `_injury_impacts`).  
**Vacuity mutation:** `assert "_build_current_strength" in W8_SCRIPT.read_text()` (today’s C4). That must **not** count.  
**Protection-removed mutation:** C1 helper goes back to `NflGameInputs(**fx)` only. Test **must FAIL**.

**T-C1-PIN-2 — C3 sha refuse.**  
Swap one byte of the EPA pack (or pass a wrong sha). Builder must refuse; no slate row written.  
**Vacuity mutation:** grep `sha256` in the script. Forbidden.  
**Protection-removed mutation:** delete the sha check; `_download` always refreshes. Test **must FAIL**.

**T-C1-PIN-3 — EPA totals overlay (G-C1-EPA-PARTIAL).**  
Perturb only `off_epa_per_play` / `home_off_epa_5g` on the builder output. Assert the **totals** overlay component moves; offense_index pair remains the index oracle. Today’s C1-EPA fixtures omit every `*_epa_5g` field.  
**Protection-removed mutation:** omit `*_epa_5g` from the fixture again. Test **must FAIL** (declared totals component does not move).

**T-C1-PIN-4 — fixture hashes remain pinned.**  
Keep `FIXTURES.sha256`. New builder-path fixtures get their own sha256 rows. Changing a fixture without updating the manifest fails.

### Bounded repair plan (not implemented)

1. Add builder-path fixtures under `data/ops/nfl-t4643u-w8-forecast-integrity/fixtures/` (or this packet’s `fixtures/`) that are **tiny hashed slices**, not live nflverse downloads.  
2. Wire tests to call `_build_current_strength` / `_injury_impacts` / `_rest_days` from the W8 module.  
3. Add C3 sha gate in the W8 script **after** Ryan CLEAR to touch that script. Until then, the test may be written against a local helper that the land will call.  
4. Do not download nflverse in CI. Do not open `DATABASE_URL`. Do not import `odds_api`.

**Needs CLEAR before land:** touching `run_w8_research_forecast_t4564u.py` (still `TICKET=t4605u` on #645). Paper may land first.

---

## Item 3 — Historical EPA as-of cutoff

**Gap ids:** 88a08cae **G-TIME-EPA**, **G-LIVE-DOWNLOAD**, **G-C2-EPA-PRIOR** · IMV RETURN 75141507 time leakage / stale grain.  
**IMV bar:** C2 missing/stale → declared fallback + flag; C3 vintage pin; no silent 2025 prior.

### Corrected contract (C3-EPA-ASOF)

| rule | required behavior |
|---|---|
| Week cap | Strength builder includes only `week <= 7` for a W8 research emit (or refuses if any `week > 7` row is present and the contract chooses refuse). |
| Label honesty | Must not write source `…_w1_w7…` if week-8+ rows were used. Must not store season-to-date EPA in `*_epa_5g` without a flag `epa_grain=season_to_date_w1_w7` (or rename the fields). |
| Kickoff vs row | `_g18_artifact` already blocks post-kickoff **forecast_ts**. That does **not** block post-kickoff **EPA rows**. After TNF 2026-W08-CAR@GB `2026-10-30T00:15:00Z`, a re-download can leak a played W8 box into “W1–W7” strength. |
| No silent 2025 prior | `_build_current_strength` on empty / `week.max() < 7` → `SystemExit` `MISSING current strength` **and** `nfl_team_efficiency_backbone_2026.json` (`prior_season=2025`, as_of 2026-08-08, sha256 `4cd45f85…`) is never opened. |
| C3 pin | EPA pack sha256 must MATCH `cb1fe8c5…` before sim (Item 2 T-C1-PIN-2). |

Sealed Oct 28 emit is pre-first-kickoff. This contract is a **re-run / future-download** hole, not a claim that the sealed slate used post-game EPA.

### Acceptance tests (must FAIL when protection removed)

**T-EPA-ASOF-1 — week-8 rows excluded or refused.**  
Fixture team-week frame: 32 teams × weeks 1–7 plus **one** week=8 row with an extreme EPA (e.g. +5.0).  
Pass iff (exclude): week-8 row does not change any team’s `off_epa_per_play` / indices vs the week≤7-only frame, **and** source does not claim `w1_w7` if week-8 was present; **or** (refuse): `SystemExit` naming week-8.  
**Protection-removed mutation:** delete the `week <= 7` filter (today’s code). Extreme week-8 EPA moves strength. Test **must FAIL**.  
**Vacuity mutation:** `assert team_df["week"].max() >= 7` (today’s existence gate). Forbidden — that stays green when week-8 leaks.

**T-EPA-ASOF-2 — `*_epa_5g` grain flag.**  
After builder, either `home_off_epa_5g` is unset **or** artifact/notes include `epa_grain=season_to_date_w1_w7` (or the field is renamed). Silent 5g name is FAIL.  
**Protection-removed mutation:** write season EPA into `*_epa_5g` with no flag (today). Test **must FAIL**.

**T-EPA-ASOF-3 — builder empty ≠ 2025 prior.**  
Call `_build_current_strength` on an empty / week-max<7 frame. Expect `SystemExit` `MISSING current strength`. Monkeypatch / wrap `open` / `Path.read_text` on `nfl_team_efficiency_backbone_2026.json` and assert it was **not** read.  
**Vacuity mutation:** today’s `test_c2_epa_missing_refuses_to_sim` (`strength={}` into `_simulate_one`). Forbidden as the sole C2-EPA oracle.  
**Protection-removed mutation:** one-line fallback onto the 2025 pack. Test **must FAIL**.

**T-EPA-ASOF-4 — first W8 kickoff is not a free pass.**  
Document TNF `2026-W08-CAR@GB` kickoff `2026-10-30T00:15:00Z`. A fixture with `forecast_ts` before kickoff and week-8 EPA rows still fails T-EPA-ASOF-1. Post-kickoff forecast_ts remains blocked by existing `_g18_artifact` (do not weaken).

### Bounded repair plan (not implemented)

1. In `_build_current_strength`, filter `team_df = team_df[team_df["week"] <= 7]` (or refuse).  
2. Stop writing season EPA into `*_epa_5g` without `epa_grain=…` (or stop writing those fields).  
3. Keep refuse-to-sim on `week.max() < 7`. Add the “2025 pack never opened” probe.  
4. Do not shrink Week 1. Do not invent week-8 EPA. Do not SELECT warehouse rolling (`nfl_dp_team_rolling_features_weekly`) — that is C6b Needs-CLEAR.

**Needs CLEAR before land:** builder script edit; any rename of `*_epa_5g` that season overlays also read.

---

## Item 4 — W8 missingness guarantees

**Gap ids:** 88a08cae **G-INVENT-W8**, **G-DUP-INJURY** · IMV RETURN 75141507 invent W8 / silent fallback.  
**IMV bar:** C2 G3 — W8 official MISSING stays flagged; overlay = last designated week; no invented official report (`062197c0` §C2). C7 auto-RETURN if inventing W8 official injury.

### Corrected contract (C2-G3-WRITERS)

Three writers, one rule. Tests must **call the writers**. Injecting `{as_of_week: 7}` is not C2.

| writer | #645 location | today’s rule | required rule |
|---|---|---|---|
| `_injury_impacts` | `run_w8…:313–372` | MISSING hardcoded; `as_of_week = max(week)` if no designations | `as_of_week` = last week **with designations**, else a documented non-8 sentinel; **always** keep `injury_as_of_week8` / `_away` if that week ≠ 8 **or** if the week-8 rows are empty stubs / unofficial |
| `_materialize_current_packs` | `run_w8…:656–691` | `PRESENT` if `latest_week >= 8` | **Never** `PRESENT` from nflverse designations. PRESENT only if a **separately pinned official-W8 SoT** exists (none today). |
| `audit_week_inputs` | `audit_w8_input_completeness_t4605u.py:270–272` | PRESENT if pack `week==8` | Same: PRESENT iff official-W8 SoT pin exists. Pack week==8 from nflverse is not official. |

Production nowcast `FROM nfl_dp_injuries` (`nfl_injury_nowcast.py:444–518`, warehouse max_week=3) stays **unwired** on the research emit. Ban a future import on that graph (test the import graph; do not SELECT).

Empty W8 stubs: `as_of_week != 8` **and** `injury_as_of_week8` still flagged.  
Designated nflverse week-8 rows: `w8_official_report` remains **MISSING**; G3 flags remain; overlay may use week-8 designations only if the contract **explicitly** says “unofficial nflverse designations, not official Wednesday book” **and** still flags official MISSING. Default: do not treat week-8 nflverse rows as official; keep last **official-designated** week (≤7 today).

Do **not** fix by writing week-8 official rows.

### Acceptance tests (must FAIL when protection removed)

**T-G3-1 — empty W8 stubs do not become week 8.**  
Frame: W7 designated rows + week-8 **empty** stub rows (no designations). Call `_injury_impacts`.  
Assert: every team `as_of_week != 8`; `w8_official_report=MISSING`; `_simulate_one` missing-set still contains `injury_as_of_week8` and `injury_as_of_week8_away`.  
**Protection-removed mutation:** restore `as_of_week = max(week)` on empty stubs (`:325`). `as_of_week==8` drops the flag (`:465–468`). Test **must FAIL**.  
**Vacuity mutation:** today’s `test_c2_g3_w8_official_missing_not_invented` (pre-set as_of_week 7/6). Forbidden as the sole G3 oracle.

**T-G3-2 — nflverse week-8 designations do not mint PRESENT.**  
Frame: at least one week-8 designated row. Call `_injury_impacts` **and** `_materialize_current_packs` (or the pack-writer fragment).  
Assert: `w8_official_report != "PRESENT"`; completeness evidence does not say PRESENT; G3 flags remain.  
**Protection-removed mutation:** restore `PRESENT if latest_week >= WEEK` (`:691`). Test **must FAIL**.

**T-G3-3 — completeness cannot close official from pack week.**  
Feed a pack with `week=8` and `w8_official_report=MISSING` (or PRESENT from a forged pack). Completeness `injury` official evidence stays MISSING unless an official-W8 SoT pin is present (none).  
**Protection-removed mutation:** `PRESENT if inj_week == week`. Test **must FAIL**.

**T-G3-4 — one fixture, three writers agree.**  
One hashed parquet slice → `_injury_impacts` as_of weeks, pack `week` / `w8_official_report`, completeness evidence are a **single documented function** of that slice (table in the test docstring). Disagreement is FAIL.  
**Vacuity mutation:** assert each writer “returns a dict.” Forbidden.

**T-G3-5 — sealed restore still honest (C4).**  
Keep `C2_sealed_restore_oracle.json` `6d303b90…`: 14/14 flags, pack `0c29ceea…`, week=7, MISSING. A repair that drops flags to make T-G3-1 green is C4 FAIL.

**T-G3-6 — no `FROM nfl_dp_injuries` on the research emit import graph.**  
Import-graph walk of `run_w8_research_forecast_t4564u.py`.  
**Vacuity mutation:** grep the one script file only (today’s G1 shape). Walk imports.  
**Protection-removed mutation:** `from src.services.nfl_injury_nowcast import fetch_nfl_injury_nowcast`. Test **must FAIL**.

### Bounded repair plan (not implemented)

1. Change `_injury_impacts` empty-team rule from `max(week)` to last designated week (or refuse / sentinel ≠ 8). Always append G3 flags when official W8 SoT is absent.  
2. Change pack writer to **never** set PRESENT from `latest_week >= 8`. PRESENT is a pinned-SoT branch that does not exist today.  
3. Change completeness official evidence to the same function.  
4. Do not invent W8 official rows. Do not wire warehouse injuries (max_week=3).

**Needs CLEAR before land:** builder + pack writer + completeness auditor (three files). Official-W8 SoT, if one is ever created, is a **separate** CLEAR — not this B.

---

## Non-vacuous oracle law (applies to all four)

A test is **vacuous** (IMV RETURN class 88a08cae / 75141507) if any of these hold:

1. It greps a substring that appears in any Python file (`"False" in text`, `"sha256" in text`).  
2. It injects the already-correct struct and never calls the writer that could invent / leak / bypass.  
3. It checks only the component the defect does **not** move (means-only C1-INJ).  
4. It can stay green after the named protection-removed mutation.

Each T-* above names a protection-removed mutation. Implementation PRs must keep those mutations as comments or as an explicit “remove-this-gate” hook that CI can run in a second job. A green suite with no failing mutation is **RETURN**, not PASS_ENG.

Stub files in `data/ops/nfl-t4673u-w8-eng-prep/stubs/` document the asserts. They are **not** collected by model-service pytest. They do **not** enable the W8 production path. They do **not** import Odds or warehouse.

---

## Bounded B sequence (after Ryan CLEAR — not this PR)

Order is the 88a08cae recommended list, clipped to the four ordered items:

| step | land | files (expected) | depends |
|---|---|---|---|
| B1 | Item 1 landing (a) — gate `error_regime` by `injury_conf` | `nfl_handicapping_framework.py` | T-C1-STDEV-* go RED on trunk, GREEN after |
| B2 | Item 2 builder-path fixtures + C3 sha refuse | W8 script + new fixtures + test file on the #645 line | B1 oracles still green (C4) |
| B3 | Item 3 `week <= 7` + grain flag + 2025-pack-not-opened | `_build_current_strength` | B2 sha refuse |
| B4 | Item 4 writer alignment (no PRESENT from nflverse) | `_injury_impacts` + pack writer + completeness | T-G3-5 sealed restore still green |

Do not merge. Do not deploy. Do not open Odds. Do not rematerialize holdout. Draft-only until a later COS_ORDER.

---

## CLEAR asks (required before implementation)

These are **asks**, not authorizations.

1. **Ryan / CoS CLEAR to implement held B repairs** — this paper is prep only. No B1–B4 land without a new order.  
2. **Landing choice for Item 1** — confirm **(a) INVARIANT** (default) vs **(b) DECLARED-UNCERTAINTY** (C5 relabel + hashed delta). Do not land (b) on silence.  
3. **CLEAR to edit** `scripts/nfl/run_w8_research_forecast_t4564u.py` (still labeled `t4605u` / `e65b9c77` on #645). Items 2–4 need that file.  
4. **CLEAR to edit** `nfl_handicapping_framework.py` (Item 1). Shared spine — game + any other `simulate_nfl_game` caller. Confirm ad-hoc HTTP / season overlays stay C4-green.  
5. **C3 pin freeze** — re-hash `cb1fe8c5…` / `0c29ceea…` / `550e1a8d…` / `d88ae734…` on the tip that will be repaired. Do not silently re-download.  
6. **Official-W8 SoT** — there is none. Do not CLEAR inventing rows. If a Wednesday official book is later pinned, that is a new SoT ticket.  
7. **Warehouse / Odds / A1 / CERT / Coming Soon / F2 / holdout** — **no ask**. Stay locked.  
8. **IMV RETURN 75141507 full text** — not in this checkout. CoS should deposit the IMV RETURN paper (or confirm sha256) next to 88a08cae before IMV re-grades a later land. This prep mapped C1-STDEV etc from Codex ids the RETURN adopted.  
9. **PASS_ENG dd6cba0c** — confirm SUPERSEDE in the register. Do not cite it as current.

---

## Non-actions (this lane)

- Did not implement B repairs.  
- Did not merge, deploy, restart, set-variables, or spend Odds.  
- Did not restore A1 API.  
- Did not lift CERT / NO-GO / Coming Soon / F2.  
- Did not mutate holdout.  
- Did not emit a new W8 slate.  
- Did not grade `PASS_ENG_CONTRACT` or `FAIL_ENG_CONTRACT`.  
- Did not reopen G34 / Exp D-R / #648.  
- Did not retitle #645 (G-C5-PR-TITLE) — noted only.

---

## Stubs

| path | role |
|---|---|
| `data/ops/nfl-t4673u-w8-eng-prep/stubs/T_C1_STDEV_MARKET_INVARIANCE.spec.py` | Item 1 asserts + mutations |
| `data/ops/nfl-t4673u-w8-eng-prep/stubs/T_C1_BUILDER_PIN.spec.py` | Item 2 |
| `data/ops/nfl-t4673u-w8-eng-prep/stubs/T_EPA_ASOF_CUTOFF.spec.py` | Item 3 |
| `data/ops/nfl-t4673u-w8-eng-prep/stubs/T_W8_MISSINGNESS.spec.py` | Item 4 |
| `data/ops/nfl-t4673u-w8-eng-prep/SHA256SUMS` | packet hashes |
| `data/ops/nfl-t4673u-w8-eng-prep/SHA8_TABLE.md` | sha8 index |

Stubs are `*.spec.py` so default pytest (`test_*.py`) does not collect them. They document contracts. They do not enable production paths.

---

Signed: Cursor engineering PREP · t4673u · 2026-10-29 · NFL NO-GO · CERT=0  
END
