# CODEX_CHALLENGE — t4643u WS-A ENG CONTRACT v1

Lane: **Codex / independent challenge** (Ryan DECISION **098da1dd** · WS-E P1)
Not the implementer. No repairs. No merge / deploy / Odds / F2 / CERT.
Does **not** self-grade `PASS_ENG_CONTRACT` — IMV grades that.

| pin | value |
|---|---|
| Challenged tip | `ab7d977d68196ac97e3f13da8357b2edc40d6c84` · #645 DRAFT `cursor/w8-full-slate-engine-5bcd` |
| Binding criteria | IMV **062197c0** (re-hashed MATCH on tip) |
| Prod-identity packet | WS-D **2ce577a6** (RO; Odds / SHA identity) |
| Sealed consume proof | **7c2d9625** / **0be23ede** · completeness **675e1cf7** |
| Path under proof | `scripts/nfl/run_w8_research_forecast_t4564u.py` → `_simulate_one` → `simulate_nfl_game` |
| Oracle script | `services/model-service/tests/test_nfl_w8_forecast_consumption_contracts_t4643u.py` |
| Codex re-hash of packet | see `SHA256SUMS` in this directory (tip packet MATCH) |
| Verdict of this paper | **CHALLENGE_FILED** · **NOT** `PASS_ENG_CONTRACT` · **NOT** `FAIL_ENG_CONTRACT` |

Hard locks honored: NFL NO-GO · CERT=0 · F2 frozen · Coming Soon ON · #648 untouched (WS-A tip delta 70303058..ab7d977d is packet + one test file only).

Independent C1 re-run (seed 4643, 1200 sims) used only to challenge oracles. No new slate emit. No Odds HTTP.

---

## What the sealed packet already does well (not a pass)

These are **not** a Codex grade. They are facts so IMV does not treat this paper as a redo of WS-A discovery.

- C0 families are named. Warehouse is **GAP** in the matrix / contract (not labeled CONSUMED there).
- C3 CLOSED-pack sha256s MATCH on disk: depth `550e1a8d…` · injury `0c29ceea…` · EPA `cb1fe8c5…` · schedule `d88ae734…`.
- G3 current restore artifacts flag `w8_official_injury_report` + `injury_as_of_week8` 14/14; injury pack `w8_official_report=MISSING`, week=7, n=153.
- C6b is explicit DEFER + Needs-CLEAR for season pack rewrite.
- C7 paper non-claims are clean (no MAE / CERT / invent-W8 / merge as eng PASS).
- `CODE_PATH_MAP.md` already names the injury mean no-op **and** stdev leakage (`:64`, `:93`).
- W8 research script does not import Odds and does not `FROM nfl_dp_*` in its own text.
- Cursor does not self-grade `PASS_ENG_CONTRACT`.

The challenge is that several Ryan failure modes are **named in prose and then left untested**, or **tested on a bypass that cannot catch them**.

---

## Gaps found (index)

Severity: **BLOCKING** = would RETURN / FAIL a C0–C7 gate if IMV applies the written criterion strictly · **HIGH** · **MEDIUM** · **LOW** · **NOTE**.

