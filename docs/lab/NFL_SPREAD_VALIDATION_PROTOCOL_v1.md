# NFL Spread Validation Protocol v1.0

**Status:** PRE-REGISTERED — awaiting CoS review/sign  
**Lab:** Kos Edge #3 Model Validation Lab  
**Protocol version:** `nfl-spread-validation-protocol-v1.0`  
**Registered:** 2026-09-04  
**Scope lock:** NFL spread only (home/away ATS). CBB excluded.  
**Machine twin (empty schema stub):** [`data/ops/lab/nfl-spread-validation-protocol-v1.schema.json`](../../data/ops/lab/nfl-spread-validation-protocol-v1.schema.json)

> **NO RESULTS IN THIS DOCUMENT.** This file pre-registers evaluation criteria
> before any outcome viewing, scorecard fill, or ATS/CLV computation. Amending
> cut points, min-N floors, or Green/Yellow/Red bars requires a **protocol
> version bump** (v1.1+), not a silent edit.

---

## 0. Lab OS intent (NFL-spread-first)

Model Validation Lab OS starts with **NFL spread** as the first validated
surface. Other sports/markets (CFB, CBB, totals, props, ML) are **out of scope
for v1.0 runs**. Adjacent CFB unused-year / calibrator design is prior art only
(§12); do not execute CFB holdouts under this protocol.

Lab outputs are **evidence reports** for CoS → Ryan. They do **not** flip live
PLAY / LEAN / PASS tags.

---

## 1. Scope

| In scope (v1.0)                                      | Out of scope                               |
| ---------------------------------------------------- | ------------------------------------------ |
| NFL regular-season + postseason **spread** ATS       | CBB / NBA / MLB / NHL / WNBA               |
| Home side and away side vs closing spread            | NFL totals, ML-only, player props, futures |
| KEI−market (or model−market) edge as discrepancy     | Live stake-tag remaps                      |
| Graded pillars → Subscriber Influence recommendation | Premium reasoning / narrative product work |

**Unit of analysis:** one game-side prediction stamped before kickoff, graded
against the **closing home spread** (ATS: cover / push / fail at −110 unit
sizing). Pushes are excluded from hit-rate denominators (standard NFL ATS).

**Edge definition (locked):**  
`edge_pts = kei_spread_home − market_spread_home`  
(or model fair when KEI absent — stamp which source was used). Absolute edge
`|edge_pts|` drives discrepancy buckets (§2). Side selection follows the sign
of edge (back the model side).

---

## 2. Discrepancy buckets (fixed cut points)

Changing any cut point requires **protocol v1.1+**. Do not retune after seeing
results.

| Bucket ID   | \|edge\| (points) | Label                       | Notes                                 |
| ----------- | ----------------- | --------------------------- | ------------------------------------- |
| `noise`     | `[0.0, 1.1)`      | Below historical LEAN floor | Research / null-edge                  |
| `lean_band` | `[1.1, 2.5)`      | LEAN-band (product sat)     | Aligns with enterprise LEAN window    |
| `play_low`  | `[2.5, 3.5)`      | PLAY band — low             | Inside `spread_play_v2_cap7`          |
| `play_mid`  | `[3.5, 5.0)`      | PLAY band — mid             | Inside `spread_play_v2_cap7`          |
| `play_high` | `[5.0, 7.0)`      | PLAY band — high            | Inside `spread_play_v2_cap7`          |
| `mega_edge` | `[7.0, ∞)`        | Cap7+ / research mega-edge  | Product doctrine: not PLAY in v2 cap7 |

**Aggregate slices (also pre-registered):**

| Slice ID           | Definition                                        |
| ------------------ | ------------------------------------------------- |
| `all_sides`        | All graded games with a finite edge               |
| `play_band_all`    | Union of `play_low` ∪ `play_mid` ∪ `play_high`    |
| `investable_proxy` | Same as `play_band_all` (Lab evidence proxy only) |

Cut points deliberately mirror product doctrine (`2.5 ≤ |edge| < 7.0`) so Lab
buckets are comparable to PLAY holdout prior art — without granting Lab
authority to change live tags.

---

## 3. Sample size (min N) and confidence intervals

