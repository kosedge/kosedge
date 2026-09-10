# CFB Week 2 house path (A→B→C)

**Date:** 2026-09-10  
**Base:** `deploy-vercel`  
**Draft PR only** — CoS AUTHORIZED A→B→C; Ryan merge later after Product+Riley.  
**No Odds API pulls. No HIST. No hand-minted KEI.**

## A — Honest week param (SHIP FIRST)

- `?week=2` no longer coerces to Week 1 Research.
- Parser: integer ≥ 0 when present and finite; default **1** when missing/invalid.
- Empty requested week → empty board + `requestedWeek` / `week0Count` / `week1Count` / `week2Count`. Never fall through to W1.
- Edge Board tabs include Week 2. Official slate `parseOfficialSlateWeek("2")` stays 2.

## B — Official slate through W2

| Field | Value |
|-------|--------|
| Generator | `scripts/cfb/publish_official_slate_2026.py` (`WEEKS=(0,1,2)`) |
| Schedule SoT | `cfb_official_schedule_2026.json` |
| **as_of** | `2026-08-31` (engine schedule pack — not wall clock) |
| **slate_version** | `cfb-official-slate-v2-dual-20260831` |
| Weeks | 0, 1, 2 |
| n_games | 183 (8 + 89 + 86) |
| n_w2 / FBS–FBS | 86 / 47 |
| Odds API | **not pulled** (no credit burn) |
| W0/W1 factcheck | carried forward by `game_id` (51 agree preserved) |
| W2 status | `unconfirmed_secondary` (ESPN primary only) |

Artifacts: `apps/web/lib/data/cfb-official-slate-2026.json` + model-service mirror.

Refresh (local/ops, still no key unless desk authorizes a pull):

```bash
env -u ODDS_API_KEY -u ODDS_API_KEY_BACKUP python3 scripts/cfb/publish_official_slate_2026.py
```

## C — KEI W2 via builder only

| Field | Value |
|-------|--------|
| Builder | `scripts/cfb/build_cfb_kei_futures_2026.py --kei-only` |
| Path | `apply_cfb_kei` / `project_game_preview` (no hand-mint) |
| Pack file | `apps/web/lib/data/cfb-kei-w0-w1-2026.json` (name kept; `weeks` is `[0,1,2]`) |
| **as_of** | `2026-08-31` (`CFB_CLOSE_AS_OF` default — same close vintage) |
| **generated_at** | `2026-09-10T13:21:20Z` (builder clock, not invented) |
| **kei_version** | `cfb-kei-v1.0-2026w0` |
| **engine_version** | `cfb-season-engine-v0.15-power-sot` |
| n_fbs_with_kei | 96 (W0=6, W1=43, W2=47) |
| Futures | not regenerated (`--kei-only`) |

```bash
env -u ODDS_API_KEY -u ODDS_API_KEY_BACKUP python3 scripts/cfb/build_cfb_kei_futures_2026.py --kei-only
```

Fail closed: `findCfbKeiGame(home, away, week)` requires week match. Missing W2 KEI → empty house fields, not W1 recycle.

## Gate checklist

- [ ] A: `week=2` does not return week-1-stamped games
- [ ] B: official slate `weeks` includes 2; `gamesForWeek(..., 2)` nonempty
- [ ] C: pack `weeks` includes 2; W2 FBS KEI from builder
- [ ] Draft PR only — do not merge