| id | gap | Ryan mode | severity | Cursor already deferred? |
|---|---|---|---|---|
| G-C1-STDEV | C1-INJ perturbation moves **spread** via ungated `error_regime`; oracle only checks means | silent fallback · incomplete tests | **BLOCKING** (C1 wrong-component) | Named in map (`:64`, `:93`); **not** in C1 must-not-move / oracle |
| G-C1-BYPASS | C1 fixtures never execute SoT → builder → `NflGameInputs` | incomplete tests · stale inputs | **HIGH** (C1/C3) | No — C1 claimed as hashed SoT oracles |
| G-TIME-EPA | No `week<=7` cap; live `_download`; season EPA written into `*_epa_5g` | time leakage · stale grain | **HIGH** (C2/C3) | Not deferred as an oracle |
| G-INVENT-W8 | Three writers of W8 official / `as_of_week`; two can invent PRESENT or drop the flag | invent W8 · silent fallback | **HIGH** (C2/G3) | `T-G3-NO-INVENT` covers flags, **not** these branches |
| G-C7-VACUOUS | Odds test is substring `"False"`; no host allowlist; WS-D paid beat/worker unaddressed | unintentional paid Odds | **HIGH** (C7 / Ryan P1) | Paper non-claim only |
| G-C2-EPA-PRIOR | Missing-strength test injects `{}`; does not prove builder refuses 2025 prior | silent fallback · stale inputs | **MEDIUM** (C2) | Forbidden in prose; not executed |
| G-C1-EPA-PARTIAL | C1-EPA moves `offense_index` only; live path also wires `*_epa_5g` totals overlay | incomplete tests | **MEDIUM** (C1) | Not named |
| G-C6-ROLLING | Season already SELECTs warehouse rolling when a session exists; C6 test pins the 2025 file only | C6 SoT · duplicate impl · wire-because-available | **MEDIUM** (C6) | Pack rewrite deferred; **rolling SELECT is already live** |
| G-G1-GREP | G1 test greps one file; completeness auditor can PASS warehouse without `nfl_dp_*` SELECT | warehouse CLOSED-as-passed · silent fallback | **MEDIUM** (C0/C5) | Probe called “separate”; emit still records `blockers_closed` |
| G-C5-PR-TITLE | #645 title + body table still “all 4 checks CLOSED” including warehouse | CLOSED labeled complete | **MEDIUM** (C5) | Matrix says GAP; title not repaired |
| G-VINTAGE-COPY | Injury + EPA pack `as_of` copied from depth snapshot | stale inputs · C3 pin integrity | **MEDIUM** (C3) | Not deferred |
| G-LIVE-DOWNLOAD | Emit always refreshes nflverse; C3 hashes not enforced at run | stale / drift | **MEDIUM** (C3) | Not deferred |
| G-DUP-INJURY | Four injury week/SoT implementations that can disagree | duplicate implementations | **MEDIUM** | Map names two engines; not the four writers |
| G-DUP-SIM | Ad-hoc HTTP / `resolve_adhoc_simulation_strength` is a third `simulate_nfl_game` SoT | duplicate implementations | **MEDIUM** | Named in map; no oracle |
| G-CAL-SILENT | `apply_linear_totals_calibration=True` not in consumption matrix | silent fallback | **LOW** | Not named as a family |
| G-C6-ART | W8 game artifacts do not flag season W1 / 2025 conflict | C6 | **LOW** | Paper DEFER only |
| G-C2-AWAY | Restore oracle requires `injury_as_of_week8` not `_away` | incomplete tests | **LOW** | Partial |
| G-TICKET-ID | Builder still `TICKET=t4605u` / decision `e65b9c77` | identity drift | **LOW** | Not in C7 |
| G-COS-HASH | IMV authority lists COS_ORDER `f26f2808`; tip copy is `1114c1d2` | provenance | **NOTE** | Different short order filed |
| G-R1-TEST | Confidence mean-effect test already green | can be misread as current consume | **NOTE** | Explicitly labeled repair target |

No gap below asserts MAE, market beat, CERT, fireable, publish, F2, Coming Soon OFF, or that W8 official rows were invented on the sealed restore.

---

## 1. Stale inputs

### G-LIVE-DOWNLOAD — emit is not pinned to C3 hashes
**Severity:** MEDIUM · **Deferred?** no

`main()` always downloads current nflverse releases and refuses a local cache:

```791:794:scripts/nfl/run_w8_research_forecast_t4564u.py
    for name, url in NFLVERSE.items():
        dest = cache / name
        # t4605u restore: always refresh public nflverse (do not reuse stale cache).
        _download(url, dest, log)
```

C3 pins (`550e1a8d…` / `0c29ceea…` / `cb1fe8c5…`) are **post-hoc hashes of a prior materialize**, not inputs the builder checks before `_simulate_one`. A Wednesday re-run can consume a different parquet than the sealed packs while still writing files named `…_w7.json` / `…_w8.json`.

