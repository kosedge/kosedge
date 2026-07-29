# NFL Narrow Second-Order Path — Holdout Report

Generated: 2026-07-29T07:20:00Z  
Branch: `nfl-second-order-edge`  
Ablation artifact: `data/ops/nfl-second-order-ablation.{json,md}`  
Policy: **`spread_play_v2_cap7`**

## Honest verdict

| Claim | Status |
| --- | --- |
| Ablation completed (additive Δ on stored v3 boards) | **YES** |
| `selective_play_ready` | **true** (locked v2 PLAY claim on stored boards; unchanged) |
| `betting_product_ready` | **false** (full-slate still RED) |
| Honest model score | **7.6 / 10** (provisional 7.7 **revoked** — E failed; B unmaterializable; A regresses) |

---

## Warehouse prep

| Step | Result |
| --- | --- |
| Migrations 043 + 044 | Applied on local `127.0.0.1:5432/kosedge` |
| Coach thin materializer | **1710** weekly rows (2023–25, SQL aggregate) |
| Personnel materializer | **0 rows** — public nflverse PBP parquet has **no** `offense_personnel` |
| Info velocity inputs | Injuries 2023–25 available; WoW velocity computed at grade time (1694 keys) |
| Visual Crossing | Key **absent** locally (`.env` / `infra/.env.docker`); Railway model-service vars **unverified** this session (CLI/API auth blocked). H stays on Open-Meteo (+ archive for recent past) → climatology. **User must paste** `VISUAL_CROSSING_API_KEY` — see signup below. |

---

## Confirmatory PLAY ablation (2024–25 spreads, v2 band)

Method: stored pre-kickoff projections + week−1 lagged factor deltas.  
Baseline matches prior play-only holdout (~72.9% ATS / ~60.4% CLV+).

| Variant | n | ATS | CLV+ (move) | n_clv | Gate | Decision |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| **baseline** | 229 | **0.7293** | **0.6039** | **207** | **GREEN** | — |
| A coach | 223 | 0.7265 | 0.6020 | 201 | GREEN | **KILL** (ATS regress) |
| B personnel | 229 | 0.7293 | 0.6039 | 207 | GREEN | **KILL** (no signal) |
| E info velocity | 232 | 0.6940 | 0.5972 | 211 | GREEN | **KILL** (ATS −3.5pp) |
| **H travel×weather** | 220 | **0.7364** | **0.6041** | 197 | YELLOW | **PROMOTE** |
| **D error regime** | 229 | 0.7293 | 0.6039 | 207 | GREEN | **PROMOTE** (0 pt shift) |
| all enabled | 227 | 0.7004 | 0.6029 | 204 | GREEN | **KILL combo** |
| H+D (+A prior script) | 218 | 0.7431 | 0.6051 | 195 | YELLOW | see below |

### Primary 2025 PLAY

| Variant | n | ATS | CLV+ | Gate |
| --- | ---: | ---: | ---: | --- |
| baseline | 112 | 0.6964 | 0.5800 | YELLOW |
| H alone | 107 | 0.7196 | 0.5895 | YELLOW |

---

## Promoted vs killed (defaults shipped)

| Factor | Default | Why |
| --- | --- | --- |
| **H** `travel_weather_interaction` | **ON** | Confirmatory ATS +0.71pp; CLV+ flat/+; graceful skip if feeds missing |
| **D** `error_regime` | **ON** | Uncertainty widen / confidence penalty only; PLAY points unchanged |
| **E** `info_velocity` | **OFF** | Confirmatory ATS 0.729 → 0.694 (−3.5pp) |
| **B** `personnel_efficiency` | **OFF** | Cannot materialize — `offense_personnel` missing from public PBP |
| **A** `coach_aggression` | **OFF** | Slight ATS/CLV regress vs baseline (ST/QB discipline) |

Env kill-switches remain (`NFL_FRAMEWORK_*_ENABLED`).

---

## Gate status

| Gate | Status | Note |
| --- | --- | --- |
| selective_play_ready | **true** | Locked v2 on stored boards still GREEN (n_clv≥200) |
| betting_product_ready | **false** | Full-slate RED unchanged |
| Ablation H-only board | YELLOW | n_clv 197 softens under 200 — live H is small additive challenger |

---

## Model health

| Area | Light |
| --- | --- |
| KAV v3 + selective PLAY (stored) | **GREEN** |
| Simulator / Railway degrade | **GREEN** |
| H travel×weather (promoted) | **YELLOW** (promoted on lift; CLV n soft; no VC key yet; Open-Meteo path hardened) |
| D error-regime (promoted) | **GREEN** (uncertainty-only) |
| E info velocity | **RED** (holdout fail — disabled) |
| A coach thin | **YELLOW→OFF** (materialized but disabled) |
| B personnel | **RED** (no data path) |
| Full-slate product | **RED** |

---

## Honest score: **7.6 / 10**

No score bump. Provisional 7.7 revoked after ablation: highest-priority E **fails** holdout; B cannot ship; A does not clear improve bar. H/D are small additive promotions that do not move the product readiness claim.

---

## Gaps to 9.5

1. Find a real personnel source (participation/package feed) before re-probing B.
2. Retune E (velocity weights / lag) offline — do not re-enable until ablation clears.
3. Optional: re-probe A at lower weights after more seasons of coach materialization.
4. Add `VISUAL_CROSSING_API_KEY` to strengthen H weather quality (not required for promote).
5. Live 2026 paper→stake under locked v2; keep full-slate RED until proven.

---

## Visual Crossing — user action still needed

| Item | Status |
| --- | --- |
| Key in local `.env` / `infra/.env.docker` | **Absent** |
| Railway model-service production | **Not set from this session** (auth blocked; assume absent until pasted) |
| Backfill / VC fetch | **Skipped** — no key; inventing one is forbidden |
| Open-Meteo dry-run (BUF, +3d) | **OK** — hourly forecast returned |
| Rate limit | VC free ~**1000/day**; cache ~18h + 1.1s spacing when keyed |

**Signup:** https://www.visualcrossing.com/weather-api → Get Free API Key → set `VISUAL_CROSSING_API_KEY` locally + Railway model-service.  
Verify: `python -m data_platform_nfl.cli --print-external-source-status` (`has_key: true`).

Open-Meteo (no-key) wins shipped: ±1h wind/temp mean, 1h process cache, forecast past **14d** + archive to **90d** before climatology.

---

## Env keys

| Var | Needed? |
| --- | --- |
| `VISUAL_CROSSING_API_KEY` | Optional — improves H weather source (**user paste required**) |
| `NFL_VC_WEATHER_ENABLED` | Default true when keyed |
| `NFL_FRAMEWORK_TRAVEL_WEATHER_ENABLED=true` | Default ON (promoted) |
| `NFL_FRAMEWORK_ERROR_REGIME_ENABLED=true` | Default ON (promoted) |
| `NFL_FRAMEWORK_INFO_VELOCITY_ENABLED` | Default OFF |
| `NFL_FRAMEWORK_PERSONNEL_ENABLED` | Default OFF |
| `NFL_FRAMEWORK_COACH_AGGRESSION_ENABLED` | Default OFF |
