# NCAAM Odds densify — Path A (2026-09-04)

**Task:** Kos Edge #14 — Odds densify GO (Ryan authorized API credits)  
**Branch:** `cursor/ncaam-odds-densify-cc68` → `deploy-vercel`  
**Sport key:** `basketball_ncaab`  
**Path:** **A only** (`apps/web/data/raw/odds/{open,close}`) — Path B untouched (README-only)

> **Lake capability only; Lab windows unchanged.**  
> Do not claim new Lab coverage windows. Lab cuts stay locked until CoS re-appendixes.  
> No Edge Board / PLAY / peek-tune v1 / invent tips / #12 GO-2.

Machine receipts: `ncaam-odds-densify-20260904.summary.json`, `.u0-receipt.json`, `.hole-receipt.json`.

---

## Credits (Odds API headers)

| Metric | Value |
|--------|------:|
| Remaining before densify (approx) | **14,491** |
| U0 re-pull (`x-requests-last` sum) | **7,400** |
| Hole fill (`x-requests-last` sum) | **6,880** |
| U0 + hole header sum | **14,280** |
| Remaining after densify | **131** |
| Used this period (final) | **19,869** |

Cost model unchanged: `regions=us`, `markets=spreads,totals` → **20 credits/request**, open+close → **40 credits/day**.

---

## Before / after inventory (Path A)

| | Open JSON | Close JSON |
|--|----------:|-----------:|
| **Before** | 488 | 488 |
| **After** | 463 | 463 |

**Before ranges:** `2022-11-01→2024-01-28` (454) + `2025-11-01→2025-12-04` (34).

**After ranges (kept, honesty-clean opens):**

| Start | End | Days |
|-------|-----|-----:|
| 2022-11-05 | 2023-04-11 | 158 |
| 2023-10-10 | 2024-04-15 | 189 |
| 2024-10-27 | 2025-01-16 | 82 |
| 2025-11-01 | 2025-12-04 | 34 |

Net file count dropped because U0 removed 185 dishonest last-known pairs; hole fill then added ~160 honest in-season pairs.

---

## 1. U0 honesty repair (`2022-11-01 → 2024-01-28`)

| | |
|--|--|
| Honesty fails **before** (open API `timestamp` drift >7d) | **185** |
| Honesty fails **after** (same window, files present) | **0** |
| Opens present in U0 window after | **269** (was 454) |
| Days force re-pulled | **185** |
| Dropped after re-pull (still >7d) | **185** |

**Finding:** Re-pull confirmed Odds API **last-known reuse** for all 185 failing days (offseason Apr–Oct 2023 + early Nov 1–4 2022). Timestamps did not become contemporaneous. Those Path A pairs were **dropped** so the lake no longer stores stale opens that Market Edge would filter anyway.

Script: `fetch_historical_ncaab_odds.py --dates-file … --force --drop-dishonest-open`.

---

## 2. Hole fill (`2024-01-29 → 2025-10-31`) — partial

Full target = **642** missing calendar days (~25,680 credits). Remaining budget allowed **172** days.

**Season-priority pull (not blind summer burn):**

1. `2024-01-29 → 2024-04-15` (78d) — rest of 2023–24  
2. `2024-10-15 → 2025-01-16` (94d) — start of 2024–25  

| | |
|--|--:|
| Days requested / fetched | 172 / 172 |
| Dropped dishonest (pre-season Oct 15–26 last-known) | 12 |
| Kept | ~160 |
| Still missing in full hole target | **482** |

---

## 3. Early window (`2020-11-16 → 2022-10-31`) — skipped

**Not pulled.** Credits exhausted (~131 left; early window ≈ 715×40 = **28,600**). Resume after monthly reset / top-up.

---

## `process_odds` refresh

| | |
|--|--|
| Output | `apps/web/data/processed/ncaab_historical_odds_open_close.parquet` |
| Rows | **189,609** |
| Unique events | **15,459** |
| `open_time` span | `2022-11-05T12:00:00Z` → `2025-12-04T12:00:00Z` |

---

## Script delta

`apps/web/scripts/fetch_historical_ncaab_odds.py` gained `--force`, `--dates-file`, `--max-credits`, `--drop-dishonest-open`, `--receipt` for bounded densify + honesty hygiene. Still Path A / `pipeline_paths.ODDS_*` only.

---

## Explicit non-claims

- **Lake capability only; Lab windows unchanged.**
- No Lab Train-A / Test-A / Holdout re-appendix.
- No Edge Board populate, PLAY/Conf%, peek-tune, invent tips, #12 GO-2.
- Path B (`historical-odds/ncaab/`) remains README-only.
- B7 alias / results-join agents are a parallel track — not blocked / not claimed here.