**Recommended test:** builder must refuse to sim (or flag `input_sha_mismatch`) unless parquet/pack sha256 equals the C3 pin. Fixture: swap one byte of the EPA pack → SystemExit, no silent continue.

### G-VINTAGE-COPY — injury / EPA `as_of` is the depth clock
**Severity:** MEDIUM · **Deferred?** no

```687:715:scripts/nfl/run_w8_research_forecast_t4564u.py
        "as_of": depth_as_of,
        ...
        "as_of": depth_as_of,
        "method": "play_weighted_w1_w7_passing_plus_rushing_epa",
```

Sealed injury + EPA packs both carry `as_of=2026-10-28T06:01:45Z` — the depth snapshot timestamp — not an injury-report clock or an EPA week-through clock. C3 “as_of 2026-10-28” for those families is therefore a **copied depth vintage**. Completeness `inseason_efficiency_current` treats `as_of[:10] >= 2026-09-10` as current (`audit_w8_input_completeness_t4605u.py:335-341`), so a copied clock can close the family even if team-week rows are older.

**Recommended test:** injury pack `as_of` must come from injury parquet `dt` / report date; EPA `as_of` from max team-week date. Assert they are allowed to differ from depth.

### G-C2-EPA-PRIOR — “no silent 2025 prior” is not executed
**Severity:** MEDIUM · **Deferred?** forbidden in prose only

`test_c2_epa_missing_refuses_to_sim` passes `strength={}` into `_simulate_one` (`test_nfl_w8_forecast_consumption_contracts_t4643u.py:229-243`). That proves the **sim gate**, not that `_build_current_strength` (`run_w8…:249-310`) refuses `nfl_team_efficiency_backbone_2026.json` (`prior_season=2025`, as_of 2026-08-08, sha256 `4cd45f85…`). A one-line fallback onto the packaged prior would keep this test green.

**Recommended test:** run `_build_current_strength` on an empty / week-max<7 frame and assert SystemExit `MISSING current strength` **and** that the 2025 pack file is never opened.

### G-C1-EPA-PARTIAL — consumed EPA family is only half-oracled
**Severity:** MEDIUM · **Deferred?** no

Live builder writes season play-weighted EPA into `home_off_epa_5g` / `away_off_epa_5g` / def-allowed (`run_w8…:433-436`). Those fields drive `_build_totals_adjustments` (`nfl_simulator.py:345-393`) even when offense indices are unchanged. C1 fixtures omit every `*_epa_5g` field (`fixtures/C1_base.json`, `C1_epa_home_boost.json`). The hashed C1-EPA oracle therefore does not move the totals overlay the emit actually uses.

**Recommended test:** C1 fixture pair that perturbs only `home_off_epa_5g` (or the builder’s `off_epa_per_play`) and asserts the declared totals component moves; offense_index pair remains the index oracle.

---

## 2. Time leakage

### G-TIME-EPA — no week cap; 5g name is a lie
**Severity:** HIGH · **Deferred?** no

`_build_current_strength` sums **every** week present in the parquet (`run_w8…:249-310`). The only gate is `team_df["week"].max() < 7` → exit (`:814-815`). There is no `week <= 7` filter. Source string is hardcoded `nflverse_stats_team_week_2026_w1_w7_play_weighted` (`:307`) even if week 8+ rows exist. Those values are then stored as `*_epa_5g` (`:433-436`) — season-to-date (or worse, in-progress W8) treated as a 5-game rolling feature.

TNF 2026-W08-CAR@GB kicks `2026-10-30T00:15:00Z`. The sealed emit (`2026-10-28T13:45:41Z`) is pre-kickoff. The **next** `_download` after that kickoff can leak a played W8 box into a “W1–W7” strength labeled current. `_g18_artifact` blocks post-kickoff **forecast_ts** (`:505-509`) but does not block post-kickoff **EPA rows** for remaining games.

