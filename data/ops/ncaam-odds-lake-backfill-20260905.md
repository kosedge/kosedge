# NCAAM Odds lake — FULL Path A backfill (2026-09-05)

**Task:** Kos Edge #14 — FULL NCAAM Path A odds lake backfill GO  
**Auth:** Ryan confirmed Odds API upgraded / on-demand payment (2026-09-05); ~100k tier  
**Branch:** `cursor/ncaam-odds-lake-path-a-backfill-7ac0` → `deploy-vercel`  
**Sport key:** `basketball_ncaab`  
**Path:** **A only** (`apps/web/data/raw/odds/{open,close}`) — Path B untouched  

> **Lake capability + Scorecard v1.2.** Lab cut dates **FROZEN** (no re-appendix).  
> No Edge Board / PLAY / peek-tune / invent KEI / Path B invent / #12 GO-2.  
> B2 stays quarantined. Influence INSUFFICIENT unless gate clears (it did not).

Machine receipts:

- `ncaam-odds-lake-backfill-20260905.hole-receipt.json`
- `ncaam-odds-lake-backfill-20260905.early-receipt.json`
- `ncaam-odds-lake-integrity-20260905.json` / `.md`
- `ncaam-lab-scorecard-v1-2-20260905.md`
- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.2.json`

---

## 1. Credits probe FIRST (cost 0)

| Metric | Value |
|--------|------:|
| Probe | `GET /v4/sports` via `check_odds_api_credits.py` |
| Remaining before | **99,953** |
| Used (period) before | 47 |
| Last request cost | **0** |
| Gate (~48k floor) | **PASS** (well above 48k; ~100k tier) |

API key never printed.

---

## 2. Backfill (inventory dates only)

Cost model unchanged: `regions=us`, `markets=spreads,totals` → **20 credits/request**, open+close → **40 credits/day**.

| Batch | Dates file | Days | Header credit sum | Dropped dishonest (>7d) | Failed | Remaining after |
|-------|------------|-----:|------------------:|------------------------:|-------:|----------------:|
| Hole | `…hole-missing-dates.txt` | 482 | **19,280** | **378** | 0 | 80,569 |
| Early | `…early-missing-dates.txt` | 715 | **28,600** | **406** | 0 | 51,844 |
| **Total** | | **1,197** | **47,880** | **784** | **0** | |

| Metric | Value |
|--------|------:|
| Remaining after (probe) | **~51,823** |
| Used (period) after | ~48,177 |
| Header-sum burn (hole+early) | **47,880** |
| Probe / misc delta vs period | ~small (sports-list probes) |

Script: `fetch_historical_ncaab_odds.py --dates-file … --drop-dishonest-open --receipt …`  
**No `--force`** on already-owned days (skip-if-exists).

---

## 3. Honesty-drop (same as densify #482)

Open API `timestamp` drift **>7d** from filename date → delete open+close for that day (last-known / offseason junk).

| | Hole | Early |
|--|-----:|------:|
| Dropped | 378 | 406 |
| Kept after drop (approx) | 104 | 309 |

**Post-backfill lake honesty fails:** **0** (integrity).

---

## 4. Inventory after (Path A)

| | Open JSON | Close JSON | Paired |
|--|----------:|-----------:|-------:|
| **Before** (post densify 2026-09-04) | 463 | 463 | 463 |
| **After** | **876** | **876** | **876** |

**Honesty-clean paired ranges:**

| Start | End | Days |
|-------|-----|-----:|
| 2020-11-16 | 2021-04-13 | 149 |
| 2021-11-04 | 2022-04-12 | 160 |
| 2022-11-05 | 2023-04-11 | 158 |
| 2023-10-10 | 2024-04-16 | 190 |
| 2024-08-20 | 2024-08-26 | 7 |
| 2024-10-27 | 2025-04-15 | 171 |
| 2025-10-25 | 2025-12-04 | 41 |

Note: the Aug 2024 pocket (7d) passed the >7d honesty gate (contemporaneous API timestamps); kept.

---

## 5. `process_odds` → parquet

| | |
|--|--|
| Output | `apps/web/data/processed/ncaab_historical_odds_open_close.parquet` |
| Rows (before → after) | 189,609 → **321,147** (after same-day event/book/open_time dedupe; was 321,320 raw) |
| Unique events | 15,459 → **26,759** |
| Fix | Explicit Float64 schema for spread/total (mixed int/half-points broke infer) |

Path A only. Path B (`historical-odds/ncaab/`) untouched.

---

## 6. Integrity grades

| Check | Grade |
| ----- | ----- |
| coverage | **GREEN** |
| open_honesty | **GREEN** (0 fails) |
| duplicates | **GREEN** (same-day key; multi-day event+book expected) |
| event_team_identity | **GREEN** |
| timestamps | **GREEN** |
| line_price_validity | **AMBER** (sparse \|spread\|>45 / total\<100 cells; expected on blowouts / thin books) |
| missingness | **GREEN** (close_spread null ~2.45%) |
| outliers | **AMBER** (same as line/price) |

Receipt: `data/ops/ncaam-odds-lake-integrity-20260905.json`.

---

## 7. Lab cuts FROZEN → Scorecard v1.2

- Cuts unchanged: Train-A `2022-11-07→2023-03-12`; Test-A `2023-11-06→2024-01-28`; 2025 pocket OUT  
- Rematerialized fair parquet (same cuts) then **one** scorecard run → **v1.2**  
- Frozen v1 / v1.1 SHA256 **unchanged**  
- No model/threshold/feature/validation-date changes  
- B2 quarantined; Board/PLAY dark  

### Grades (Test-A OOS) — computed, no peek-tune

| Pillar | v1.1 | v1.2 |
| ------ | ---- | ---- |
| Predictive Quality | **AMBER** | **AMBER** |
| Market Edge Evidence | **AMBER** | **AMBER** |
| Evidence Quality | **GREEN** | **GREEN** |
| Subscriber Influence | **INSUFFICIENT EVIDENCE** | **INSUFFICIENT EVIDENCE** |

### Honest compare (Lab grain identical)

| Metric | v1.1 | v1.2 |
| ------ | ---- | ---- |
| Test-A n_actual / n_lab | 2205 / 2298 (0.9595) | 2205 / 2298 (0.9595) |
| Train-A n_actual / n_lab | 3583 / 3676 (0.9747) | 3583 / 3676 (0.9747) |
| Test-A B2 / B1 MAE | 9.248 / 8.5703 | 9.248 / 8.5703 |
| Test-A ATS / CLV+ | 0.5305 / 0.5012 | 0.5305 / 0.5012 |

**Interpretation:** hole + early missing days sit **outside** frozen Lab windows, so primary Lab metrics match v1.1 bit-for-bit after rematerialize. Lake capability expanded; Lab windows not re-appendixed. No second run. No model rebuild.

---

## Explicit non-claims

- No Path B invent  
- No Edge Board / PLAY / Conf% / invent KEI  
- No Lab cut date change  
- No threshold shopping / peek-tune after Test-A  
- Influence remains **INSUFFICIENT** (gate did not clear)  
- Scorecard did not “fail” in the RED/diagnose-rebuild sense — AMBER pillars are honest soft clears under frozen gates; stop-and-diagnose-for-model-rebuild **not** triggered  
