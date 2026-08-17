# NFL Week-1 readiness — 2026-08-17

Branch: `feat/nfl-week1-readiness` → `deploy-vercel`  
Kickoff: Wed Sep 9, 2026. Doctrine unchanged: Model = research fair. KEI = model + desk factors. Tag = KEI vs market only.

## Root cause — `/pro/nfl/weekly-slate` 404

No App Router page existed. The live desk home is `/pro/nfl/slate/today` (Overview CTA and primary nav already pointed there). Bookmarks / typed `/pro/nfl/weekly-slate` 404’d.

**Fix:** edge redirect + `app/(pro)/pro/nfl/weekly-slate/page.tsx` → `/pro/nfl/slate/today`.

## Depth before / after (key teams)

Pack: `nfl_depth_chart_2026_w1.json` · `as_of 2026-08-13` · snapshot `nfl-depth-2026-w1-20260813T120000Z`  
Camp check Aug 17: O’Connell named Murray MIN QB1 on Aug 11. Pack already matched. No identity rewrite.

| Team | Before (pack 8/13) | After (this pass) | Notes |
|------|--------------------|-------------------|--------|
| MIN QB1 | Kyler Murray | **unchanged** | Named 8/11. Preview copy was still “competing in camp” — **copy fixed**. |
| ARI QB1 | Jacoby Brissett | **unchanged** | Kyler is MIN. Preview now says that explicitly. |
| WAS QB1 | Jayden Daniels (active) | unchanged | Healthy 1st-team as of 8/09. |
| WAS OL | Tunsil OUT · Allegretti OUT | unchanged | Coleman/Wylie LT; Good-Jones C. Packaged, not live. |
| ATL QB | Tua 1 / Penix 2 (open) | unchanged | Dual unresolved — labeled. |
| CLE QB | Watson 1 / Sanders 2 (open) | unchanged | Monken has not named a starter. |
| MIA QB1 | Malik Willis | unchanged | Tua is ATL. |
| All 32 | Named QB1 | Named QB1 | 32/32 skill-starter teams. |

`injury_paths[]` is empty. Current = packaged. Boards must not claim a live injury feed.

## Injury → current path (manual v1)

| Gate | What happens | What does **not** happen |
|------|----------------|--------------------------|
| Midweek report | Beat + desk notes → `injury_status` / `ol_roles` on the pack | Model gut-edit |
| Friday final | Lock W1 named starters. If a QB1/skill1 is OUT, add `injury_paths[]` with a week window and republish pack | Invented IR length |
| Gameday inactives | Apply inactives to **current** depth. KEI may reprice (`injury_net`, QB backup drop-off) | Model rewrite; fake PLAY volume |

Republish season-engine / power only if a SoT identity move changes ratings. Version strip stays engine · paths · as_of. Weeks 0–2 remain prior-heavy (no Week-1 cliff).

Banner on Edge Board + season-engine desks: **Depth as_of 2026-08-13 — not live injury feed.**

## Edge Board honesty (W1)

- Default slate = Week 1 REG. PRE off the default board.
- Tag = KEI vs best market. PASS under threshold.
- Model ≠ KEI when desk factors apply; identity when none.
- Open missing → show — ; do not block current-line edges.
- Weather / rest / short week / travel / ref / QB / inactives: label when not in stack. Never invent.

Live www smoke 2026-08-17 (`/edge-board/nfl`, Week 1 tab, 16 REG, PRE=0). Open `$undefined` renders as — (not invented). All 16 tags PASS (under W1 threshold — honest, not forced PLAY).

| Game | Model | KEI | Market (best) | Open | Tag |
|------|-------|-----|---------------|------|-----|
| NE @ SEA | −4.5 | −4.2 | +4 | — | PASS |
| SF @ LAR (Melbourne) | −4.3 | −3.8 | +3.5 | — | PASS |
| ARI @ LAC | −7.1 | −9.0 | +10.5 | +10.5 | PASS |

Model ≠ KEI on the sample (desk factors applied). Tag = KEI vs best market.

## Smoke table

| URL | Expect | Pass |
|-----|--------|------|
| `/pro/nfl/overview` → Weekly Slate CTA | 200 W1 matchups | **PASS** (www 200; CTA already `/pro/nfl/slate/today`) |
| `/pro/nfl/weekly-slate` | 307 → `/pro/nfl/slate/today` | **SHIP** (www still 404 until this PR; alias added) |
| `/pro/nfl/slate/today` | Week 1 content | **PASS** (www 200) |
| `/edge-board/nfl` | 16 W1 games; depth as_of banner; PRE off | **PASS** games/PRE (www 16 REG, PRE=0). Banner ships this PR. |
| `/pro/nfl/fantasy` | Brissett ARI / Murray MIN; preseason-fallback honesty | **PASS** SoT (pack+CSV). Banner + preview copy this PR. |
| `/pro/nfl/previews` MIN | Named starter, not camp competition | **SHIP** this PR |

## KEI factor stack (P1 — confirmed, not invented)

Wired in `nfl_kei_week1_reprice.py`. Web driver line now also labels engine names (`qb_confirmation`, `qb_backup_dropoff`).

| Factor | Behavior |
|--------|----------|
| QB confirmed / backup drop-off | Applied from pack SoT. Open competition = confidence only, no crown. |
| Rest / short week | Short week not applied on W1 (no prior REG). |
| Travel | Cross-country TZ applied. SF–LAR Melbourne is **labeled** “international travel not in stack” — no invented long-haul tax (same-coast TZ would have been silent). |
| Weather | Outdoor totals/pass tax only with a real forecast. Indoor → “not applied”. Never climatology. |
| Injury / inactives | Pack statuses only. Empty `injury_paths[]` → current = packaged. |
| Refs | Apply only from a Week 1 crew pack. Empty → “ref not applied”. |

## Residual P1

- Live injury API (none — process + labels only).
- Outdoor weather / Melbourne travel chips when real obs exist — do not invent.
- CLE / ATL open QB still labeled, not crowned.
- Full 32-preview refresh beyond MIN/ARI.
- K/DST stay omitted until real projections exist.
- Season-engine republish only if a later SoT identity move changes ratings. Weeks 0–2 stay prior-heavy.

## Confirm

- Model untouched as research fair.
- Edge / Tag still KEI vs market only.
- No invented injuries, depth, or PLAY volume.
