# Historical Odds – Credit Estimate (Odds API)

Use this to plan how many credits you need so you don’t waste any. **Credits reset on the 1st of each month** (not just the year).

## Cost formula (historical endpoint)

- **10 credits per region × per market per request** (the-odds-api.com historical).
- We use **1 region** (`us`) and **2 requests per day** (open snapshot + close snapshot).
- So: **credits per day = 20 × (number of markets)**.

| Markets requested             | Credits/request | Requests/day | Credits/day |
| ----------------------------- | --------------- | ------------ | ----------- |
| 2 (e.g. spreads, totals)      | 20              | 2            | **40**      |
| 3 (e.g. h2h, spreads, totals) | 30              | 2            | **60**      |

---

## Your requested coverage (estimate) — back to 2000

Assumptions: 1 region (`us`), 2 requests/day (open + close), **seasons from 2000–01 through 2024–25** (25 full seasons unless noted).  
**Important:** The Odds API may **not** offer historical data back to 2000 for any sport. Their docs often cite **June 2020** (or Nov 2020 for NCAAB) as the earliest. Confirm per-sport start dates at [the-odds-api.com](https://the-odds-api.com) before running large pulls; if data only starts in 2020, real credits will be much lower.

| Sport        | Markets                  | Season range                            | Est. days | Credits/day | Est. total credits |
| ------------ | ------------------------ | --------------------------------------- | --------- | ----------- | ------------------ |
| **MLB**      | Moneyline (h2h) + totals | 2000 → 2025 (Apr–Oct each year)         | ~5,564    | 40          | **222,560**        |
| **NFL**      | Spread + totals          | 2000–01 → 2024–25 (game days only)      | ~2,100    | 40          | **84,000**         |
| **NBA**      | Spread + totals          | 2000–01 → 2024–25                       | ~4,250    | 40          | **170,000**        |
| **NHL**      | Moneyline (h2h) + totals | 2000–01 → 2024–25                       | ~5,000    | 40          | **200,000**        |
| **CFB (D1)** | Spread + totals          | 2000–01 → 2024–25, **excl. bowl games** | ~2,450    | 40          | **98,000**         |
| **WNBA**     | Spread + totals          | 2000 → 2024                             | ~3,000    | 40          | **120,000**        |
| **NCAAB**    | Spread + totals          | 2000–01 → 2024–25                       | ~3,750    | 40          | **150,000**        |

**Rough total (if all dates from 2000 are available): ~1,044,560 credits.**

Day math by sport:

- **MLB:** 26 seasons (2000–2025) × ~214 days (Apr–Oct) = 5,564.
- **NFL:** 25 seasons × ~84 game days = 2,100.
- **NBA:** 25 seasons × ~170 days (Oct–Jun) = 4,250.
- **NHL:** 25 seasons × ~200 days (Oct–Jun) = 5,000.
- **CFB:** 25 seasons × ~98 days (Sep–early Dec, no bowls) = 2,450.
- **WNBA:** 25 seasons (2000–2024) × ~120 days (May–Oct) = 3,000.
- **NCAAB:** 25 seasons × ~150 days (Nov–Apr) = 3,750.

---

## Notes

1. **API start dates:** Many sports on the Odds API only have historical from **2020** (e.g. NCAAB from 2020-11-16). If that’s the case, only days from 2020 onward count; total credits would be far lower than the table above.
2. **CFB:** “Excluding bowl games” = only request dates before bowl season (e.g. through early Dec). Fewer days than full season.
3. **Game days vs calendar days:** NFL/NBA/NHL/MLB don’t have games every day. You can reduce credits by only requesting **dates that have games** (if your fetch script supports that). The table above uses calendar-day estimates; actual game-days-only would be lower for NFL especially.
4. **Plans:** Common tiers are 20K, 90K, 100K, 450K, etc. per month. ~1M credits would require a large plan or spreading pulls across many months.

---

## Suggested approach

1. **Confirm historical start dates** per sport (e.g. one test request per sport).
2. **Prioritize** which sports/seasons you need first.
3. **Run in order** (e.g. one sport per month) so you stay within quota and don’t waste credits.
4. **Re-run the credits check** (`pnpm run check:odds-credits`) before/after big pulls.
