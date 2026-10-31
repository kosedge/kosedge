# CURSOR ENGINEERING RCA — t4577u v1

**RESEARCH_DIAGNOSTIC · CERT=0 · NFL NO-GO · Coming Soon ON · DRAFT findings only**

- Authority: DECISION_RYAN_t4577u (resume NFL modeling RCA). Structure: t4575u.
- Cursor owns **implementation defects + data/chronology + emit reproducibility**, independent of Alex’s predictive/model-design lane.
- Alex paper (handoffs 1.3–1.6 + exp E): `ALEX_PREDICTIVE_RCA_t4577u_v1.md` sha256 `8167ddd68f1272e755efab49f80ecfca74dbaac475d045d9c14a415e708c85b7` (CoS ACCEPT 8167ddd6). This document confirms or falsifies those handoffs with code-path evidence; it does **not** duplicate Alex’s encompassing/MSE paper.
- F2 PHI@WSH frozen. No merge / deploy / publish. No Odds API. No protected holdout (2024–25). No production scoring-equation change. No scale-factor curve-fit.

**This VM:** `DATABASE_URL` **UNSET**. Warehouse connectivity was not invented. All n=2992 numbers below were recomputed from the pinned PR #646 emit CSV + in-repo OOS scores (no DB).

---

## Status lock (unchanged)

NFL is not fireable. Shared historical result (IMV-reproduced; independently re-scored here) is that EPA and RECORD lose to the market on spread MAE for 2013–2023 n=2992. That fact is **not** the cause. This RCA separates **what the code actually does** from **why a better model would look different**.

---

## Independent re-score of the n=2992 panel

**SUPPORTED BY EVIDENCE.** Script: `research/nfl/t4577u_engineering_rca_diagnostics.py`. Sidecar: `research/nfl/t4577u_engineering_rca_numbers.json`.