**Recommended test:**
1. Strength builder fixture with week=8 team-week rows → must exclude them (or refuse) and must not label `w1_w7`.
2. Assert `*_epa_5g` is either unset or renamed/flagged `season_to_date_w1_w7` — not silent 5g.

W8 kickoffs themselves are not leaked on the sealed restore (first game 2026-10-30). This is a **re-run / future-download** hole, not a claim that the Oct 28 slate used post-game EPA.

---

## 3. Silent fallbacks

### G-C1-STDEV — declared “means unchanged”; observed spread move
**Severity:** BLOCKING for C1 · **Deferred?** named, not oracled

IMV C1: FAIL if “wrong component moves.”

Contract C1-INJ-FIELD (`C0_C7_CONTRACT.md:39`) declares component = `diagnostics.injury_nowcast.home_impact` identity and **means unchanged**. `must_not_move` = `injuries_depth.margin_points`. Test (`test_…py:112-124`) checks those and stops.

Engine: `injury_conf` defaults 0 → mean term is zero (`nfl_handicapping_framework.py:311-341`). `error_regime` averages **raw** impact without confidence (`:837-861`) and feeds `compute_error_regime_uncertainty` (`nfl_second_order_factors.py:120`, `* 0.15`). Totals-overlay stdev **is** confidence-gated (`nfl_simulator.py:438-447`); error-regime stdev is **not**.

Codex re-ran the hashed fixtures (seed 4643, 1200 sims):

| | spread_home | home_wp | mean_home | injuries_depth.margin | error_regime.stdev_widen |
|---|---|---|---|---|---|
| `C1_base` | −0.14 | 0.4892 | 23.175 | 0.0 | 0.2182 |
| `C1_inj_impact_only` | **−0.13** | 0.4892 | 23.175 | 0.0 | **0.2387** |

Means match the oracle. **Spread moved.** Markets are not equal. Cursor already wrote this in `CODE_PATH_MAP.md:64` (“StDev leakage … can change MC spread/WP slightly”) and `:93` (overlay labeled CONSUMED; mean silent zero). That is an exact miss they left **erratum-eligible in prose** and **green in C1**.

**Recommended test (do not implement here):**
- C1-INJ must assert `markets.spread_home` / `total_mean` / `home_win_prob` **and** `error_regime.stdev_widen` either (a) unchanged, or (b) listed as a declared consumed side-effect with a hashed delta.
- If (b), C5 cannot call the overlay CONSUMED-into-means; it is CONSUMED-into-uncertainty.

### G-INVENT-W8 — invent paths exist; C2 never calls them
**Severity:** HIGH · **Deferred?** `T-G3-NO-INVENT` does not cover these branches

Three writers, three rules:

1. `_injury_impacts` hardcodes `w8_official_report=MISSING` (`run_w8…:355`) **but** if a team has no designations, `as_of_week = max(week)` (`:325`). Empty W8 stubs → `as_of_week=8` → `_simulate_one` does **not** append `injury_as_of_week8` because `as_of_week == WEEK` (`:465-468`).
2. `_materialize_current_packs` sets `"w8_official_report": "PRESENT" if latest_week >= WEEK else "MISSING"` (`:691`). Any nflverse week-8 designation row flips the pack to PRESENT. That is inventing a W8 official book from nflverse designations.
3. Completeness auditor: `"PRESENT" if inj_week == week else "MISSING"` (`audit_w8_input_completeness_t4605u.py:270-272`).

C2-G3 (`test_…py:156-174`) injects fixture dicts with `as_of_week` 7 and 6. **`_injury_impacts` is never called.** Sealed restore oracle reads prior artifacts, not the pack writer.

Sealed restore today is honest (week 7, MISSING). The **code paths that would invent** are untested.