| Level                         | min N                                                        | CI level                                    |
| ----------------------------- | ------------------------------------------------------------ | ------------------------------------------- |
| Overall (`all_sides`)         | 200                                                          | **95%** Wilson (or Agresti–Coull) for rates |
| Per discrepancy bucket        | 40                                                           | **95%** Wilson for rates                    |
| Regime slice (§5)             | 40                                                           | **95%** Wilson for rates                    |
| CLV movement sample (product) | 200 for GREEN on Market Edge Evidence; 40 soft segment floor | **95%**                                     |

If `n < min N` for a required slice: that slice grades **YELLOW** on Evidence
Quality (thin sample) and cannot alone carry a Green claim on the dependent
pillar. Do not pool post-hoc to clear min N.

**Breakeven ATS reference (locked):** `0.5238` (−110). Stretch band: `0.55`.

---

## 4. Grade pillars — primary + secondary metrics

Each pillar receives exactly one of: **GREEN** / **YELLOW** / **RED** /
**N/A—DATA GAP** (when a required input series is missing — never invent).

### 4.1 Predictive Quality

| Role      | Metric                                                                                                                                                  |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary   | Spread **MAE vs closing line**, graded **market-relative only** (model/KEI MAE ≤ market-implied benchmark MAE). No absolute-pt OR escape hatch in v1.0. |
| Secondary | Margin MAE vs final score differential (enterprise echo ≤9.5 is secondary, not a GREEN alternate); Brier on home cover probability (if WP published)    |
| Reporting | Bias (signed mean error) reported but not grade-primary; absolute spread-vs-close MAE reported but does not gate GREEN in v1.0                          |

### 4.2 Market Edge Evidence

| Role      | Metric                                                                                   |
| --------- | ---------------------------------------------------------------------------------------- |
| Primary   | ATS hit rate and −110 unit **ROI** on `play_band_all` (and per bucket with n≥40)         |
| Secondary | Movement **CLV+ rate** (§6); mean CLV move (points)                                      |
| Reporting | Full-slate ATS on `all_sides` reported for context; selective claim uses `play_band_all` |

### 4.3 Evidence Quality

| Role      | Metric                                                                                                                                   |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Primary   | Effective N (graded games); CLV movement coverage rate (`n_clv_move / n`)                                                                |
| Secondary | Regime stability (§5): share of regime slices that do not contradict the overall directional claim; OOS window integrity (no peek flags) |
| Reporting | Missing-odds / push / duplicate rates                                                                                                    |

---

## 5. Regime tests

Run each regime **only when field coverage ≥ 80%** of the graded slate for
that field; otherwise mark the regime **N/A—DATA GAP** (do not impute).

| Regime         | Levels (locked)                            | Data field / source expectation       | If missing                        |
| -------------- | ------------------------------------------ | ------------------------------------- | --------------------------------- |
| Home / Away    | `home_side`, `away_side`                   | Side backed by edge sign              | Always available                  |
| Favorite / Dog | `favorite` (`market_spread` side), `dog`   | Closing market spread sign            | Always when close exists          |
| Week bands     | `W1–W4`, `W5–W12`, `W13–W18`, `postseason` | NFL week number                       | Always when slate tagged          |
| Outdoor / Dome | `outdoor`, `dome`                          | Venue roof / stadium type on game row | **N/A—DATA GAP** if <80% coverage |
| Edge bucket    | §2 buckets                                 | Computed edge                         | Always when edge finite           |

Regime grades are **diagnostic**. A single thin regime RED does not auto-RED
Market Edge Evidence if overall `play_band_all` clears — but two or more
contradictory regime REDs with n≥40 each force Market Edge Evidence ≤ YELLOW
(stability fail under Evidence Quality secondary).

---

## 6. CLV definition + source

**Primary CLV methodology (locked):** `movement_only_n_snaps_ge_2`

| Field                    | Definition                                                                                                             |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Open                     | Earliest owned open snapshot for the game spread                                                                       |
| Close                    | Latest pre-kickoff owned close (or consensus close join)                                                               |
| Eligible movement sample | `open ≠ close` **and** `n_snaps ≥ 2`                                                                                   |
| CLV sign (model side)    | Positive when line moves toward the model-backed side from open→close                                                  |
| CLV+ rate                | Share of eligible games with positive CLV                                                                              |
| Expected data source     | Owned `odds_snapshots` / DB open–close densify (product path). Prefer owned OC before any Odds API historical densify. |

