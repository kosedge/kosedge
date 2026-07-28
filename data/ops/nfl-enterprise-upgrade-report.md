# NFL Enterprise Upgrade Report (COMPLETE + PLAY holdout)

Generated: 2026-07-28T21:05:00Z  
Branch: `nfl-kav-sharpen`  
DB: `127.0.0.1:5432/kosedge` (promoted restore warehouse)

## Executive verdict

| Claim | Status |
| --- | --- |
| KAV owned efficiency + schema v3 retrain | **DONE** |
| Full 2025 KAV-wired board re-sim | **DONE** (285/285 scored; 1693 model rows 2020–25) |
| Owned open/close dense 2020–2025 | **DONE** (parallel densify; do not re-burn) |
| Selective PLAY publish (PASS default) | **DONE** |
| ATS/CLV go/no-go gate infrastructure | **DONE** |
| PLAY-only unused holdout (2025) | **DONE — YELLOW** (ATS clears; CLV short) |
| Betting-product ready (full slate) | **NO — RED** |
| Selective PLAY ready | **NO — false** |
| Honest model score (now) | **7.1 / 10** |

---

## 1) What was done

### Pillar 1 — KAV v3 retrain + 2025 re-sim + holdout

| Item | Detail |
| --- | --- |
| Supervised schema | **v3**, 41 features incl. `diff_kav_net_5g` |
| Active fit | train **2992** / chronological holdout **570** |
| Holdout metrics | Brier **0.148**, margin MAE **7.48**, total MAE **9.20** → **GREEN** |
| 2025 re-sim | Dual resume+reverse batch + playoff gapfill (conf/SB under season_year=2026) |
| Coverage | **285/285** scored 2025 schedule games with fresh KAV projections |
| Blend retune | **Not promoted** (keep market blend 0.30) |
| Leakage | week−1 KAV only |

Artifacts: `nfl-kav-supervised-retrain-v3.json`, `nfl-kav-holdout-report.md`, `nfl-kav-resim-summary.json`, `nfl-kav-resim-playoff-gapfill.json`, `nfl-kav-grading-after.json`

### Pillar 2 — Owned OC densify (parallel; not re-run here)

| Metric | Before | After |
| --- | ---: | ---: |
| Schedule OC 2020–2025 | partial | **1693/1693** |
| CLV spread n | 159 | **601** (densify workstream cited 545 mid-flight) |
| CLV total n | 117 | **374** (densify cited 309 mid-flight) |
| Credits | — | **6,742** (~2.992M remaining) |

Report: `nfl-oc-densify-2020-2023-report.md`

### Pillar 3 — Selective publish

| Layer | Path |
| --- | --- |
| Python | `services/model-service/src/services/nfl_side_total_publish_policy.py` |
| API | `/nfl/fair-lines` → `publish_tag_*`, `stake_eligible_*` |
| Web | `apps/web/lib/nfl-publish-policy.ts` + `EdgeBoard.tsx` |
| Rules | PASS default; spread PLAY ≥2.5 (LEAN **off**); total PLAY only **[2.5, 3.0)**; RED product gate → force PASS |
| Props | `PLAY_STAKE_ELIGIBLE=False` unchanged |

### Pillar 4 — ATS/CLV enterprise gates

| Item | Path |
| --- | --- |
| Engine | `nfl_enterprise_gates.py` |
| Ops | `scripts/nfl/evaluate_enterprise_gates.py` |
| Docs | `docs/NFL_ENTERPRISE_GATES.md` |
| Tests | `tests/test_nfl_enterprise_gates.py` — **6 passed** |
| Latest | `nfl-enterprise-gates-latest.{json,md}` → **RED / not ready** |

---

## 2) BEFORE → AFTER metrics

Sources: `nfl-kav-grading-before.json` → `nfl-kav-grading-after.json` (full densify + full KAV re-sim).

