# NFL Pre-P0 Firm-Up — 2026-08-21

Branch: `feat/nfl-prep0-firmup` → `deploy-vercel`

Product integrity before Canonical Schedule P0 and the 100k resim. No schedule rewrite. No 100k in this PR.

## 1. Essay strip

| Surface | Before | After |
|---------|--------|--------|
| Power Ratings | Method blurb, Bayesian shrinkage wall, Ryan Adj policy / Tuesday job | Engine/version strip + Model transparency (`#power-ratings`) |
| Survivor planner | Path SOS / parlay / intrinsic PR essay | “Lock one team per week…” |
| Survivor helper | Blend / SOS / PR essay | Used teams + week + remaining picks |
| True PR (`/pro/nfl/model`) | SOS / Week-1 cliff / Edge vs KEI paragraph | One-line + hub (`#game-boxes`) |
| Awards | “Methodology” wall (Award Score math) | One-line index honesty + hub |
| Fantasy Methods accordion | 7-bullet LIMITATIONS_BASE | One-line + hub (`#fantasy`) |

Canonical copy stays on `/pro/model-transparency`. Boards do not fork new essays.

## 2. Edge Board opens

**Inventory (live fair-lines, 2026-08-21):** 16 REG Week 1 games on the board (no silent game drop). Open from first `odds_snapshots` capture.

| Game | Before Open spread / total | After | Reason |
|------|----------------------------|-------|--------|
| ARI@LAC | −10.5 / 46.5 | keep | exact UUID snapshot |
| ATL@PIT | −3.0 / 41.5 | keep | exact UUID snapshot |
| BAL@IND | 3.5 / 48.5 | keep | exact UUID snapshot |
| BUF@HOU | 1.5 / 44.5 | keep | exact UUID snapshot |
| CHI@CAR | 2.5 / 45.5 | keep | exact UUID snapshot |
| CLE@JAX | −7.5 / 40.5 | keep | exact UUID snapshot |
| **DAL@NYG** | **— / —** | alias join (same-date home/away) | parallel Odds `games` UUID — same class as market-blend fallback |
| **DEN@KC** | **— / —** | alias join | same |
| GB@MIN | −1.5 / 45.5 | keep | exact UUID snapshot |
| MIA@LV | −3.5 / 40.5 | keep | exact UUID snapshot |
| **NE@SEA** | **— / —** | alias join | same |
| NO@DET | −7.0 / 49.5 | keep | exact UUID snapshot |
| NYJ@TEN | −2.5 / 38.5 | keep | exact UUID snapshot |
| **SF@LAR** | **— / —** | alias join | same + LA↔LAR |
| TB@CIN | −3.5 / 52.5 | keep | exact UUID snapshot |
| WAS@PHI | −4.5 / 47.5 | keep | exact UUID snapshot |

Root cause: `_first_open_odds_by_game_ids` was **exact schedule UUID only**. Consensus market already had a team/date fallback; Open did not. Fair-lines now remaps earliest snapshot from schedule UUID ∪ same-date home/away (LA↔LAR, WSH↔WAS) onto the schedule `game_id`. `open_join_status`: `exact` / `alias` / `missing`.

Do **not** invent `open = current`. True no-book stays `—`. Game membership still padded from the schedule pack.

**Note:** This live pull also had Odds API unauthorized, so **Current** was unjoined (`market_joined=false`) for every W1 row. That is a secrets/feed issue, not an Open join-key bug. Opens that were present came from existing Postgres snapshots.

Confirm the four alias games after Railway deploys this model-service change. If a matchup still has `open_join_status=missing`, there is no snapshot to restore.

## 3. Fantasy draft board

- Nav chip **Rankings → Model rank**. Default `/pro/nfl/fantasy` tab is **Value** (ADP + Value Δ), not model-only order.
- Columns: Model, ADP, Value Δ, **Advice** (Wait / Reach / Fair from `deskDraftAdvice`), Floor/Med/Ceil.
- ADP source + freshness stay in the hero (FantasyPros; unmatched = —).
- Builder + Mock still use `value-aware-recs` (need + pick). Desk advice is pick-agnostic and does not claim an optimal pick.
- Methods accordion stripped.

## 4. K/DST hooks

| Piece | Status |
|-------|--------|
| Module `nfl_kicker_dst_projections` | Unchanged scoring |
| Table `nfl_fantasy_season_draft_rankings` | Load path; Fantasy `hasKd` lights filters/mock when K/DST rows exist |
| `src/services/nfl_kdst_publish.py` | **New.** `load_kdst_publish_artifact(season)` → None until `data/ops/artifacts/nfl-kdst-season-{season}.json` (or `NFL_KDST_PUBLISH_PATH`) |
| Materialize | Returns `kdst_publish` status; kicker volume overlay when artifact has `fg_attempts` |
| `kicker_layer` | Documents the same publish hook (ST/boxes stay approximate until artifact) |
| Desk copy | Points at draft-rankings table + module — honest empty, no fake K/DST |

100k brief can write the artifact and remat; no second Fantasy architecture pass.

## Smoke

| # | Check |
|---|--------|
| 1 | Power + Survivor: no long model essay; hub link |
| 2 | Edge Board: opens table above; 16 W1 games; no silent drops |
| 3 | Fantasy: ADP + Value Δ visible; default Value tab |
| 4 | Wait/Take (Advice) on desk + Builder/Mock |
| 5 | K/DST honest empty; publish hook ready |
| 6 | `/pro/model-transparency` still resolves |

## Non-goals (held)

Canonical kickoff rewrite, full 100k, nav redesign, fake K/DST or fake ADP.