**Secondary (optional, labeled separately):** prediction-timestamp→close CLV
when a prediction `as_of` / board stamp exists. Report as
`clv_pred_ts_to_close`; do not mix into the primary movement sample.

**Hard rule:** If historical open/close odds are missing for a game or season
window → grade CLV metrics **N/A—DATA GAP**. Do **not** invent, backfill from
memory, or scrape unverified closes to fill gaps. Flat open=close rows stay in
`clv_*_all` reporting only; they are excluded from the product movement sample.

---

## 7. OOS / walk-forward definition (no peek)

| Window                         | Role                                                                                                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Primary unused holdout season  | Most recent completed NFL season with locked boards available at eval time (default target: **2025** if boards exist) — **not** used for any Lab knob search |
| Confirmatory window            | Immediately prior season(s): default **2024–2025** combined for CLV N                                                                                        |
| Walk-forward by season         | For each season S in `{2020…primary}`: metrics computed using only rules frozen before viewing S outcomes under this protocol                                |
| Selection era (if ever needed) | Must be declared in a **future protocol version** before use; v1.0 ships with **no selection search** — cut points are frozen in §2                          |

**No-peek rules:**

1. Protocol v1.0 criteria are frozen before loading outcome joins for Lab scoring.
2. Do not widen/narrow buckets after seeing ATS/CLV.
3. Do not drop regimes post-hoc to clear Green.
4. Any exploratory cut requires protocol v1.1+ and a new unused window.

---

## 8. Green / Yellow / Red criteria

**Honesty note:** **RED is a successful Lab outcome** when it correctly detects
failure or insufficient support. The Lab’s job is evidence integrity, not a
Green narrative. Shipping a truthful RED without flipping product tags is a
pass for the Lab process.

### 8.1 Predictive Quality

**GREEN gate choice (locked, CoS 2026-09-04):** **market-relative comparison only** for
spread-vs-close MAE. The former absolute OR (`≤ 13.0 pts`) is removed — too loose /
always-true. v1.0 does **not** use an absolute spread-MAE floor as an alternate OR
gate. A tight absolute (`≤ 4.0 pts vs close`) is reserved only as a possible **additional
AND conjunct** in a future protocol bump — not an escape hatch in v1.0.

| Grade        | Criteria (all must hold unless noted)                                                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GREEN        | Overall n≥200; model/KEI spread MAE ≤ market-implied benchmark MAE (**market-relative only** — no absolute OR); no catastrophic bias (\|mean signed error\| ≤ 2.0 pts on `all_sides`) |
| YELLOW       | n≥100 and primary MAE within 15% of market benchmark **or** margin MAE ≤ 10.5; else thin-sample caution                                                                               |
| RED          | n≥100 and model spread MAE worse than market by >15% **and** margin MAE > 10.5; or systematic bias \|mean error\| > 3.0 pts                                                           |
| N/A—DATA GAP | Closing lines or finals missing for ≥20% of intended slate                                                                                                                            |

_Margin MAE ≤ 9.5 (enterprise supervised-holdout echo) is **secondary** for Predictive
Quality — report it; it does not alone carry or substitute for the market-relative GREEN
gate. Absolute spread-vs-close MAE is reported for transparency only in v1.0._

### 8.2 Market Edge Evidence

| Grade        | Criteria                                                                                                                                                                                                                                                                                      |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GREEN        | `play_band_all` ATS ≥ 0.5238 with n≥60; movement CLV+ ≥ 0.55 with **n_clv_move ≥ 200**; −110 ROI > 0                                                                                                                                                                                          |
| YELLOW       | ATS ≥ 0.5238 with n≥60 but CLV+ fails floor **or** 40 ≤ n_clv_move < 200; **or** ATS clears with flat/weak CLV                                                                                                                                                                                |
| RED          | `play_band_all` ATS < 0.5238 at n≥60; **or** ROI < 0 at n≥60; **or** CLV+ < 0.50 at n_clv_move ≥ 100                                                                                                                                                                                          |
| N/A—DATA GAP | Outcomes missing; or CLV series absent when ATS alone would otherwise be claimed as product-ready — ATS may still be reported, but Market Edge Evidence cannot be GREEN without CLV or a pre-registered second unused year (mirrors CFB/NFL honesty: ATS-only never full Green for influence) |

