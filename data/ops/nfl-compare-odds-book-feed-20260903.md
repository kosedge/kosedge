# NFL Compare Odds — Odds API book feed honesty (2026-09-03)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Scope:** designated Compare Odds books vs what The Odds API actually carries for NFL.  
**Out of scope:** remat, KEI mint, hide, paywall, adding non-designated books.

## Locked designated set (Ryan — keep all twelve columns)

`draftkings, fanduel, betmgm, betrivers, hardrockbet, fanatics, bovada, williamhill_us, betonlineag, bet365, circa, betr`

Display aliases: `williamhill_us` → **Caesars**; `betonlineag` → **BetOnline**.

Not `market` / `keinfl` (those are display aliases, not Odds API keys).

**No theScore** — not in designated, carried, or request sets (any spelling / `espnbet`).

## Carried vs not-carried (NFL)

**Carried (9 — requested from feed):**  
`draftkings, fanduel, betmgm, betrivers, hardrockbet, fanatics, bovada, williamhill_us, betonlineag`

**Honest not-carried (3 — column only, never requested):**  
`bet365, circa, betr`

| Key | Region | NFL on feed? | Notes |
| --- | --- | --- | --- |
| `draftkings` | `us` | **yes** | |
| `fanduel` | `us` | **yes** | |
| `betmgm` | `us` | **yes** | |
| `betrivers` | `us` | **yes** | |
| `hardrockbet` | `us2` | **yes** | Requires `regions=us,us2` (or explicit `bookmakers=`) |
| `fanatics` | `us` | **yes** | Paid-tier key |
| `bovada` | `us` | **yes** | |
| `williamhill_us` | `us` | **yes** | Caesars; paid-tier key |
| `betonlineag` | `us` | **yes** | BetOnline |
| `bet365` | — | **no** | No US key. Only `bet365_au` (`au`, paid; AFL/NRL h2h/spreads/totals). Not usable for NFL. |
| `circa` | — | **no** | Circa Sports is **not** on The Odds API in any region. |
| `betr` | — | **no** | No US key. Only `betr_au` (`au`). |

**Request path:** pull only the nine carried keys so we never invent lines and never risk `INVALID_BOOKMAKERS` on dead keys.  
**UI path:** keep all twelve designated columns; the three not-carried read as **not carried by the feed**, not as “book has no number.”

## Regions audit

**Regions string sent for NFL:** `us,us2`

All nine carried keys resolve under `us` or `us2` per [The Odds API bookmakers by region](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html) (CoS verified 2026-09-03). No extra region required for `bovada`, `williamhill_us`, or `betonlineag`.

| Path | Value |
| --- | --- |
| `apps/web/lib/odds-api.ts` (`fetchEdgeBoard` / `fetchOddsComparison`) | `us,us2` |
| `nfl_fair_lines` | `us,us2` |
| `_fetch_live_nfl_market_lines_by_abbr` | `us,us2` |
| `pull_odds_snapshot` (NFL sport) | `us,us2` |
| `nfl_edges_today` | `us,us2` |

`hardrockbet` lives in `us2`; `fanatics` and `williamhill_us` are paid `us`. Bookmakers param still takes priority when set, but regions must include `us2` wherever we rely on region scoping.

## Street / Best Line

- **Best Line / Best O/U / Best ML** = best number across every **carried** book that posted (juice tiebreak; fresher `last_update` breaks remaining ties). Never DK-locked.
- **Open** = preferred-book current among posted carried books (DK → FD → …). That is open preference, not best.
- **PLAY stake close** remains DK → FD → consensus (grading a bettable DK/FD print). Shop column stays Best. No PLAY chrome ungated here.
- Do **not** invent lines for not-carried books.

## Occupancy note (live 2026-09-03)

DK **272** vs FD **32** / Fanatics **18** / BetRivers **17** / MGM **16** / Hard Rock **16** / bet365·circa·betr **0**:

- **272** = full NFL regular-season game count. DK is posting the season-long slate; other books are only printing the near-term (≈ Week 1 / next ~2 weeks) board. Honest market behavior — not a request bug.
- The three not-carried zeros are **provider coverage**, not empty cells from a book that declined to post.

## Additional Odds API NFL books we are **not** pulling (report only)

**us:** `betus`, `lowvig`, `mybookieag`  
**us2:** `ballybet`, `betparx`, `espnbet`, `fliff`, `rebet`  
**eu:** `pinnacle`  
**us_ex:** `novig`, `prophetx`, `kalshi`, `polymarket`, `betopenly`

Do not add these unless Ryan designates them.
