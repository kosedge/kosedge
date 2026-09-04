# NCAAB historical odds — Path B (retired destination claim)

## Status (Odds P1 VERIFY ACCEPTED — ONE EMPTY)

**This directory is docs-only.** There is **no** `open/` or `close/` JSON under
`apps/web/data/historical-odds/ncaab/`, and those trees were **never tracked** in
git. Do **not** treat Path B as a second market lake.

CoS Odds P1 VERIFY: Path B = README-only / **ONE EMPTY**. Scripts already write
and read **Path A** only.

---

## Live lake (Path A) — use this

| Role | Path |
|------|------|
| Raw open snapshots | `apps/web/data/raw/odds/open/YYYY-MM-DD.json` |
| Raw close snapshots | `apps/web/data/raw/odds/close/YYYY-MM-DD.json` |
| Processed parquet | `apps/web/data/processed/ncaab_historical_odds_open_close.parquet` |

Canonical layout and pipeline order: [`apps/web/data/README.md`](../../README.md).

Code SoT (no Path B):

- `scripts/fetch_historical_ncaab_odds.py` → writes Path A
- `pipeline_paths.ODDS_OPEN` / `ODDS_CLOSE` → Path A
- `src/process_odds.py` → reads Path A → parquet above

---

## Coverage floor (honest — do not invent denser)

| Layer | Floor |
|-------|--------|
| **Odds API** NCAAB historical (`basketball_ncaab`) | From **2020-11-16** (API start; no pre-2020–21) |
| **In-repo Path A lake** (VERIFY) | Currently starts **2022-11-01** |

Do not claim 2020–21 / 2021–22 open/close JSON in this repo unless Path A is
actually densified later. API availability ≠ lake contents.

---

## Credits (cost on the-odds-api.com)

Unchanged planning note for anyone running the Path A fetch script:

- **Historical odds endpoint**: **10 credits per region per market**.
- Script uses `regions=us` and `markets=spreads,totals` → **20 credits per request**.
- **2 requests per day** (open + close) → **40 credits per day**.

| Range | Days (approx) | Requests | Credits (approx) |
|-------|----------------|----------|-------------------|
| One season (~150) | 150 | 300 | 6,000 |
| 2020-11 → 2025-04 | ~1,600 | 3,200 | 64,000 |
| **3 seasons** | ~900 | 1,800 | **~22,000** |

---

## Usage (writes Path A, not here)

1. `export ODDS_API_KEY="your_key"`
2. From `apps/web`:

   ```bash
   python scripts/fetch_historical_ncaab_odds.py
   # optional range:
   python scripts/fetch_historical_ncaab_odds.py --start 2024-11-01 --end 2025-02-15
   python src/process_odds.py
   ```

Output lands under **`data/raw/odds/{open,close}/`**, then parquet under
**`data/processed/`** — never under this Path B folder.
