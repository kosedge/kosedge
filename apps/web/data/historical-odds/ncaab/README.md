# NCAAB historical odds (open + close)

## ⚠️ 2015–2016 is not available

**The Odds API only has NCAAB historical data from November 16, 2020** (`basketball_ncaab` start date). They do not offer 2015–2016 or any season before 2020–21.

Seasons you *can* pull:

- **2020–21** (from 2020-11-16)
- **2021–22**, **2022–23**, **2023–24**, **2024–25**

---

## Credits (cost on the-odds-api.com)

- **Historical odds endpoint**: **10 credits per region per market**.
- This script uses `regions=us` and `markets=spreads,totals` → **2 markets × 1 region = 20 credits per request**.
- We do **2 requests per day** (one “open” snapshot, one “close” snapshot) → **40 credits per day**.

Rough totals:

| Range              | Days (approx) | Requests | Credits (approx) |
|--------------------|----------------|----------|-------------------|
| One season (~150)  | 150            | 300      | 6,000             |
| 2020-11 → 2025-04  | ~1,600         | 3,200    | 64,000            |
| **3 seasons**      | ~900           | 1,800    | **~22,000**       |

Check your plan: 20K/month, 100K/month, etc. You can run the script for a **short date range** first (e.g. one month) to confirm everything and cost.

---

## Usage

1. Set your API key:  
   `export ODDS_API_KEY="your_key"`

2. Install deps (if needed):  
   `pip install requests`  
   (or use the same venv as `ingest_kenpom`.)

3. Run (default: from 2020-11-16 to today, open + close each day):

   ```bash
   cd apps/web
   python scripts/fetch_historical_ncaab_odds.py
   ```

4. Optional date range:

   ```bash
   python scripts/fetch_historical_ncaab_odds.py --start 2024-11-01 --end 2025-02-15
   ```

Output files:

- `data/historical-odds/ncaab/open/YYYY-MM-DD.json` – snapshot early that day (UTC).
- `data/historical-odds/ncaab/close/YYYY-MM-DD.json` – snapshot later that day (UTC).

Each JSON has the API response: `timestamp`, `previous_timestamp`, `next_timestamp`, and `data` (list of events with `bookmakers`, etc.).