**Recommended tests:**
- `_injury_impacts` on a frame with week-8 empty stubs only → `as_of_week != 8` **and** `injury_as_of_week8` still flagged.
- `_injury_impacts` + pack writer on a frame with week-8 designated rows → must **not** write `w8_official_report=PRESENT` (nflverse ≠ official Wednesday book) and must keep G3 flags.
- Completeness evidence must not say PRESENT unless a separately pinned official-W8 SoT exists (none today).

### G-G1-GREP — warehouse can be “passed” without SELECT
**Severity:** MEDIUM · **Deferred?** “probe stays separate” — emit still consumes the verdict

`test_c3_g1_no_warehouse_select_in_forecast_path` (`test_…py:148-153`) only asserts the W8 script text has no `FROM nfl_dp_` and contains `Does not read DATABASE_URL`. The emit then imports `audit_week_inputs` (`run_w8…:999-1009`) and records `blockers_closed`.

Completeness warehouse close (`audit_…py:288-313`):

```python
warehouse_ok = (
    probe_ok
    or (bool(db["DATABASE_URL_present"]) and bool(db["local_5432_accepting"]))
    or railway_ok          # railway whoami exit=0
    or (status_ok and run_ok and probe_ok)
)
```

`DATABASE_URL` + listening `:5432`, or a successful `railway whoami`, marks `current_weekly_depth_db` **ok=True** with **no** `SELECT` of `nfl_dp_depth_chart_weekly`. Tests set `DATABASE_URL` (`test_…py:16`). That is CLOSED-access / CLOSED-complete without consume — the exact miss class 7c2d9625 sealed.

WS-A matrix correctly labels G1 **GAP**. #645 title and the four-blocker table still say warehouse **CLOSED** (see G-C5-PR-TITLE).

**Recommended test:** completeness `current_weekly_depth_db.ok` is true only given a hashed RO probe with `SET TRANSACTION READ ONLY` + table counts; whoami / URL+port alone must not pass. G1 grep must include imported auditors.

### G-CAL-SILENT
**Severity:** LOW · **Deferred?** no

`_simulate_one` sets `apply_linear_totals_calibration=True` (`run_w8…:446`). Default in `simulate_nfl_game` is also True (`nfl_simulator.py:520`). Not a consumption-matrix family. Totals can move without an EPA/rest/injury flag.

**Recommended test:** C1 base with calibration on vs off; if delta ≠ 0, name the overlay and pin the calibration source sha.

---

## 4. Duplicate implementations

### G-DUP-INJURY
**Severity:** MEDIUM · **Deferred?** map names game vs season; not the four writers

| writer | week rule | W8 official |
|---|---|---|
| `_injury_impacts` (`:313-372`) | per-team last designated, else `max(week)` | always MISSING |
| `_materialize_current_packs` (`:656-691`) | slate-wide last designated week | PRESENT if `latest_week >= 8` |
| `audit_week_inputs` (`:270-272`) | pack `week` field | PRESENT if `week==8` |
| `fetch_nfl_injury_nowcast` → `_fetch_injury_rows_for_week` (`nfl_injury_nowcast.py:444-518`) | `FROM nfl_dp_injuries` `week=None` (latest per player) | warehouse max_week=3 |

W8 research emit uses (1). Pack + completeness use (2)/(3) and can disagree with (1) on BUF/JAX/LAC/WAS (week 6) / CIN (week 5) vs a week-7 pack. (4) is the production nowcast SELECT — a **second injury SoT** that would regress to W3 if wired. Not called from the W8 script today; no test forbids a future import.

**Recommended test:** one fixture parquet → assert `_injury_impacts` as_of weeks, pack `week` / `w8_official_report`, and completeness evidence are a single documented function of that parquet. Ban `FROM nfl_dp_injuries` on the research emit import graph.

### G-DUP-SIM
**Severity:** MEDIUM · **Deferred?** named in `CODE_PATH_MAP.md:31`

