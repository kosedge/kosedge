# CFB truth audit + soft-launch status

Date: 2026-08-12  
Branch: `feat/cfb-truth-audit` → `deploy-vercel`  
Doctrine: Same poster process as NFL. Audit before features. Honest empty > fake KEI.  
Prod: `www.kosedge.com` (checked 2026-08-12 ~16:30 ET)

## Verdict

**Not soft-launch quality yet.** CFB has a usable **MODEL** research desk (Season Model + Project Game) and a **markets-only** Edge Board. There is **no KEI handicap**, no PLAY/LEAN tags, no conserved futures/wins table, and no PRESEASON/MODEL/LIVE truth badges. That is an honest preseason desk — not a launch-grade betting board.

This PR fixes only P0 falsehoods found on prod (literal `{status.*}` roster line; nav/hub copy that branded CFB Fair Lines / empty KEI tables as if a handicap existed). No new model layers.

---

## LIVE vs MODEL vs missing

| Surface | State | Evidence (prod 2026-08-12) |
|---------|--------|----------------------------|
| `/pro/cfb/model` | **MODEL** | Engine `cfb-season-engine-v0.9-inseason` · mode `packaged_real_roster` · 130 teams · 780 densified sample games · roster `packaged_espn_roster_2026` as_of **2026-08-04**. Badge was “CFB tracking”, not PRESEASON/MODEL. |
| `/pro/cfb/project-game` | **MODEL** | 200. Team-level spread / total / WP→ML, Off/Def drivers, early-season uncertainty (W1–W4). Approximate calibration. Edge Board explicitly left markets-only. |
| `/edge-board/cfb` | **LIVE markets** (books) / **no KEI** | Header “Markets only”; copy: KEI columns stay blank. ~222 spread rows; fallback snapshot `capturedAt 2026-07-31` with Week-0/1 kickoffs (e.g. 08/29). No Week 18. No invented tags. |
| `/pro/cfb/fair-lines` | **missing KEI** (honest shell) | Pending board; `resolveKeiGames("cfb")` returns `[]`. No `kei_lines_cfb.json`. |
| `/pro/kei-lines/cfb` | **missing KEI** | Empty table. Prod copy told operators to generate `kei_lines_*.json` — that would be fake KEI. Fixed this PR. |
| Season wins / futures | **missing** | No CFB futures hub. Season-sim API exists (`n_sims` default 15, cap 200) on a **780-game densified sample**, not an official FBS slate. **No NFL 272 assumption** in CFB code. Σ wins for this pack would be 780, not 272. |
| Labels | **gap** | No finished future week labeled “current”. Also no shared PRESEASON/MODEL/LIVE helper (NFL has `nfl-truth-label.ts`; CFB does not). Project Game week picker is just “Week 1”…“Week 15”. |
| Roster / Arch Manning | **MODEL, still valid** | Snapshot as_of **2026-08-04** (`cfb_real_roster_snapshot_2026.json`). Texas QB1 = **Arch Manning**. Coverage 133/134 named QBs; unmatched codes `FAY`, `SOUTH`. Notes: camp battles unresolved; returning snap% is class-year proxy. 8 days stale — not a different QB era. |

`GET /api/cfb/season-engine/status` (via www):

- `engine_version`: `cfb-season-engine-v0.9-inseason`
- `schedule_source`: `packaged_sample_densified` · **780** games · **130** teams
- `roster_as_of` / `as_of`: `2026-08-04`
- Fidelity: `espn_named_qb` 127 · `approximate_curated` 128 · `placeholder_fbs` 2
- Status probe defaults `demo=true` on the CFB route, which here means **packaged universe**, not a fake round-robin. Mode string is `packaged_real_roster`.

---

## KEI status

**None. By design.**

- `sportIsMarketsOnlyEdgeBoard("cfb")` is true.
- `resolveKeiGames("cfb")` always `[]`.
- Edge Board must not invent handicap, Model-vs-KEI split, or PLAY/LEAN.
- Project Game numbers are **research MODEL** lines, not KEI. They must not be copied onto the Edge Board as KEICFB.

P0 copy bugs on prod (fixed here):

1. Season Model roster line rendered literal `depth {status.depth_source}` / `portal {status.portal_source}` (missing `$` in template).
2. Primary nav labeled `/pro/cfb/fair-lines` as **KEI Lines** even though no handicap exists.
3. Hub footer Edge Board card (source) claimed “Open vs best prices with KEI and directional edge tags.”
4. Empty `/pro/kei-lines/cfb` invited a pipeline export of invented `kei_lines_cfb.json`.

---

## Top 5 gaps (trust impact)

1. **No CFB truth-state badges** — MODEL desks can be read as live/current. NFL already has PRESEASON/MODEL/LIVE. Highest trust fix after this audit.
2. **No KEI / no tag policy** — Edge Board cannot support PLAY/LEAN. Soft-launch betting desk is blocked until a real handicap exists (do not stub).
3. **Densified 780-game sample ≠ official FBS schedule** — season paths, SOS, and any future wins table would be approximate. Conservation must use FBS game count (~780 here), never NFL 272.
4. **Roster as-of 2026-08-04 + proxy returning/portal-out** — Arch Manning smoke still holds; camp/depth will drift before Week 0 (08/29).
5. **Two unjoined truths** — Project Game (MODEL) vs Edge Board (books only). Joining them without KEI would be fake edge.

---

## P0 fixes in this PR

- Interpolate CFB model roster depth/portal strings.
- Markets-only sports (CFB, NHL): primary nav **Fair Lines**, tools **KEI (not shipped)**.
- CFB hub footer + overview KEI hint: honest empty, no tag/KEI advertising.
- CFB/NHL KEI table empty copy: do not instruct inventing `kei_lines_*.json`.

## Recommended next PR (only)

**`feat/cfb-truth-labels`** — port the NFL truth-label contract to CFB Season Model + Project Game (PRESEASON until Week 0/1 kickoff; MODEL on engine numbers; never LIVE without a real week). No KEI, no schedule rewrite, no new layers.

---

## Soft-launch bar (not met)

| Bar | CFB now |
|-----|---------|
| Honest empty > fake KEI | Yes (board); nav/copy P0s fixed this PR |
| Truth labels on research desks | No |
| KEI vs market tags | No |
| Conserved season wins / futures | No |
| Official schedule + fresh roster | Packaged densified + 2026-08-04 ESPN |

Use CFB as a **MODEL + markets** preview. Do not sell it as a KEI desk.