| Metric | BEFORE | AFTER | Δ |
| --- | ---: | ---: | ---: |
| Model spread MAE | 9.613 | **9.528** | −0.085 |
| Model total MAE | 10.123 | **10.109** | −0.014 |
| Market spread MAE | 9.778 | 9.776 | — |
| Market total MAE | 10.300 | 10.296 | — |
| ML Brier | 0.200 | **0.197** | −0.003 |
| ATS hit | 0.493 | 0.499 | +0.006 |
| CLV spread n | 159 | **601** | +442 |
| CLV spread +rate | 0.660 | 0.508 | diluted (honest) |
| CLV spread avg | +2.02 | +1.03 | — |
| CLV total n | 117 | **374** | +257 |
| CLV total +rate | 0.633 | 0.527 | diluted (honest) |
| Model rows graded | 1693 | **1693** | full |

**Supervised holdout (v3):** Brier 0.148 · margin MAE 7.48 · total MAE 9.20 · n=570 · **GREEN**

**Interpretation:** Model **beats market close MAE** on spread and total after KAV re-sim. Full-slate ATS still below −110 (~52.38%). CLV sample is hundreds+; ~50% +rate is the honest densified history.

---

## 3) Gate status (betting-product claim)

| Check | Status |
| --- | --- |
| ATS vs −110 | **RED** (0.499 < 0.5238) |
| CLV spread sample | **RED** (n=601 OK, +rate 0.508 < 0.55) |
| MAE vs market close | **GREEN** |
| Supervised holdout | **GREEN** |
| Owned OC coverage | **GREEN** |
| Props stake policy | **GREEN** (stake-off) |
| **Overall / betting-product ready** | **RED / false** |

Do **not** market as a paid every-game betting card. Ship PASS-default board; selective PLAY only where segment evidence clears.

---

## 4) PLAY-only holdout (2025, pre-registered)

See `nfl-play-only-holdout.json` and `nfl-path-to-95-report.md`.

| Slice | n | ATS | CLV n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Spread PLAY (≥2.5) | 206 | 0.762 | 105 | 0.533 | YELLOW |
| Total PLAY [2.5,3.0) | 26 | 0.731 | 14 | 0.214 | RED |
| GREEN shrink segments | — | — | — | — | **none** |

---

## 5) Honest model score: **7.1 / 10**

| Score | Meaning |
| ---: | --- |
| 10 | Institutional Vegas-competitive every-game |
| 7 | Chargeable **selective** edge |
| 5.5 | Prior baseline |

**7.1** = prior 6.8 + PLAY-only holdout + selective ATS evidence. Cap below subscription GREEN until CLV n≥200 @ ≥55% on the PLAY universe. Do **not** claim 9.5 or 60%.

---

## 6) Gaps to 9.5 (prioritized)

1. Grow PLAY-tagged CLV to n≥200 with +rate ≥55% (live 2026 + owned OC; no densify re-burn).  
2. Calibrate edge magnitude (mean PLAY |edge| ~7 pts is too wide).  
3. Live 2026 paper → stake confirmation under locked thresholds.  
4. Speed market-sim (cache supervised fit + calibration).  
5. Special-teams KAV / inactives only if leakage-safe + holdout-positive.  
6. Props remain research-only until dedicated holdout.  
7. Prod warehouse promote + migration 041 + active v3 fit.

---

## 7) Needs from user

1. **Prod DB promote** if Railway still points at empty slim `kosedge`.  
2. **Do not re-densify** 2020–23 OC (~3M credits left for live).  
3. Keep `NFL_PRODUCT_GATE_STATUS` conservative until PLAY CLV clears.  
4. Continue capturing open/close into `odds_snapshots` through 2026.

---

## Key artifacts

- `data/ops/nfl-enterprise-upgrade-report.md` (this file)  
- `data/ops/nfl-kav-enterprise-next-report.json`  
- `data/ops/nfl-kav-grading-before.json` / `nfl-kav-grading-after.json`  
- `data/ops/nfl-kav-supervised-retrain-v3.json`  
- `data/ops/nfl-enterprise-gates-latest.{json,md}`  
- `data/ops/nfl-oc-densify-2020-2023-report.md`  
- `data/ops/nfl-kav-resim-summary.json`  
- `docs/NFL_ENTERPRISE_GATES.md`
