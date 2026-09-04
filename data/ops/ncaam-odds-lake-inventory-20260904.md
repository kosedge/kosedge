# NCAAM Odds lake inventory — Path A (2026-09-04)

**Task:** Kos Edge #14 / #3 — historical odds lake **INVENTORY ONLY**  
**Branch:** `cursor/ncaam-odds-lake-inventory-4b3c` → `deploy-vercel`  
**Hard rules honored:** No Odds API calls · no credit spend · no Lab cut / model / board changes

Machine receipts:

- `data/ops/ncaam-odds-lake-inventory-20260904.receipt.json`
- `data/ops/ncaam-odds-lake-inventory-20260904.hole-missing-dates.txt` (482 days)
- `data/ops/ncaam-odds-lake-inventory-20260904.early-missing-dates.txt` (715 days)

Prior densify SoT (do not re-litigate Lab): `data/ops/ncaam-odds-densify-20260904.md` + `.summary.json` / `.u0-receipt.json` / `.hole-receipt.json`.

---

## Verdict (one paragraph)

We did **not** already have the hole/early days sitting in another store: Path B is README-only, the processed parquet `open_time` dates exactly match Path A (**0** overlap with the **482 + 715** missing days), the stale `apps/web/src/data/...` parquet copy only covers 2022-11→2023-04, and the July enterprise training-pull verify receipt shows `ncaam.mainline_games=0` despite a checkpoint claiming 894 dates. The gaps exist because pre-#482 Path A only ever held `2022-11-01→2024-01-28` plus a thin 2025-11 pocket; densify then spent ~14.3k credits on U0 honesty drops (185 last-known opens removed) plus a credit-capped 172-day season-priority hole slice (~160 kept), stopping with **~131 credits left** — enough to explain skipping the remaining **482** hole days and the entire **715**-day early window (~28.6k), not a failure to look in the DB for owned snapshots.

---

## 1. Store inventory (fail-closed)

| Store | Path | Odds lake? | Finding |
|-------|------|------------|---------|
| **Path A raw** | `apps/web/data/raw/odds/{open,close}` | **YES — canonical** | **463 / 463** dated JSON pairs |
| **Path A parquet** | `apps/web/data/processed/ncaab_historical_odds_open_close.parquet` | **YES — processed** | **189,609** rows / **15,459** events; open dates = Path A set |
| Path A stale copy | `apps/web/src/data/processed/ncaab_historical_odds_open_close.parquet` | No (stale) | 84,672 rows; open `2022-11-01→2023-04-16`; **0** overlap w/ missing |
| Path B | `apps/web/data/historical-odds/ncaab/` | **No** | README-only (no `open/`/`close/`) |
| Merged join | `.../merged_games_with_odds_and_ratings.parquet` | Derived | Path A ∩ ratings; **0** missing `open_time` overlap |
| Enterprise pull ops | `data/ops/odds-enterprise-training-pull/` | Not a lake dump | Checkpoint `ncaam:mainlines` **894** dates; inventory **`mainline_games: 0`** (2026-07-28) |
| Railway `odds_snapshots` | model-service Postgres | Unknown live (sealed URL) | Best in-repo receipt = enterprise **0** NCAAM games; no SQL dump in-repo. Live `/api/jobs/nba-inventory` works; no working NCAAM inventory route |
| Prisma `MarketSnapshot` / `BookLine` | `apps/web/prisma/schema.prisma` | Live/board schema | Not a historical open/close lake |
| KenPom / SportsData / schedules / KEI skeleton | various | **NOT odds** | Excluded (game result ≠ odds snapshot) |

---

## 2. Independent missing-date recount

Honesty rule (same as densify / fetch script): Path A day counts as owned only if **both** open+close JSON exist **and** open API `timestamp` drifts **≤7d** from filename date (and file non-empty).

### Hole — `2024-01-29 → 2025-10-31`