Exceptional ATS with flat CLV stays **≤ YELLOW** (enterprise honesty rule).

### 8.3 Evidence Quality

| Grade        | Criteria                                                                                                                                                                |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GREEN        | Overall n≥200; CLV movement coverage ≥ 70% on `play_band_all`; ≤1 regime with n≥40 contradicts overall direction; OOS windows intact; schema/version stamps present     |
| YELLOW       | 100 ≤ n < 200 **or** CLV coverage 40–70% **or** one contradicting regime (n≥40) **or** soft CLV n (40–199)                                                              |
| RED          | n < 100 for claimed surface **or** CLV coverage < 40% when odds were expected **or** ≥2 contradicting regimes (n≥40) **or** peek / post-hoc protocol violation detected |
| N/A—DATA GAP | Cannot establish coverage denominators (broken inventory)                                                                                                               |

---

## 9. Subscriber Influence decision rules

Lab emits one of: **YES** / **LIMITED** / **NO** / **INSUFFICIENT EVIDENCE**.

This is a **recommendation to CoS → Ryan**, not an automatic product flip.

| Decision                  | Rule (locked)                                                                                                                                                          |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **YES**                   | Predictive Quality ≥ YELLOW; Market Edge Evidence = GREEN; Evidence Quality = GREEN                                                                                    |
| **LIMITED**               | Market Edge Evidence = GREEN or YELLOW; Evidence Quality ≥ YELLOW; no pillar RED that is process-integrity (peek). Scope claim to confirmatory window / PLAY-band only |
| **NO**                    | Market Edge Evidence = RED **or** Predictive Quality = RED at adequate n                                                                                               |
| **INSUFFICIENT EVIDENCE** | Any pillar = N/A—DATA GAP that blocks Market Edge Evidence; **or** Evidence Quality = RED for thin n; **or** CLV N/A—DATA GAP when Green would otherwise be claimed    |

**Hard lock:** Lab results never write LIVE PLAY / LEAN / PASS. CoS packages
evidence; Ryan decides any doctrine/tag change after a separate unused holdout
if product policy must move.

---

## 10. Comparators (when data allows)

When closing lines + model + KEI joins exist for the same games, report three
strategies side-by-side on identical OOS windows:

| Comparator ID         | Side rule                                                                                                                                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kosedge_alone`       | Bet model/KEI side when \|edge\| in `play_band_all`                                                                                                                                                                     |
| `market_alone`        | Null / home-favorite baseline at close (document exact rule: always home favorite when spread ≠ 0; pick'em excluded)                                                                                                    |
| `kosedge_plus_market` | Same as `kosedge_alone` but require agreement with a simple market-momentum filter: open→close move not strictly against the model side (eligible movement rows only; if CLV series N/A—DATA GAP, skip this comparator) |

Metrics per comparator: ATS, ROI (−110), n, CLV+ (when available). No blending
weight search in v1.0 — comparator is descriptive, not a retune license.

---

## 11. Pipeline stages (spec only)

Ordered stages for a future runner. **This PR does not implement or execute them.**

```text
1. prediction          → stamped model/KEI spread + as_of
2. timestamped market  → open + close (owned odds_snapshots)
3. outcome             → final score → ATS vs close
4. error               → signed spread error, margin error
5. calibration         → reliability / MAE / Brier aggregates
6. edge bucket         → map |edge| → §2 bucket IDs
7. CLV                 → movement sample or N/A—DATA GAP
8. regime              → §5 slices (or N/A—DATA GAP)
9. threshold evaluation→ apply §3–§8 bars (frozen protocol version)
10. grades             → Predictive / Market Edge / Evidence Quality
11. influence          → YES / LIMITED / NO / INSUFFICIENT EVIDENCE (§9)
```

Artifacts (future): empty-result-shaped JSON conforming to the twin schema
stub under `data/ops/lab/`. No filled scorecards in protocol PRs.

---

## 12. Prior art (cite — do not rebrand as Lab discovery)

The following already exist on `deploy-vercel`. Lab v1.0 **inherits** their
locked floors and honesty rules as prior art. Quoting them is citation, not a
new finding.

### 12.1 `docs/NFL_ENTERPRISE_GATES.md`

Already locks Green/Yellow/Red vocabulary; full-slate ATS floor ≥ 52.38%
(n≥200); CLV+ ≥ 55% with n≥200; PLAY-only unused holdout bars; supervised
holdout Brier/MAE floors; default PASS board posture; `spread_play_v2_cap7`
band `2.5 ≤ |edge| < 7.0`; LEAN band historically weak; product CLV uses
**movement sample** (open≠close, n_snaps≥2); props stake-off; factor freeze;
honesty: failed retunes must not promote; prefer owned OC densify before Odds
API gap pulls.

### 12.2 `data/ops/nfl-play-only-holdout.json` (+ `.md`)

Pre-registered PLAY-only unused holdout for policy `spread_play_v2_cap7`:
gates `ats_min=0.5238`, `ats_n_min=60`, `clv_pos_min=0.55`,
`clv_n_min_product=200`, `clv_n_min_segment=40`; methodology
`movement_only_n_snaps_ge_2`; primary unused season 2025; confirmatory
2024–2025; notes that 2020–22 clean-era CLV is weak — do not claim durability
from that era. Lab buckets and min-N floors intentionally align to these gates.

### 12.3 `apps/web/lib/nfl-spread-play-lock.ts` + `/NFL_SPREAD_PLAY_LOCKED.md`

Owner lock (Ryan Kos, 2026-09-03): spread PLAY only in `spread_play_v2_cap7`;
totals PLAY sat; prop PLAY sat; publish≡action after remap; do not hunt PLAY
or retune floors without a new unused holdout + explicit Ryan flip. **Lab must
not violate this lock** — evidence only.

### 12.4 CFB adjacent prior art (not executed here)

- `docs/CFB_KEI_CALIBRATOR_DESIGN.md` — PLAY unsat requires CLV **or** a
  second unused year; ATS-only never unsats PLAY; versioned guards; design-only
  posture.
- `data/ops/cfb-historical-calibration-20260805.md` (+ unused-year / spread
  tag-close holdout ops notes) — chronological calibration vs close, honest
  reconstruction limits, no invented odds.

Lab remains **NFL-spread-first**. Do not run CFB evaluations under protocol
v1.0.

### 12.5 Evaluator / policy code paths (reference)

- `scripts/nfl/play_only_holdout.py`, `scripts/nfl/evaluate_enterprise_gates.py`
- `services/model-service/src/services/nfl_enterprise_gates.py`
- `services/model-service/src/services/nfl_side_total_publish_policy.py`
- `apps/web/lib/nfl-publish-policy.ts`

These are product/gate infrastructure. Lab may later read their outputs as
inputs; this protocol PR adds **no** new evaluation runs.

---

## 13. Hard locks (Lab law)

1. **No live PLAY / LEAN / PASS flip** from Lab results. Report evidence only.
   CoS → Ryan decides any product change.
2. **No rebuild** of models, boards, or KEI packs unless a defect is proven
   **and** CoS gates the rebuild.
3. **No inventing missing historical odds.** Missing → **N/A—DATA GAP**.
4. **No p-hacking / post-hoc bucket changes.** Change criteria only via
   protocol version bump (v1.1+) with a fresh unused window.
5. **Premium reasoning not required** for this scaffold / protocol registration.
6. **RED = success** when it honestly detects failure (§8).

---

## 14. Amendment process

| Change type                                | Required action                        |
| ------------------------------------------ | -------------------------------------- |
| Typo / citation path fix                   | Patch on same version with CoS note    |
| Any numeric cut point, min N, or grade bar | New protocol version (v1.1+)           |
| Add sport/market (CFB, totals, …)          | New protocol doc (do not overload v1)  |
| Fill scorecard / run pipeline              | Separate PR **after** CoS sign of v1.0 |

**CoS sign line (blank until review):**

```text
CoS sign-off: ____________________  Date: __________  Protocol: v1.0
```

---

## 15. Explicit non-goals for this registration PR

- No holdout execution
- No ATS / ROI / CLV result tables from Lab runs
- No scorecard JSON filled with numbers
- No scripts that compute Lab grades yet
- No outcome-dataset analysis in this change set
