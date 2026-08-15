# CFB Open-Ingest Scaffold + Diagnostic Join Readiness

**Date:** 2026-08-14 (live pull 2026-08-15)  
**Branch:** `feat/cfb-open-ingest-scaffold` → `deploy-vercel` (stacked on #233–#241)  
**Ingest id:** `cfb-open-ingest-v0.15.1-20260814`  
**Doctrine:** Model stays pure research fair. `used_in_spread` stays **false**. No KEI. No Edge tags. No rank=market. When opens exist, we join and diagnose — we do not auto-blend into a published line.

This pass is the **pipe and join**, not the handicap product.

---

## How to pull Week 0–2

Sport key: **`americanfootball_ncaaf`** (The Odds API).  
Markets: `spreads,totals,h2h`. **No props.**  
Secrets: existing `ODDS_API_KEY` / `ODDS_API_KEY_BACKUP` env (or `apps/web/.env.local`). Never commit keys.

```bash
# on-demand (default weeks 0–2)
python scripts/cfb/pull_cfb_game_odds.py --weeks 0-2

# same via dispatcher
python scripts/cfb/cfb pull-opens --weeks 0-2

# re-map a saved snapshot (no API credits)
python scripts/cfb/pull_cfb_game_odds.py --weeks 0-2 --replay path/to/snapshots.json

# latest inventory
python scripts/cfb/cfb inventory
```

Optional scheduled hook (document only — not enabled this pass):

```cron
# once books post Week 0 lines; daily is enough
0 14 * * * cd /path/to/kosedge && python scripts/cfb/pull_cfb_game_odds.py --weeks 0-2
```

Writes (not Railway Postgres):

| Path | What |
| --- | --- |
| `/Volumes/KosEdgeData/clean/odds/cfb/live/` | HD lake when mounted |
| `data/cfb/warehouse/clean/odds_cfb/live/` | gitignored repo fallback |
| `live/snapshots/{pulled_at}.json` | raw Odds API events |
| `live/mapped/{pulled_at}.jsonl` | flattened book × market + slate keys |
| `live/inventory.json` | latest counts |
| `live/attempts.jsonl` | every attempt, including honest empties |

Snapshot key: `pulled_at|book|odds_event_id|market`. Re-running the same `pulled_at` is a no-op.

Unmatched events (FCS, unknown Odds API name, no slate pair) are **logged, not forced**.

---

## Join command

```bash
python scripts/cfb/cfb diagnostic 2026
# equivalent
python scripts/cfb/run_market_diagnostic.py --season 2026
```

- **n=0** → `{ "status": "insufficient_market_rows", "n_opens": 0, "n_closes": 0 }` — exit 0, no invented ATS/MAE.
- **n>0** → same hist slices (week band, \|line\|, home/favorite, conference tier). Still `used_in_spread=false`, `kei=false`, `blend=false`.

Upcoming snaps count as **opens**, not closes. Close = last snap strictly before kickoff.

---

## Current inventory (one real pull)

**Live pull:** 2026-08-15T12:23:47Z · source `the-odds-api` · key remaining ~4.98M  
Committed copy: `data/ops/cfb-open-ingest-inventory-20260814.json`

| Field | Value |
| --- | ---: |
| n_events | 111 |
| n_matched_events | 62 |
| n_unmatched_events | 49 |
| **match_rate** | **55.9%** |
| **n_opens** | **55** |
| **n_closes** | **0** |
| Week 0 / 1 / 2 games with a snap | 6 / 43 / 6 |

Unmatched are almost all **FCS vs FBS** (Albany, Furman, Maine, …). Those stay unmatched — not forced onto an engine code. Two FBS Odds API aliases added on replay (`Sam Houston State`, `Southern Mississippi`).

`cfb diagnostic 2026` after the pull: **`status=ok`**. vs open n=55, mean **+6.35**, MAE **9.40**. vs close n=0 (no kickoffs yet). Thin. Same cold / short-favorite shape as hist — **not a KEI publish**.

---

## Product honesty (unchanged)

- Edge Board CFB remains **markets-only**. KEI / Edge / Tag columns stay blank.
- Model pages: research fair only.
- `used_in_spread` remains false on all model writes.
- No training on 2026 opens this pass.
- No silent fill of missing opens with hist averages.

---

## Ready for KEI design when…

All of these must be true. Not “when the board looks empty.” **Not true yet.**

1. **Week 0–2 opens exist** — `n_opens` covers a usable FBS–FBS slice. **Met (55).**
2. **Join match rate is inspectable** — unmatched logged; no forced slate keys. **Met (55.9%; FCS leftover).**
3. **`cfb diagnostic 2026` returns `status=ok`** with the same slices as hist. **Met for vs-open.** vs-close still empty.
4. **Held-out diagnostic clears** — live 2026 join does not contradict the hist “cold / short-favorite” read in a way we paper over. Thin n stays flagged. **Not met.** vs-open MAE 9.4 / mean +6.4 is the same short-favorite story. Do not design KEI to erase it.
5. **Closes exist for a later gate** — KEI design may start from opens; publish still waits on a close/holdout story. Close ≠ lock until densify is honest. **Not met (`n_closes=0`).**
6. **`used_in_spread` is still false** until a later explicit flip. No PLAY/LEAN. No Edge Board CFB population from this pipe. **Still false.**

Until 4–5 clear: ingest + diagnose only.

---

## Blockers

- **Closes:** Week 0 kickoff window starts **2026-08-29**. `n_closes` stays 0 until then.
- **FCS coverage:** Odds API `americanfootball_ncaaf` includes FCS; match rate ~56% is expected, not a key bug.
- **API plan:** sport key works; credits remaining were high on this key. Not a blocker.
- **Books:** DK/FD/MGM and others stored; open/close reduction still prefers DK then FD.
- **KEI:** not a blocker — a non-goal. Pipe is ready; the line is not earned.
