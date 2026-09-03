# NFL Compare Odds — Odds API book feed honesty (2026-09-03)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Scope:** designated Compare Odds books vs what The Odds API actually carries for NFL.  
**Out of scope:** remat, KEI mint, hide, paywall, adding non-designated books.

## Designated books (Ryan — keep all nine columns)

`draftkings, fanduel, betmgm, betrivers, hardrockbet, fanatics, bet365, circa, betr`

Not `market` / `keinfl` (those are display aliases, not Odds API keys).

## Per-book Odds API coverage (NFL)

Source: [The Odds API bookmakers by region](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html) (CoS verified 2026-09-03).

| Key | Region | NFL on feed? | Notes |
| --- | --- | --- | --- |
| `draftkings` | `us` | **yes** | |
| `fanduel` | `us` | **yes** | |
| `betmgm` | `us` | **yes** | |
| `betrivers` | `us` | **yes** | |
| `hardrockbet` | `us2` | **yes** | Requires `regions=us,us2` (or explicit `bookmakers=`) |
| `fanatics` | `us` | **yes** | Paid-tier key |
| `bet365` | — | **no** | No US key. Only `bet365_au` (`au`, paid; AFL/NRL h2h/spreads/totals). Not usable for NFL. |
| `circa` | — | **no** | Circa Sports is **not** on The Odds API in any region. |
| `betr` | — | **no** | No US key. Only `betr_au` (`au`). |

**Request path:** pull only the six carried keys so we never invent lines and never risk `INVALID_BOOKMAKERS` on dead keys.  
**UI path:** keep all nine designated columns; the three zeros read as **not carried by the feed**, not as “book has no number.”

## Regions audit (`us,us2`)

| Path | Before | After |
| --- | --- | --- |
| `apps/web/lib/odds-api.ts` (`fetchEdgeBoard` / `fetchOddsComparison`) | `us,us2` | unchanged |
| `nfl_fair_lines` | `us,us2` | unchanged |
| `_fetch_live_nfl_market_lines_by_abbr` | `us,us2` | unchanged |
| `pull_odds_snapshot` (NFL sport) | `us` only | **`us,us2`** |
| `nfl_edges_today` | `us` only | **`us,us2`** |

`hardrockbet` lives in `us2`; `fanatics` is paid `us`. Bookmakers param still takes priority when set, but regions must include `us2` wherever we rely on region scoping.

## Street / Best Line

- **Best Line / Best O/U / Best ML** = best number across every **carried** book that posted (juice tiebreak; fresher `last_update` breaks remaining ties). Never DK-locked.
- **Open** = preferred-book current among posted carried books (DK → FD → …). That is open preference, not best.
- **PLAY stake close** remains DK → FD → consensus (grading a bettable DK/FD print). Shop column stays Best. No PLAY chrome ungated here.
- Do **not** invent lines for not-carried books.

## Occupancy note (live 2026-09-03)

DK **272** vs FD **32** / Fanatics **18** / BetRivers **17** / MGM **16** / Hard Rock **16** / bet365·circa·betr **0**:

- **272** = full NFL regular-season game count. DK is posting the season-long slate; other books are only printing the near-term (≈ Week 1 / next ~2 weeks) board. Honest market behavior — not a request bug.
- The three zeros are **provider coverage**, not empty cells from a book that declined to post.

## Additional Odds API NFL books we are **not** pulling (report only — Ryan decides)

**us:** `betonlineag`, `betus`, `bovada`, `williamhill_us` (Caesars, paid), `lowvig`, `mybookieag`  
**us2:** `ballybet`, `betparx`, `espnbet`, `fliff`, `rebet`  
**eu:** `pinnacle`  
**us_ex:** `novig`, `prophetx`, `kalshi`, `polymarket`, `betopenly`

Do not add these in this change.
