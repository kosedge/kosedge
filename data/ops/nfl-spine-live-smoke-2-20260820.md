# NFL spine LIVE smoke 2 — 2026-08-20

**Status:** A1–A4 green with an honest 2026 gap label → **`NFL_WEEKLY_PROPS_LIVE = false` (flag not flipped)**  
**Ready for LIVE brief:** **yes** — A1/A4 green; 2025 still 3C; 2026 SUM is populated and labeled, not claimed as 3C-tight receiving.  
**Branch:** `fix/nfl-spine-worker-hygiene-2026-sum` (hygiene image landed on Railway this afternoon)  
**Spine version:** `player-production-v3-phase3c`  
**Edge cal:** unchanged `prop-structure-cal-v1`  
**Checked:** 2026-08-20 18:28–18:51 UTC

No PLAY / blend / DK-FD / structure-knob retune in this pass.

Root cause for 2026 gap 0.417: `data/ops/nfl-spine-2026-gap-20260820.md`.

---

## Smoke table (A)

| Gate | Result | Evidence |
|------|--------|----------|
| A1 services | **GREEN** | API / worker / beat / Postgres Online. New worker `celery@405ad06c058f`. `default` LLEN **0**, `poison_in_sample` empty. Bare baselines **400**. `/health/celery` broker redacted. Beat does not schedule rebuild/bare remats. Models backlog is leftover MLB nowcast / market-history, not week-22 poison. |
| A2 prod parity | **GREEN** (2025) / **reported** (2026) | 2025 cap-17: **max 4590 / n=4 / gap 0.097**. 2026 weeks 1–18 remat today: **max 4297 / n=4 / gap 0.417**. Cause = densified hydrate/rookie intercepts, not missing 3C knobs. |
| A3 equality | **GREEN** | 2025 w1 n=40 and 2026 w1 n=24: props path == fantasy path (`production_from_baseline_row`). |
| A4 surfaces | **GREEN** | Draft rankings count **940** (half-PPR 2026). www `/pro/nfl/fantasy` **200**, McCaffrey #1 **17g** from API (not `preseason-fallback`). Weekly fantasy **200** (was 500). Props **200** gated (“not live”). No false degraded banner. |

**Gate:** Part B LIVE flag stays **false** in this PR. 2026 receiving is **not** 3C-tight; desk methods note ships with the web PR.

---

## A1 — Railway services (post hygiene deploy)

| Service | Railway | Probe |
|---------|---------|-------|
| model-service / API | Online · deploy `d33b382d` 2026-08-20 14:46 ET | `/health` ok · `/health/db` connected · `/health/celery` ok, password redacted |
| model-service-worker | Online · `a14ae261` | Consuming `default,odds,models` |
| model-service-beat | Online · `304c9477` | Cycle week clamped 1–18; no `run_nfl_props_layer_rebuild` / bare baselines in beat |
| Postgres | Online | Direct query ok |

Queues at 18:50 UTC: `default` 0 · `models` ~597 (nowcast/history; **0** poison remats in sample) · `odds` 0.

Controlled proofs (no week-22 path):

- `POST /nfl/ops/materialize-player-baselines?season=2026` → **400** (`week is required`)
- Season-only rebuild now expands to weeks **1–18** on `models` (do not fire a full rebuild in this smoke)
- 2026 W13–18 remat `97f95d57` **SUCCESS** before this deploy (no bounce during STARTED)

Safe entrypoint: `data/ops/nfl-spine-safe-rematerialize.md`.

---

## A2 — Prod data parity

### 2025 cap-17 (control, must not regress)

| Metric | 3C expect | **Prod now** |
|--------|-----------|--------------|
| Max QB pass | ~4590 | **4590** (D.Prescott DAL, 17g) |
| n ≥4000 | 4 | **4** |
| Pass↔rec gap | ~0.10 | **0.097** |

### 2026 cap-17 (today’s remat, not 3C-tight rec)

| Metric | Jul 19 (first smoke) | **Now** |
|--------|----------------------|---------|
| Max QB pass | 4123 (Goff) | **4297 (Burrow)** |
| n ≥4000 | 3 | **4** |
| Pass↔rec gap | 0.299 | **0.417** |
| Baseline `updated_at` | 2026-07-19 | **2026-08-20** weeks 1–18 |

3C knobs **did** apply (QB winner-take-most 0.92, attempt cap, `TEAM_PASS_ATTEMPTS_TARGET_SCALE=0.92` on skill targets). Gap is **receiving high** because 2026 week-1 features are `rookie_baseline_v1` + `preseason_hydrate_v1` (~25 skill players/team vs ~8 PBP in 2025). Additive target intercepts (WR 0.6 / TE 0.55 / RB 0.5) do not renormalize on that grain. Rankings sanity: Burrow **4297** in draft table = pool max.

---

## A3 — Equality smoke

Same helper `production_from_baseline_row` on prod baselines.

| Sample | n | equal | mismatch |
|--------|---|-------|----------|
| 2025 w1 first 40 QB/RB/WR | 40 | 40 | 0 |
| 2026 w1 first 24 QB/RB/WR | 24 | 24 | 0 |

Spine `player-production-v3-phase3c`.

---

## A4 — Surface smoke

| Surface | HTTP | Notes |
|---------|------|-------|
| `/pro/nfl/fantasy` | 200 | McCaffrey #1, 17 games, API payload in page. **No** `preseason-fallback`. No degraded banner. SUM methods copy lands with this web PR. |
| `/pro/nfl/props` | 200 | Gate “not live”. No degraded banner. `NFL_WEEKLY_PROPS_LIVE = false`. |
| `GET /nfl/fantasy/draft-rankings?season=2026` | 200 count **940** half-PPR (300 default page) | SoT SUM table populated (2025: 601 / profile) |
| `GET /nfl/fantasy/rankings?season=2026&week=1` | **200** count 300 | Was 500 (`AmbiguousParameter`). CAST + empty-200 in API image |
| `GET /nfl/ops/player-layer-coverage?season=2026` | 200 | No week param — not 500 |

Materialize jobs: 2025 `0e25f70c` SUCCESS (1803 rows / 3 profiles); 2026 `b979d81f` SUCCESS (2820 rows). Kickers still 0 (expected).

---

## Remaining (not A1/A4 red)

- 2026 pass↔rec gap **0.417** — labeled, not patched. Do not describe 2026 receiving as 3C-tight.
- `models` still holds a nowcast/history backlog (`MLB_NOWCAST_ENABLED=false` on beat; leftover queue). Not week-22 poison.
- Web methods copy for the gap note ships when this PR hits `deploy-vercel` / Vercel.

**LIVE flag in this PR:** false. **Ready for LIVE brief: yes.**