Third caller: `routes/nfl.py` + `resolve_adhoc_simulation_strength` (`nfl_epa_authority.py:166+`) with `overlays_off` and packaged-EPA. Same `simulate_nfl_game`, different SoT. C1/C2 never compare the two. A reader of “W8 research path is authoritative for this emit” can still hit the ad-hoc path in prod (API is Offline per 2ce577a6; worker is Online).

**Recommended test:** snapshot ad-hoc strength source vs research `_build_current_strength` for one frozen game; assert they differ **and** that the W8 artifact flags the ad-hoc path unused.

### G-C6-ROLLING — season already wires warehouse strength when available
**Severity:** MEDIUM · **Deferred?** C6b defers **pack rewrite**; rolling SELECT is existing code

```19:24:services/model-service/src/services/nfl_season_engine/loaders.py
1. DB ``nfl_dp_team_rolling_features_weekly`` via ``_load_team_strength_priors``
2. Packaged ``nfl_team_efficiency_backbone_<season>.json``
```

`load_universe_from_db` calls `_load_team_strength_priors(session, …)` at `loaders.py:1455` **before** packaged fill. `test_c6_g4_season_still_binds_w1_and_2025_prior` (`test_…py:263-272`) only checks the W1 depth file week/as_of, the 2025 prior file, and the string `ignored stale DB depth`. It does **not** fail if a live session prefers warehouse rolling over research W1–W7 EPA. That is already “wire because available” on the season engine — the C3 hard stop the warehouse paper applies to G1.

WAREHOUSE_AUTHORITY correctly says rolling was **not probed**. C6 test still treats the 2025 pack as the season strength SoT.

**Recommended test:** with a fake session that returns rolling rows, assert season notes include `STALE_FALLBACK` / `Needs-CLEAR` vs research EPA sha `cb1fe8c5…`, and that this ticket did not add a new SELECT. IMV C6 (a) or (b) — (b) is chosen, but (b) requires a **flag in the running loader**, not only a markdown DEFER.

---

## 5. Unintentional paid Odds

### G-C7-VACUOUS
**Severity:** HIGH for the Ryan P1 Odds bar · **Deferred?** C7 paper non-claim

```275:279:services/model-service/tests/test_nfl_w8_forecast_consumption_contracts_t4643u.py
def test_c7_no_odds_no_market_blend_on_w8_path() -> None:
    text = W8_SCRIPT.read_text(encoding="utf-8")
    assert "apply_market_blend" in text
    assert "False" in text
```

`"False"` appears in any Python file. This cannot catch:
- `from src.services.odds_api import …` added next to nflverse `_download`
- `simulate_nfl_game(..., market_spread_home=fetched)` — blend applies whenever the line is not None (`nfl_simulator.py:604-624`)
- Celery `pull_odds_snapshot` on the **same** worker image (WS-D 2ce577a6 §4: beat `pull-odds-season-cadence` + `pull-odds-3am-refresh` are **intentional paid** and **Online**; GAP-1 45–63 credits/h unexplained; Vercel request-time Odds **UNVERIFIED**)

W8 script today: `odds_api=False` on artifacts, no Odds import, urllib only to nflverse GitHub. That is the current text, not a regression lock. Completeness `_railway_cli_status` can invoke `railway run` against production Postgres (`audit_…py:83-98`) — not Odds, but it is a live prod side-effect on a “research emit.”

WS-A C7 (“this packet does not assert Odds as eng PASS”) is a **non-claim**, not a proof that running the draft cannot spend.

**Recommended tests / locks (Needs CLEAR before any of them hit a network):**
- Import graph of `run_w8_research_forecast_t4564u.py` excludes `odds_api`, `the-odds-api`, `ODDS_API_KEY`.
- urllib host allowlist = nflverse GitHub releases.
- Every C1/C2 sim (already in-process) asserts `market_blend.spread_applied is False` and `total_applied is False` (Codex observed this on the C1 pair; the oracle does not).
- WS-D beat/worker paid path remains **out of this ticket** and must stay flagged `Needs-CLEAR` — do not “fix” it from WS-A.

Codex did **not** call Odds.

---