| pin | sha256 |
|---|---|
| EPA WF features CSV (PR #646 tip `a027cc7d`) | `02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2` |
| OOS scores `historical_oos_games.csv` | `1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed` |
| Walk-forward games pin (export `82ffb211`) | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` |
| Join `(season, week, home, away)` | **2992 / 2992**, 0 unjoined |

Convention (same as Alex 88b3b7ce): `m = home − away`; `mm = −market_spread_home`; `pm_epa = −epa_trailing_spread_home`; `pm_rec = record_pred_margin_home`.

| signal | MAE | mkt MAE | gap | bias | slope mdl~mkt | SD ratio | slope act~mdl | mean pred / mkt / act |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| EPA margin | 10.687 | 9.962 | +0.725 | −0.949 | 0.304 | 0.442 | 1.584 | 1.06 / 2.03 / 2.01 |
| RECORD margin | 10.802 | 9.962 | +0.840 | −1.003 | 0.230 | 0.379 | 1.606 | 1.00 / 2.03 / 2.01 |

Matches Alex EPA WF v2 / R1 to reported precision. `apply_market_blend=false` and `simulations=4000` on all 2992 rows. `max|record_pred_margin_home + record_spread_home| = 0.0`.

Observed `|spread|` range on the emit (MC published): EPA max 7.89 / p95 5.50; RECORD max 7.91 / p95 5.19; **market max 27.0 / p95 13.0**.

---

## Alex → Cursor handoffs (t4577u)

### 1.3 rest_days hard-coded 7.0 — does `simulate_nfl_game` consume rest?

**Verdict: CONFIRMED placeholder in the WF emit. The simulate path DOES consume rest. Rest contribution is identically zero on n=2992 because both sides are forced to 7.0.**

| claim | label | evidence |
|---|---|---|
| Emit writes `rest_days_home=rest_days_away=7.0` on every game | **SUPPORTED BY EVIDENCE** | `scripts/nfl/emit_epa_wf_pbp_strict_asof_t4564u.py` (PR #646) L547–L548 hard-code; manifest `engine.rest_days: 7.0`. Re-score: all 2992 rows are 7.0 / 7.0 (Alex sidecar; confirmed in emit CSV). |
| `NflGameInputs` defaults rest to 7.0 | **SUPPORTED BY EVIDENCE** | `nfl_simulator.py` L98–L99 |
| `simulate_nfl_game` forwards rest into decompose | **SUPPORTED BY EVIDENCE** | `nfl_simulator.py` L536–L537 |
| Decompose uses rest for points | **SUPPORTED BY EVIDENCE** | `compute_nfl_projection_decomposition` `nfl_handicapping_framework.py` L299–L309: `rest_delta * 0.18` margin (cap ±2.0) and `−|rest_delta| * 0.12` total (cap ±1.2). L344–L351: short-rest flag if `rest_days < 6.0` → ±0.30 margin. |
| Equal 7/7 rest is a no-op | **SUPPORTED BY EVIDENCE** | Local decompose: 7 vs 7 → rest_margin 0.0, short_rest false, predicted_margin = HFA 1.05 only (equal indices). |
| Unequal rest would move the line | **SUPPORTED BY EVIDENCE** | Local decompose: home 4.0 vs away 7.0 → rest_margin **−0.54** + situational **−0.30** = **−0.84** vs the 7/7 book. The path is live; the emit never feeds it. |
| Calendar rest exists but is unused by WF emit | **SUPPORTED BY EVIDENCE** | `nfl_data.rest_days_from_schedule` L97–L110 is a **DOW heuristic** (Thu→4, Mon→6, else 7), not true days-since-last-game. Emit does not call it. **ABSENT:** any kickoff-to-kickoff rest in the n=2992 path. |

**Not an implementation bug inside `simulate_nfl_game`.** It is an **emit input defect**: rest is a consumed feature whose research values were replaced by a constant.

Do **not** implement Alex exp D from this seat.

---

### 1.4 ~12.5 pts per net EPA vs ~20.9 empirical — coded constant/prior?

**Verdict: There is no single `12.5` constant. The ~12.5 slope is the emergent product of two coded priors (`0.75` and `16.0`) plus the `(off/def − 1)` map and the ±0.25 / ±6.5 clamps. That is a coded prior, not a fitted β, and not “intended 20.9 then accidentally 12.5” in any comment we found.**

| claim | label | evidence |
|---|---|---|
| EPA→index is a coded linear map | **SUPPORTED BY EVIDENCE** | `efficiency_backbone.epa_to_strength_indices` L68–L86: `offense = clamp(1 + 0.75·off_epa + 0.18·Δpressure, 0.82, 1.22)`; `defense = clamp(1 + 0.90·(−def_epa_allowed) + 0.14·Δpressure, 0.82, 1.24)`. Same formula copied in `tasks._epa_to_strength_indices` and `historical_market_backtest._offense_defense_index`. |
| Index→points is a coded ratio × weight, then hard-capped | **SUPPORTED BY EVIDENCE** | `nfl_handicapping_framework.py` L280–L289: `off_def = clamp(off/max(0.75,opp_def) − 1, ±0.25)`; `base_margin = clamp((off_def_h − off_def_a)·16.0 + 0.35·spread_signal, ±6.5)`. Defaults L87–L91. Locked in `LOCKED_SCORING` (`nfl_regression_diagnose.py` L101–L109). |
| Product `0.75 × 16.0 = 12.0` | **SUPPORTED BY EVIDENCE** | Local decompose around 0 EPA (HFA-only 1.05): putting net EPA entirely on home offense yields **exactly 12.000 pts per unit net EPA**. Split off/def ≈ 12.6–13.0. Alex’s emit regression **12.46** sits on this line. **ABSENT:** any identifier or comment equal to 12.5 or 20.9. |
| ±6.5 cap + ±0.25 off_def clamp bind the tail | **SUPPORTED BY EVIDENCE** | Theoretical max \|efficiency + HFA\| = **7.55**. Elite EPA mismatch (`+0.25 / −0.15` vs `−0.15 / +0.20`) **hits both clamps** and returns 7.55. Emit `|spread|` max 7.89 (MC noise around that ceiling) vs market max 27. |
| 16-0 vs 0-16 RECORD also caps at 7.55 | **SUPPORTED BY EVIDENCE** | `team_strength_from_record` L80–L94 → indices 1.12/1.12 vs 0.90/0.92; raw efficiency 6.62 → clamp 6.5 + HFA 1.05. |
| “12.5 is an intended design target” | **HYPOTHESIS (unsupported in comments)** | No docstring states “we want ~12 pts per EPA.” Comments describe the 16.0 / 6.5 knobs as framework defaults; HFA 1.05 was trimmed after a 2023–25 ATS note (`nfl_handicapping_framework.py` L80–L82). Treating 12.5 as a fitted market scale would be the forbidden curve-fit. |

**Engineering read:** Alex’s 12.5 vs 20.9 is **not** a missing multiply-by-1.68 constant we should paste in. It is the **locked handicap core** doing what it is coded to do. Changing `0.75` / `16.0` / `6.5` is a **scoring-equation change** (forbidden in this PR). Any replacement β must be estimated inside a walk-forward generator on ≤2022 only (Alex exp A) — not by stretching eval preds.

---

### 1.5 Neutral-site games still get +home — is the flag ignored?

**Verdict: CONFIRMED. `NflGameInputs` has no `neutral_site` field. `compute_nfl_projection_decomposition` always adds static HFA +1.05. The flag is ABSENT, not mis-read.**

| claim | label | evidence |
|---|---|---|
| HFA is unconditional | **SUPPORTED BY EVIDENCE** | `nfl_handicapping_framework.py` L450–L455 and L782–L797: `home_field_advantage.margin_points` is always `priors.home_field_points` (default 1.05). Notes: “Static home-field prior in point space.” |
| Simulator input has no venue/neutral flag | **SUPPORTED BY EVIDENCE** | `NflGameInputs` (`nfl_simulator.py` L89–L172): **ABSENT** `neutral_site` / `location` / `venue`. Grep of `nfl_simulator.py` and `nfl_handicapping_framework.py` for `neutral`: **no matches**. |
| ESPN schedule parser *does* read `neutralSite` | **SUPPORTED BY EVIDENCE** | `nfl_data.fetch_nfl_schedule` L73 writes `neutral_site`. That field is **not** threaded into `NflGameInputs` or decompose. |
| n=55 Neutral in the emit still get +home | **SUPPORTED BY EVIDENCE** | Emit `nflverse_location`: home 2937 / Neutral 55. Week-22 Super Bowls (2021 CIN vs LAR, 2022 PHI vs KC, 2023 KC vs SF) are `location=Neutral` and still run the HFA term. 2022 SB RECORD decomp margin is **exactly 1.05** (equal records + HFA) on a neutral field. |
| Alex mean +0.68 EPA vs market −0.97 on n=55 | **SUPPORTED BY EVIDENCE** (Alex sidecar). Cause of the +0.68 (HFA plus residual rating) = **HYPOTHESIS** on the mix; cause “flag ignored” = **SUPPORTED** (there is no flag to honor). |

This is a real implementation defect. Magnitude on the pooled MAE is small (55/2992 × 1.05 ≈ 0.019 pts) and does **not** explain the +0.725 gap. It **does** explain why Super Bowl / London / Super Bowl-adjacent books are systematically home-tilted vs market.

Do **not** implement Alex exp B from this seat.

---

### 1.6 RECORD totals near-constant — emit defect vs design?

**Verdict: DESIGN of `team_strength_from_record`, correctly applied by the emit. Not a broken totals column.**

| claim | label | evidence |
|---|---|---|
| Same win% drives both O and D | **SUPPORTED BY EVIDENCE** | `nfl_data.team_strength_from_record` L91–L94: `offense = 0.90 + 0.22·win_pct`, `defense = 0.92 + 0.20·win_pct`. One scalar, two near-collinear indices. |
| Totals use `off_def_h + off_def_a` | **SUPPORTED BY EVIDENCE** | `nfl_handicapping_framework.py` L290–L297. When O and D both rise with win%, the home and away `off_def` terms **cancel**. 16-0 vs 0-16 total delta = **+0.22** pts; 10-3 vs 3-10 = **−0.08**. |
| RECORD export does not pass EPA fields | **SUPPORTED BY EVIDENCE** | t4422u `export_walkforward_pergame_2013_2023.py` builds `NflGameInputs` from record indices only → `_build_totals_adjustments` returns `applied=False` (`nfl_simulator.py` L366–L372). No pace / EPA-interaction totals channel. |
| Observed SD matches the design | **SUPPORTED BY EVIDENCE** | RECORD total SD **0.270** vs market **4.355** (ratio **0.062**). Mean 45.23 vs prior 45.3. Week-1 0-0 vs 0-0 book is 44.84 because 0.90/0.92 is **below** 1.0, not because a column was dropped. |
| “Emit forgot to write a totals model” | **FALSIFIED as a wiring bug** | The totals column is populated (MC `total_mean`). It is structurally incapable of moving. This is Alex 3.7 / exp C (model design), not a missing assignment. |

Related foot-gun (not Alex 1.6, but same function): `tasks.py` L1565–L1566 comments that a 0-0 record is “exactly 1.0”. **False.** `0-0` has a `-` so it does **not** take the `(1.0, 1.0)` early return; `games = max(1, 0+0) = 1`, `win_pct = 0` → **0.90 / 0.92**. Empty/`None` is 1.0; week-1 0-0 is not. **SUPPORTED BY EVIDENCE.**

---

### Exp E — walk-forward as-of audit (kickoff < target; season boundary)

**Verdict: The n=2992 EPA emit is week-ordinal strict-as-of, not kickoff-timestamp as-of. Same-week leakage is refused. Prior-season weeks are used at week 1 (honest in time, no offseason regression). The warehouse SoT path is a different, leaky contract. Full kickoff-level proof is not closed on this VM.**

#### What the preferred emit actually does

| rule | label | evidence |
|---|---|---|
| Rolling uses `(season, week) < (target_season, target_week)` | **SUPPORTED BY EVIDENCE** | `emit_epa_wf_pbp_strict_asof_t4564u.py` `_rolling_before` L387–L401; docstring L10–L14; manifest `asof_policy`. Last **5** weekly means, unweighted. |
| PBP grain = team-week `AVG(epa)` on `play_type ∈ {pass, run}` | **SUPPORTED BY EVIDENCE** | `_load_pbp_week_rows` L276–L376. Seasons loaded **2012–2023** so 2013 W1 has a prior year. |
| Same-week Thursday ↛ Sunday | **SUPPORTED BY EVIDENCE** (policy) | Current week is excluded entirely. Conservative vs `kickoff < target`. |
| Kickoff-timestamp comparison | **ABSENT** | `_rolling_before` never reads `kickoff_utc` / gameday. **HYPOTHESIS** that NFL week structure makes week-grain ≡ kickoff-honest across weeks (TNF week N+1 is after MNF week N). Not proven for 2020 COVID reshuffles or any week-label error. |
| Week 1 window always length 5, spans prior season | **SUPPORTED BY EVIDENCE** | Rolling CSV sha256 `1b07654ea500535ff445e0f3c20acc26a6c3006857951562755e406adff52479`: `games_in_window_5 = 5` on 2013 W1 (32 teams) and every other W1 row sampled; `asof_policy=strict_prior_weeks_unweighted_weekly_mean_last5`. Matches Alex 2.4. Time-honest (2012 games are before 2013 W1 kickoff). **No** offseason regression / roster-change shrink. |
| Franchise continuity on EPA, not on RECORD | **SUPPORTED BY EVIDENCE** | Emit rolls on `canonicalize_team` (`STL→LAR`, `SD→LAC`, `OAK→LV`; `nfl_canonical_teams.py` L48–L58). RECORD W-L keys raw OOS codes (STL stays STL). Small-n cross-relocation mismatch. |

#### Warehouse path (NOT the n=2992 EPA eval, but it *is* production / old backtest SoT)

| rule | label | evidence |
|---|---|---|
| Rolling SQL includes **CURRENT ROW** | **SUPPORTED BY EVIDENCE** | `data_platform_nfl/ingest.py` `materialize_matchup_features_from_usage` L1278–L1297: `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW`. |
| Matchup join is same `(season, week, team)` as the game | **SUPPORTED BY EVIDENCE** | same file L1470–L1474. A week-W prediction can include week-W situational EPA. |
| `historical_market_backtest.py` uses that join | **SUPPORTED BY EVIDENCE** | L222–L225. That script is the source of “raw model MAE 9.63 vs market 9.92, so blend 0.30” (`nfl-market-blend-backtest-2026-08-19.json`, n=3562, **includes 2024–25**). |
| Those “we beat the market” numbers are not the honest n=2992 eval | **SUPPORTED BY EVIDENCE** | Honest strict-as-of EPA MAE is **10.687 vs 9.962**. The 9.63 figure used a leaky week-aligned warehouse join + extra matchup_diff / totals channels (`historical_market_backtest.py` L300–L305) + 2024–25. **Do not treat 9.63 as a fireable EPA win.** |
| Production priors `week <= as_of_week` | **SUPPORTED BY EVIDENCE** | `tasks._week_cap_nullable_predicate` L773; `_fetch_rolling_feature_latest_rows` L780–L830. Inherits warehouse CURRENT ROW semantics when those rows exist. |

#### Season-boundary handling (exp E remainder)

- **Honest:** prior-season team-weeks are before week-1 kickoff.
- **Not a shrink / roster model:** last-5 of year Y-1 is used at full weight at Y week 1 (Alex 2.4). That is a **model-design** weakness, not leakage.
- **Bye weeks:** weekly rows exist only when the team has PBP that week; `_rolling_before` takes last 5 non-null weeks → effectively last 5 **games**, not last 5 calendar weeks. **SUPPORTED BY EVIDENCE** (filter `off_epa is not None` then `recs[-5:]`).
- **Kickoff < target assertion:** **not executed** on this VM (would require PBP play timestamps or nflverse schedules joined to every contributing week). Policy string is week-ordinal, not kickoff. **HYPOTHESIS** remaining: no COVID / flex week-label inversion. Recommended as the actual exp E script (see §E), not as a claimed pass.

Alex 2.5 “no leakage signature because EPA never beats the market” is **not** a leakage proof. Underperformance can coexist with leakage. The week-grain emit looks conservative intra-week; warehouse CURRENT ROW is the leaky contract.

---

## A) Confirmed defects + evidence

Each item is an **implementation or data-contract** defect (or a locked prior that the emit cannot escape). Not a request to retune on the eval.

### A1. Locked efficiency→points transform compresses spreads (shared EPA+RECORD layer)

- **What:** `off_def` clamp ±0.25 × `margin_weight` 16.0, then `max_margin_points` 6.5, then +HFA 1.05. Theoretical ceiling **±7.55** (plus MC noise ~0.2). Market p95 is 13; market max 27.
- **Where:** `nfl_handicapping_framework.py` L280–L289, L450–L455, L782–L797; `LOCKED_SCORING`; framework `nfl-handicap-core-v3.1`.
- **Repro:** `PYTHONPATH=services/model-service python3 research/nfl/t4577u_engineering_rca_diagnostics.py --emit-csv <02f6b2e2 csv> --oos-csv data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv`
- **Numbers:** slope 0.304 / 0.230; max \|model spread\| 7.89 / 7.91; RECORD decomp hits the 7.55 cap on **59** games; **637** games are exactly HFA-only (1.05).
- **Label:** **SUPPORTED BY EVIDENCE** as the mechanism of *compression*. That this is “wrong” vs “deliberate shrinkage of a weak signal” is Alex’s design question (3.1–3.5), not an off-by-sign bug.

### A2. HFA is a static +1.05 and is applied on neutral sites

- **What:** Always-on +1.05. Neutral flag ABSENT. Sample actual home margin **+2.01**, market **+2.03** → bias −0.95 / −1.00. 55 Neutral games still get +home. Super Bowl 2022 decomp = 1.05 on Neutral.
- **Where:** `nfl_handicapping_framework.py` L82, L93–L95, L450–L455; `NflGameInputs` has no neutral field.
- **Label:** **SUPPORTED BY EVIDENCE.** Alex 3.8: bias is ~4% of MSE — real, secondary. Neutral gate is still a defect.

### A3. WF emit rest is a constant; simulate would use real rest if given

- See handoff 1.3. **SUPPORTED BY EVIDENCE.**

### A4. RECORD week-1 (and any 0-0 / equal-record) book is HFA-only

- **What:** All 175 week-1 games have `record_decomp_pred_margin_home = 1.05` uniquely. 0-0 maps to 0.90/0.92 for **every** team, not 1.0.
- **Where:** `team_strength_from_record` L80–L94; emit/export use entering W-L before the game (PIT: update after scores — t4422u export).
- **Label:** **SUPPORTED BY EVIDENCE.** This is why RECORD week 1–4 MAE gap is worse than EPA’s (+0.912 vs +0.525 in Alex 88b3b7ce).

### A5. RECORD totals cannot move (design, correctly wired)

- See handoff 1.6. **SUPPORTED BY EVIDENCE.**

### A6. Warehouse rolling is same-week leaky; that path produced the false “EPA beats market” backtest

- See exp E warehouse table. **SUPPORTED BY EVIDENCE.** Explains Alex 88b3b7ce §8: 2023 PARTIAL EPA gap −0.215 (warehouse / `record_vs_epa_backtest_records.json`) did **not** reproduce on strict-as-of PBP (+0.699). RECORD 2023 did reproduce (+0.974 vs +1.004).

### A7. Production `simulate_nfl_game` on `deploy-vercel` always blends when a market line is passed; `apply_market_blend` is ABSENT

- **Where:** `nfl_simulator.py` L604–L628 (no flag). t4422u branch added `apply_market_blend=False` so the sealed `games.csv` could score cover/over without blending means.
- **Repro risk:** Re-running the t4422u export on **this** tip while passing `market_spread_home` would **not** reproduce the unblended n=2992 contract.
- **Label:** **SUPPORTED BY EVIDENCE.** The n=2992 eval itself is unblended (`apply_market_blend=false` in the CSV). Production published lines are not comparable to that eval (Alex 1.7).

### A8. EPA eval strength ≠ production `package_to_strength_indices`

- **What:** Emit uses bare `epa_to_strength_indices` on pass/run EPA + pressure. Live `_load_team_strength_priors` → `package_to_strength_indices` adds success / explosiveness / RZ / ST / splits (`efficiency_backbone.py` L35–L42, L262+).
- **Label:** **SUPPORTED BY EVIDENCE** as a methodology mismatch. Not a sign bug. n=2992 EPA is **not** the Edge Board book.

### A9. EPA emit double-uses raw EPA on **totals** (not the primary spread path)

- **What:** Indices already carry EPA. Emit also sets `home_off_epa_5g` / `away_off_epa_5g` / def allowed (`emit` L549–L552) → `_build_matchup_adjustments` total_signal (L283–L291) and `_build_totals_adjustments` `offense_defense_epa_interaction_5g` (L382–L393), both added again in `base_total_points` (L290–L294). `spread_signal` from `matchup_diff_*` is 0 (diffs not passed).
- **Label:** **SUPPORTED BY EVIDENCE** as extra totals channels. Impact on spread MAE: **HYPOTHESIS** (small). Impact on EPA total SD 2.51 vs RECORD 0.27: **SUPPORTED** that EPA totals can move and RECORD cannot.

### A10. MC means are the published spread; 4000 sims do not systematically bias the mean

- **What:** `spread_home = −mean(home_score − away_score)` (`nfl_simulator.py` L596–L652). RECORD MC vs decomp: mean(MC − decomp) = **−0.011**, mean |diff| = **0.176**, max 0.80. SE of a 9.8-pt Gaussian margin at n=4000 is ~0.22. Consistent with sampling noise, not a biased estimator.
- **Score floors:** `max(7.5, expected_home)` / `max(7.0, expected_away)` (L582–L583; decompose L815–L817) can inflate totals if a side would go below the floor. Rare at ~22 PPG.
- **Label:** **SUPPORTED BY EVIDENCE** that n_replicates is **not** the cause of the MAE gap. W8’s n=40 is a **different** live-ops issue (CoS W8 report), not this historical panel.

### A11. Sign conventions on the n=2992 emit are internally consistent

- **SUPPORTED BY EVIDENCE.** `spread_home` negative = home favored; `record_pred_margin_home = −record_spread_home` (identity 0.0); `pm_epa = −epa_trailing_spread_home` aligns with `pm_rec`. nflverse `spread_line` in `historical_market_backtest.py` is the **opposite** convention (positive = home favored) — documented at L20–L25. OOS `actual_spread_home` is `away − home` (`HISTORICAL_OOS_DIAGNOSTIC.md` L36). Scoring that mixes those columns without a flip is a foot-gun; **this** re-score used `home_score − away_score` and reproduced Alex. Alex 1.1–1.2 **CONFIRMED**.

---

## B) Unproven hypotheses

1. **HYPOTHESIS:** Kickoff-level leakage exists in 2020 (or any week-label inversion) despite week-ordinal `<` policy. Exp E script not run against play timestamps.
2. **HYPOTHESIS:** Intra-week conservative as-of (Sunday cannot see Thursday) *hurts* MAE vs a true kickoff-as-of (information loss, not leakage).
3. **HYPOTHESIS:** STL/SD/OAK EPA franchise merge vs RECORD raw codes adds measurable slope error (small n).
4. **HYPOTHESIS:** EPA totals double-count (`A9`) moves `epa_trailing_total` enough to matter for total MAE (+0.325 gap). Not isolated here.
5. **HYPOTHESIS:** Production `package_to_strength_indices` extras would change n=2992 EPA MAE if replayed (A8). Not run.
6. **HYPOTHESIS:** Missing injury / QB / weather / travel (Alex 2.3, 3.4) explain the >7-pt disagreement bucket. Engineering confirms those inputs are **ABSENT** from the emit (`injury_overlay` / `ifb_overlay` / `personnel_overlay` / `market_blend_applied` all False 2992/2992). Causal share is Alex’s lane.
7. **HYPOTHESIS:** HFA 1.05 was over-trimmed because the 2023–25 ATS note used blended or leaky books (`nfl_handicapping_framework.py` L80–L82). Not re-fit here (would be a scoring change).
8. **HYPOTHESIS:** Opponent-adjusted ratings (Alex exp A) would raise encompassing `c` above 0. Engineering confirms **ABSENT** opponent adjustment / SOS on the emit (`_rolling_before` is raw team-week EPA). Not implemented.

---

## C) Data chronology / leakage findings

| path | as-of contract | used for n=2992 EPA? | leakage? |
|---|---|---|---|
| PR #646 PBP emit | `(season,week) < target`, last 5 weekly means, 2012 loaded for 2013 W1 | **YES** (preferred) | Same-week **refused**. Kickoff-timestamp **ABSENT**. Week 1 = prior season (time-honest, no shrink). |
| Warehouse `nfl_dp_team_rolling_features_weekly` | `ROWS … CURRENT ROW` + join at game week | **NO** (DATABASE_URL unset; 2013–22 not in default remat) | **YES — same-week EPA can enter the prediction.** |
| `historical_market_backtest.py` | warehouse join | NO (different n=3562, through 2025) | **YES** + holdout years in the blend sweep. |
| RECORD W-L export (t4422u) | same-season W-L updated **after** the game | YES (RECORD columns) | **NO** for the game being predicted. Week 1 = 0-0. |
| Production `_load_team_strength_priors` | `week <= as_of_week` on warehouse rows | NO (not this eval) | Inherits warehouse CURRENT ROW if those rows exist. |

**DATABASE_URL gap (this VM and PR #646):** unset. Railway MCP exposes the **name** `DATABASE_URL` on model-service `e0c54f94-…` / Postgres `4d1abc93-…` but **values are hidden**. Local `127.0.0.1:5432` refused. Warehouse 2013–22 rematerialize was not performed and is **not invented**. Filed previously: PR #646 `DATABASE_URL_BLOCKER.md`.

**POST included:** 95 games with week>18; 3 week-22 Super Bowls. n=2992 is REG+POST, not REG-only.

**MS-9 / market:** emit `market_line_source` is the walk-forward export’s nflverse close proxy, not owned Odds-API close. **No Odds calls were made.** True-close / CLV remains deferred (Alex 2.2).

---

## D) Ranked engineering fixes

Effort is technical (files / tests / deps), not calendar. **None of these are implemented in this PR.** None stretch eval preds by `1/0.304`.

| rank | fix | why | effort | deps | risk |
|---|---|---|---|---|---|
| 1 | **Neutral-site HFA gate** (honor `neutral_site` / `nflverse_location==Neutral` → HFA 0) | A2 / handoff 1.5. Small MAE, large integrity. | Small: thread one bool through `NflGameInputs` → decompose; tests for SB/London. | Schedule location already on the emit. | Scoring-equation adjacent (HFA application). Needs a research flag, not a silent prod flip. |
| 2 | **WF emit: real rest from schedule dates** (replace 7.0/7.0) | A3 / 1.3. Simulate already consumes rest. | Small–med: kickoff diffs or `rest_days_from_schedule` (DOW heuristic is weaker than true last-game rest). | nflverse schedule dates already in emit columns. | `rest_days_from_schedule` is DOW-only; prefer actual last-game date. Do not ship as a “fix” without ≤2022 WF. |
| 3 | **Warehouse rolling: `ROWS BETWEEN n PRECEDING AND 1 PRECEDING`** (or as-of join to prior week) | A6. Stops same-week leakage in production/backtest SoT. | Med: rematerialize + contract tests; do **not** use default `season=` week-22 entrypoint (`nfl-spine-safe-rematerialize`). | `DATABASE_URL` authorized. 2013–22 situational may still be missing. | Changes live priors. Research remat only until IMV. |
| 4 | **Port `apply_market_blend` onto `deploy-vercel` simulator** (default True for prod, False for research export) | A7. Makes the n=2992 path reproducible on the production tip. | Small: flag + tests. | t4422u already has the patch. | Must default to today’s blend behavior so prod numbers do not jump. |
| 5 | **Document / test 0-0 → 0.90/0.92** (fix the `tasks.py` comment; decide whether cold-start should be 1.0) | A4. Comment is false. | Tiny if comment-only; small if week-1 maps to 1.0/1.0 (spreads unchanged when *all* teams are 0-0; totals move 44.84→45.3). | None. | Changing the 0-0 map is a scoring input change. |
| 6 | **Do not** raise `margin_weight` / drop the 6.5 cap / multiply preds by ~1.68 | Forbidden curve-fit; Alex 3.3 shows encompassing `c≈0` — more scale without more information loses to market *worse* in the disagreement tail. | — | — | Explicitly out of scope. |

**Not ranked as eng defects:** opponent-adjusted ratings, per-season HFA, QB/weather features, totals pace model (Alex A/B/D/C). Those are model-design experiments. Cursor does not own them as “bugs.”

---

## E) Proposed development-data experiments (no holdout, no scale-fit)

Fit / decide on **≤2022** only; one look at **2023** (n=285). Never 2024–25. No Odds. No convenient `k = 1/slope` stretch.

**This PR does not implement Alex experiments A/B/D.**

### E0. Exp E (Cursor-owned, recommended next) — kickoff-as-of audit

- **Assert:** every team-week that enters `_rolling_before` for game G has `max(kickoff of games in that team-week) < kickoff(G)`.
- **Also assert:** no play with `play.game_id == G.game_id` enters G’s window (already implied by week `<`).
- **Season boundary:** list, for every week-1 row, `{first, last}` contributing season-weeks (expect Y-1 last 5 team-weeks; already `games_in_window_5=5`).
- **COVID / flex:** flag any pair where week ordinal and calendar order disagree.
- **Stop:** if any kickoff inversion is found, block promotion of A–D until the window is rebuilt.
- **Expected MAE change:** none if clean; integrity only.
- **Deps:** nflverse schedules + PBP (public); **no** warehouse required. Script can live under `research/nfl/`.

### E1. Rest ablation (uses 1.3; not full exp D)

- Replace 7.0/7.0 with true days-since-last-game from the same nflverse schedule already joined. Leave scoring knobs (`0.18` / `0.30`) untouched.
- ≤2022 walk-forward; 2023 one-look. Metric: encompassing `c` and MAE gap vs market. Drop if `c` CI includes 0.

### E2. Neutral HFA = 0 (uses 1.5; not full exp B)

- Zero the HFA term when `nflverse_location == Neutral` (55 games). Do **not** re-estimate HFA on 2013–23.
- 2023 bias and Neutral-slice mean vs market. Stop if Neutral mean does not move toward market (Alex: market −0.97).

### E3. Leakage contrast (warehouse CURRENT ROW vs strict week) on **≤2022 only** if `DATABASE_URL` is later authorized

- Same games, two feature clocks, same locked equation. Quantifies how much of the 9.63-vs-10.69 “EPA win” was same-week information.
- **Do not** run if it requires 2024–25 or Odds.

### E4. Forbidden (listed so it is not “forgotten”)

- Multiply `epa_trailing_spread_home` by ≈3.3 or fit `a + b·pred` on the eval.
- Touch 2024–25.
- Call Odds API.
- Merge / remat-to-prod / flip Coming Soon.

---

## Reproducibility of the n=2992 emit path

| step | pin | notes |
|---|---|---|
| RECORD baseline | PR #638 `cursor/t4422u-walkforward-pergame-export-f36b` tip `82ffb211…`; `export_walkforward_pergame_2013_2023.py`; `games.csv` sha256 `4fe1cdd7…` | Unblended; 4000 sims; seed namespace `t4422u-unblended-record`. Script **not** on `deploy-vercel`. Requires the branch’s `apply_market_blend=False`. |
| EPA fill | PR #646 `cursor/epa-wf-feature-emit-5bcd` tip `a027cc7d`; `scripts/nfl/emit_epa_wf_pbp_strict_asof_t4564u.py`; CSV sha256 `02f6b2e2…`; manifest `3073dd96…` | Offline nflverse PBP; **no** DATABASE_URL. Joins `(season,week,game_id)` order-identical to `games.csv`. |
| Fallback | PR #644 — feature CSVs only; **not** the n=2992 sim emit | Do not use for this RCA. |
| This RCA re-score | `research/nfl/t4577u_engineering_rca_diagnostics.py` | No DB, no Odds, seasons ≤2023. |

**This branch (`deploy-vercel` tip `bfc89f57` at branch cut) cannot regenerate `games.csv` by itself** (export script + blend flag live on PR #638). It **can** re-score a copy of the pinned CSV. Independent challenge: `git show origin/cursor/epa-wf-feature-emit-5bcd:…/epa_wf_features_2013_2023.csv` and run the diagnostic.

---

## What this RCA is not

- Not a GREEN, edge, or CERT claim.
- Not Alex’s predictive paper. Encompassing `c≈0`, MSE split, and exp A/B/D design live there.
- Not a production scoring change and not a merge candidate for model math.
- Not a warehouse rematerialize (DATABASE_URL unset).

---

## IMV challenge surface

Every **SUPPORTED BY EVIDENCE** row names a file + function + line (or a sha256 + join count). The diagnostic script re-creates the n=2992 table without secrets. The remaining **HYPOTHESIS** rows are listed in §B; the one Cursor should run next is **exp E (kickoff-as-of)**, still research-only.
