# CFB totals-guard real-roster holdout — STOP blocker (20260903)

**Branch:** `cursor/cfb-totals-guard-real-roster-blocker-09cd` → `deploy-vercel`  
**Verdict:** **STOP** — 2023–24 real roster/SP+ (live-style units/QB) is **not reconstructable**. No real-roster unused-2025 table. No fake numbers. No mix.  
**Product change:** none. Flag **OFF**. Identity `kei_total = model_total` stays live. No `apply_cfb_kei`. No pack remat. No W1 λ retune. PLAY stays sat.  
**Prior proxy harness (not this path):** `data/ops/cfb-totals-guard-holdout-20260903.md` (PR #442) — hist-cal league-avg roster/QB.  
**Design SoT:** `docs/CFB_KEI_CALIBRATOR_DESIGN.md` (merged `9ee285f9`).  
**Artifacts:** `data/ops/cfb-totals-guard-real-roster-holdout-blocker-20260903/`

## Why this STOP exists

Ryan/CoS GO asked for unused **2025** totals-guard eval on **REAL roster/SP+** (live-style units/QB), not the hist-cal league-avg proxy — because matchup inflation must exist in the eval or (b) is theater.

Hard locks that force STOP when fit years cannot share that path:

1. **Fit and eval must share the SAME roster path.**
2. Fit on **2023–24 real-roster** if reconstructable; eval unused **2025 real-roster**.
3. **Do NOT mix proxy-fit λ=0.54 onto a real-roster eval.**
4. If 2023–24 real roster/SP+ is **not reconstructable: STOP and report.** Do not invent a mix. Do not retune from 2025.
5. No KEI wire. No W1 λ retune. No this-week pack recut. No CLV mint. PLAY stays sat. No global `MATCHUP_RESPONSE` cut. Don’t round 1.056→1.0. Don’t use W0–4 to un-RED W0–2.

## Exists vs missing (evidence)

### What exists (repo / live 2026)

| Artifact | Role | Years |
| --- | --- | ---: |
| `cfb_real_roster_snapshot_2026.json` | ESPN roster + depth/QB/units/portal heuristics | **2026 only** |
| `cfb_efficiency_snapshot_2025_carry_2026.json` | Final-2025 SP+ → 2026 preseason carry | **2025→2026 only** |
| `scripts/cfb/package_real_roster_2026.py` | Packager hardcoded to 2026 ESPN site roster | 2026 |
| `scripts/cfb/package_efficiency_2025_carry.py` | Public cfbupdate SP+ (current) / optional CFBD | 2025→2026 |
| Hist-cal proxy (`historical_calibration.py`) | Prior-year `cfb_ratings` adj EPA + **league-avg** roster/QB/units | 2022–2025 graded |
| Warehouse v1 | Games, closes, odds lake, PBP | 2020–2025 games; **no historical rosters** |
| Proxy totals-guard holdout (PR #442) | Identity vs (b)/(a) on unused 2025 | league-avg path |

Live 2026 compose path (status / project-game): **prior-year SP+ + ESPN roster + QB + units**. That is the honesty bar for “real-roster” here.

### What is missing (required for same-path fit 2023–24 + eval 2025)

| Required pack | Status |
| --- | --- |
| `cfb_real_roster_snapshot_2023.json` (pre-W0 units/QB) | **Missing** |
| `cfb_real_roster_snapshot_2024.json` | **Missing** |
| `cfb_real_roster_snapshot_2025.json` | **Missing** |
| `cfb_efficiency_snapshot_2022_carry_2023.json` (final-2022 SP+) | **Missing** |
| `cfb_efficiency_snapshot_2023_carry_2024.json` | **Missing** |
| `cfb_efficiency_snapshot_2024_carry_2025.json` | **Missing** |
| Warehouse historical roster materialization | Explicitly **not done** (ops 2026-08-12) |
| CFBD key in this environment | **Unset** (`/ratings/sp?year=` → 401) |

### Investigation notes (non-binding probes)

| Probe | Result |
| --- | --- |
| Hist-cal ops (2026-08-05) | Already stated: seasons 2022–2025 **do not** have packaged historical roster/QB snapshots; league-avg proxy used. |
| Warehouse known gaps | “**Historical rosters** (`load_cfb_rosters`) not materialized this pass — identity is ESPN maps + packaged aliases.” |
| Warehouse walk-forward | Historical seasons use **program EPA prior**; “The 2026 roster/QB pack is not applied to 2020–25.” |
| ESPN site roster `?season=2023..2025` | HTTP 200 but **0 athletes** (current-season endpoint only). |
| ESPN core `seasons/{Y}/teams/{id}/athletes` | Athlete **$ref lists** exist for 2023–2025 (position/experience resolvable). **Not** a packaged live-style snapshot; no portal/returning/recruiting packager; no Week-0 freeze; not wired into season-engine. |
| Public SP+ (`cfbupdate.com/sp-ratings`) | Serves **2026** rankings only; `/sp-ratings/2024` etc. **404**. |
| ESPN SP+ story pages | 2025 story has HTML; 2024 story has **no** scrapable `<tr>` table in this environment. Neither is a packaged multi-year SP+ archive in-repo. |
| CFBD `ratings/sp?year=` | Would be a reconstruct path **if** keyed; **401 without key**. Not inventing a substitute. |
| In-repo SP+/roster packs | Only `…_2026` roster + `…_2025_carry_2026` efficiency. |

**Conclusion:** Raw ESPN core athlete refs are a **future packaging research lead**, not a reconstructable live-style units/QB+SP+ path for fit 2023–24 today. SP+ archives for 2022–2024 finals are absent without CFBD (or a committed multi-year pack). Building an invented hybrid (core athletes + `cfb_ratings` / league-avg / 2026 overlay) would violate the same-path lock.

## What we refuse to do

- Mix **proxy-fit λ≈0.54** (PR #442) onto a real-roster eval.
- Fit coefficients on unused **2025**.
- Use W0–4 to un-RED W0–2.
- Round proxy (b) mean gap 1.0558 → 1.0.
- Wire `apply_cfb_kei` / turn any totals-guard flag on.
- Mint CLV.
- Unsat PLAY.
- Cut global `MATCHUP_RESPONSE`.
- Publish a fake real-roster GREEN/RED table.

## Proxy path status (context only — not promoted)

PR #442 unused 2025 W0–2 on **league-avg** path: (b) **not** all-GREEN (`abs(mean)` bar fails at ~1.056); (a) GREENS level/MAE/direction on that proxy join. Honesty note from that run still stands: proxy understates live 2026 Over-drunk. This STOP does **not** re-grade those numbers on a different roster path.

## Unblock (future; out of scope here)

All of the following must land **before** a real-roster twin holdout is honest:

1. Packaged **Week-0 (or preseason) real-roster** snapshots for **2023, 2024, and 2025** with the same unit/QB fields live compose reads (or a documented equivalent packager + tests).
2. Packaged **prior-year SP+** carries: 2022→2023, 2023→2024, 2024→2025 (CFBD multi-year or committed public archives — not `cfb_ratings` league-avg identity).
3. Twin harness: fit **only** 2023–24 on that path; eval unused 2025; §4 W0–2 primary; identity vs (b) vs (a); (c) exploratory only.
4. If (b) GREENS §4 → STOP/report again — still no `apply_cfb_kei` until a separate enable decision.

## Harness / tests shipped with this STOP

| Path | Role |
| --- | --- |
| `scripts/cfb/run_totals_guard_real_roster_holdout.py` | Closed-door runner: asserts reconstructability; exits **2** with blocker JSON (no eval numbers). |
| `…/totals_guard_real_roster.py` | Same-path + pack inventory helpers. |
| `tests/test_cfb_totals_guard_real_roster_blocker.py` | No year leakage; refuse proxy→real mix; reconstructability false today. |

## CoS one-liner

**STOP: 2023–24 live-style roster/SP+ not reconstructable (only 2026 roster + 2025→2026 SP+ pack; warehouse has no hist rosters; CFBD SP+ keyed/absent). No mixed proxy-λ real-roster eval; flag OFF; identity stays live; no apply_cfb_kei.**