## 6. Unsupported causal claims

None of the WS-A packet claims MAE / market beat / CERT as eng PASS. C7 paper is clean.

Residual over-claims (not predictive; still unsupported as **identity**):

- PR title “all 4 input checks CLOSED” (warehouse access ≠ forecast consume). Matrix contradicts the title; title remains.
- Injury overlay **CONSUMED** while means are a silent zero and stdev is an undeclared mover (G-C1-STDEV). Cursor named the inconsistency; the verdict enum still says CONSUMED.
- EPA source string `w1_w7` / field name `*_epa_5g` (G-TIME-EPA) is a grain claim the builder does not enforce.
- `CODE_PATH_MAP` “Team-sim volume = EPA” is a true description of current wiring, not a causal “EPA should be volume.” Fine if IMV reads it as FACT about code.

No Alex Q1–Q4 causal promotion in this packet. Out of scope for this challenge except: do not let C1-INJ “means unchanged” be cited as “injury does not affect the forecast.”

---

## 7. Incomplete tests (other)

### G-C1-BYPASS
**Severity:** HIGH · **Deferred?** no

C1 helpers (`test_…py:58-61`) build `NflGameInputs(**fx["inputs"])` and call `simulate_nfl_game`. They never run `_load_canonical_week`, `_rest_days`, `_build_current_strength`, `_injury_impacts`, `_depth_meta`, or the C3 packs. C3 pins can rot relative to the builder and C1 stays green.

**Recommended:** at least one C1 path that starts from the pinned packs / a hashed parquet slice and ends at the declared component.

### G-C2-AWAY
**Severity:** LOW

`C2_sealed_restore_oracle.json` `required_missing_inputs` lists `injury_as_of_week8` but not `injury_as_of_week8_away`. Current 14/14 happen to include both. The oracle would still pass if away flags dropped.

### G-R1-TEST
**Severity:** NOTE

`test_c1_injury_with_confidence_moves_means_repair_target` (`test_…py:127-139`) already passes because the engine honors injected confidence. It is labeled a repair target. It must not be counted as C1 evidence that today’s builder consumes injury into means (it does not set confidence: `run_w8…:426-432`).

C4 “still wired” (`test_…py:253-260`) is a string search for field names in the script, not a C1 re-run after a repair.

---

## 8. Warehouse CLOSED labeled CONSUMED

**Matrix / contract:** G1 = GAP. C0 PASS condition “warehouse not labeled CONSUMED” holds **inside** `C0_C7_CONTRACT.md` / `INPUT_CONSUMPTION_MATRIX.md` / `.json`.

**Outside the matrix:**

### G-C5-PR-TITLE
**Severity:** MEDIUM · **Deferred?** matrix only

#645 title (unchanged on tip `ab7d977d`):  
`DRAFT t4615u CERT=0: W8 pipeline restore — all 4 input checks CLOSED (do not merge)`

PR body four-blocker table: `current_weekly_depth_db | CLOSED`, then later “G1 warehouse | GAP (CLOSED ≠ CONSUMED)”. IMV C5: provenance/READ+GATE cannot be summarized as CONSUMED in the **PR body**. They did not write CONSUMED. They did write CLOSED for the warehouse family on the same page as the consume table. That is the 675e1cf7 / 7c2d9625 confusion class.

**Recommended:** retitle / rewrite the four-blocker table to GAP for warehouse before CoS FORWARD. Not a code repair.

G-G1-GREP above is the **runtime** form of the same miss.

Season loaders already `SELECT` `nfl_dp_*` (depth skipped if W1 pack present; rolling preferred). G1 “refuse SELECT” is scoped to the W8 script text only.

---

## 9. Inventing W8 injury

Sealed restore: **not invented**. Pack week=7, `w8_official_report=MISSING`, 153 designated, sha256 MATCH `0c29ceea…`. 14/14 flags present.