| Metric | Claimed (#482) | **Recount** |
|--------|---------------:|------------:|
| Calendar days in window | 642 | **642** |
| Honest Path A owned | ~160 | **160** |
| Missing honest Path A | **482** | **482** |
| Present-but-dishonest in window | — | **0** |
| Parquet `open_time` date ∩ missing | — | **0** → **ALREADY OWNED: none** |

Missing ranges:

1. `2024-04-16 → 2024-10-26` — **194d**
2. `2025-01-17 → 2025-10-31` — **288d**

Owned inside hole (for context): `2024-01-29→2024-04-15` (78) + `2024-10-27→2025-01-16` (82).

### Early — `2020-11-16 → 2022-10-31`

| Metric | Claimed (#482) | **Recount** |
|--------|---------------:|------------:|
| Calendar days | 715 | **715** |
| Honest Path A owned | 0 | **0** |
| Missing | full window | **715** |
| Parquet ∩ missing | — | **0** → **ALREADY OWNED: none** |

False friend (not ownership): parquet has **56** events with `commence_time` on `2025-01-17` but `open_time` **2025-01-16** (already owned). Fail-closed: commence ≠ snapshot day.

---

## 3. Credits to finish (from fetch script — not guessed)

Source: `apps/web/scripts/fetch_historical_ncaab_odds.py`

- `regions=us`, `markets=spreads,totals`
- `CREDITS_PER_REQUEST = 20`
- Open + close = **2 requests/day** → **40 credits/day**

| Pocket | Remaining days | Credits |
|--------|---------------:|--------:|
| Hole remainder | **482** | **19,280** |
| Early window | **715** | **28,600** |
| **Total (all calendar missing)** | **1,197** | **47,880** |

Densify receipt remaining credits: **131** (`hole-receipt.credits_remaining_last`, summary `final_remaining`).

Optional season-priority subsets (Nov–Apr only; still calendar days, not Lab windows):

| Subset | Days | Credits |
|--------|-----:|--------:|
| Hole in-season-ish | 119 | 4,760 |
| Early in-season-ish | 347 | 13,880 |

Offseason May–Oct days often return API last-known (honesty drop risk) — densify already prioritized in-season for that reason.

---

## 4. Why the last densify run stopped

| Step | What happened |
|------|----------------|
| **U0** (`2022-11-01→2024-01-28`) | 185 dishonest opens re-pulled; API still last-known; **all 185 dropped**. Header credits **7,400**. Honesty fails 185→0 in that window. |
| **Hole** | Dates-file pre-capped to **172** season-priority days (budget), not a mid-loop `--max-credits` stop (`stopped_for_credits: false`). **12** days (2024-10-15→26) dropped dishonest. **~160 kept**. **482 never requested**. |
| **Early** | **Skipped** — ~**131** credits left vs ~**28,600** needed. |

So: **credit cap / intentional skip**, not “true miss of data we already owned elsewhere.”

---

## 5. Integrity snapshot (current lake baseline — not a Lab scorecard)

| Check | Result |
|-------|--------|
| Path A open/close | 463 / 463; no open-only / close-only |
| Honest pairs | **462** |
| Residual dishonest open | **1** — `2023-04-11` (API ts `2023-04-04T03:40:39Z`, drift **7.35d**, 1 event). Densify ops table listed pocket through 04-11; honesty-correct end is **2023-04-10** (157d). |
| Empty / placeholder files | **0** |
| Zero-event snapshots | **0** |
| Honest pockets | `2022-11-05→2023-04-10` (157), `2023-10-10→2024-04-15` (189), `2024-10-27→2025-01-16` (82), `2025-11-01→2025-12-04` (34) |
| Parquet | 189,609 rows / 15,459 events / 21 books; open dates ↔ Path A 1:1 |
| `event_id+book` multi-rows | 4,759 groups — same event listed on multiple snapshot dates (expected from `process_odds`), not duplicate files |
| Null lines (book rows) | open_spread 1,742 · close_spread 1,912 · open_total 2,778 · close_total 3,610 |

---

## 6. Explicit non-claims

- **Inventory + pricing inputs only.** No Lab Train-A / Test-A / Holdout re-appendix.
- No Odds API fetch, no credit burn, no board / PLAY / peek-tune.
- Railway live NCAAM `odds_snapshots` count not re-verified SQL-side this run (credentials sealed); in-repo enterprise verify remains **0** — fail-closed against “already owned in DB.”
- Dates-files are for a **later** backfill; this PR does not run them.

---

## Next (CoS / Ryan)

1. Top up / wait for monthly Odds API credit reset.
2. Prefer hole in-season remainder first (`hole-missing-dates.txt` filtered Nov–Apr), then early in-season, using `fetch_historical_ncaab_odds.py --dates-file … --drop-dishonest-open --max-credits … --receipt`.
3. Re-run `process_odds` after any pull; do **not** re-appendix Lab cuts from lake capability alone.