Invent risk is **forward** (G-INVENT-W8): pack writer PRESENT iff `latest_week >= 8`; completeness PRESENT iff pack week==8; `_injury_impacts` can set `as_of_week=8` on empty stubs and drop the flag. C2 does not execute those functions.

Do **not** “fix” by writing week-8 official rows. Recommended tests are refuse/flag only.

---

## 10. C6 season vs game SoT

Contract chooses IMV C6**(b)** DEFER + Needs-CLEAR. That is an allowed handling **if** code does not claim one SoT.

Facts on tip:

- Season depth exclusive W1 pack `21f202ec…` as_of 2026-08-13 (`loaders.py:7-17,1653-1682`) vs research W8 `550e1a8d…`. Test asserts the W1 file still exists. Good for “not rewritten.”
- Season strength: rolling DB **first**, else 2025 prior `4cd45f85…` (`loaders.py:19-25,1455`). Test does not see rolling (G-C6-ROLLING).
- Season injuries: `packaged_injury_paths` / not W7 nflverse. Warehouse injuries max_week=3 — do-not-wire is paper only.
- W8 game artifacts do not carry a `season_sot_conflict` flag (G-C6-ART). Dual-book exists in-repo; this emit does not call `simulate_one_season_path` (`CODE_PATH_MAP.md:29`).

IMV C6 FAIL if “contract claims one SoT while code still binds a conflicting pack without a flag.” The contract does **not** claim one SoT. The **season loader docstring** still calls W1 “authoritative SoT” (`loaders.py:7-10`) with no STALE_FALLBACK flag unless DB depth was skipped. That is a code claim, not a WS-A paper claim.

**Recommended:** loader note `STALE_FALLBACK vs research W8 pack 550e1a8d / EPA cb1fe8c5` when packaged W1 / 2025 prior / rolling DB are used. Needs-CLEAR to change SoT. No pack rewrite on this ticket.

---

## Recommended test / repair additions (Codex does not implement)

Priority if CoS forwards to a repair draft (still #645, still no merge/Odds):

1. **C1-INJ** — declare or forbid `error_regime.stdev_widen` + market equality (G-C1-STDEV). BLOCKING for C1.
2. **C2-G3** — execute `_injury_impacts` + pack writer on empty-W8-stub and designated-W8 frames (G-INVENT-W8).
3. **C3 pin enforce** — emit refuses unless parquet/pack sha256 MATCH; no silent re-download drift (G-LIVE-DOWNLOAD).
4. **EPA week cap** — `week<=7` (or refuse) + stop writing season EPA into `*_epa_5g` without a flag (G-TIME-EPA).
5. **C7 Odds** — import graph + urllib allowlist + `market_blend.*_applied is False` (G-C7-VACUOUS). Do not touch beat/worker.
6. **C6 flag** — season loader STALE_FALLBACK when rolling/W1/2025 prior bind; test the rolling-preferred branch (G-C6-ROLLING).
7. **G1** — completeness cannot PASS warehouse on whoami/URL+port; retitle #645 (G-G1-GREP, G-C5-PR-TITLE).
8. **C1 builder path** — one hashed pack/parquet → component oracle (G-C1-BYPASS, G-C1-EPA-PARTIAL).
9. **C2 EPA** — builder empty frame ≠ 2025 prior (G-C2-EPA-PRIOR).
10. **Identity** — emit ticket/decision sha8 = t4643u / 098da1dd or an explicit “builder still t4605u” flag (G-TICKET-ID).

No item above is a warehouse-into-prod wire. No item invents W8 official rows. No item is a predictive experiment.

---

## Non-actions (this lane)

- Did not implement repairs.
- Did not merge, deploy, restart, set-variables, or spend Odds.
- Did not reopen G34 / Exp D-R / #648.
- Did not emit a new W8 slate.
- Did not grade `PASS_ENG_CONTRACT` or `FAIL_ENG_CONTRACT`.
- Did not treat WS-D 2ce577a6 as a deploy order.

Signed: Codex independent challenge · t4643u WS-E · tip `ab7d977d` · 2026-10-28
END
