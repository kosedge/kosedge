# NFL Camp Desk — daily cadence + writer SOP (2026-08-21)

> **LOCKED addendum (2026-08-30 — Ryan):** Living cadence SoT is `docs/writers/TRAINING_CAMP_DESK.md` + `content/writers/camp-desk-2026/README.md`. **Weekday (Tue–Fri)** = real-news clubs only (quiet skip/pulse; ~6pm ET) — **NEVER** a 32-card dump. **Monday** = full 32 + weekly preview NUMBER pass. “Desk updating” is empty-shelf UI only — **not** a substitute for shipping. This file remains a ship note for the Aug 21 package.

Preseason product: Camp Desk is never empty; writers work like a real desk.

## Why it was empty

Last live file was `2026-08-17.json`. The 72-hour window buried it by Friday Aug 21, and the page copied **No KosEdge camp notes inside the 72-hour window**. That is the wrong empty state during camp.

## What shipped

| Item | Location |
|------|----------|
| Friday daily package | `content/writers/camp-desk-2026/2026-08-21.json` — league wrap + WAS/HOU/BAL/CLE/ATL/NYJ/MIN |
| Monday structure | `package: "monday"` on `2026-08-17.json` (full 32 remains the **Monday-only** template — not weekday) |
| Loader | Every `YYYY-MM-DD.json` in that folder (no code change for the next day) |
| Preseason shelf | Newest package always visible; older days → Archive |
| Empty copy | **Desk updating** + last note date — UI fallback only; still ship the cadence package |
| No X product | Beat map shows writer + outlet only; sources drop `x.com` / `twitter.com` hrefs |
| Writer SOP | `docs/writers/TRAINING_CAMP_DESK.md` + folder `README.md` |

## Friday package (original desk, Pass throughout)

Research: Commanders.com / SI (Newton pec surgery, Allegretti setback, White hamstring; Tunsil already long-term), Yahoo/NFL Network (Higgins ACL season), Ravens.com (Pinter patellar tendon), Falcons.com/AJC (Penix still no 11s), AP/NFL.com (Hall 2–3 weeks, expected Week 1), CBS tracker (Adams season-ending). Joint-practice Browns QB split still unset.

SoT flags (intel path only — no invented starters): WAS OL+Newton, HOU Higgins WR2 open, BAL center competition, ATL Penix availability, CLE QB1 unset, MIN Adams out / Murray still named.

## How a human or agent adds the next day

1. Research beat index + official/local/AP. Do not scrape tweets.
2. Copy `2026-08-21.json` (weekday real-news) or `2026-08-17.json` (Monday all-32). Do **not** ship a weekday as full-32.
3. Save `content/writers/camp-desk-2026/YYYY-MM-DD.json`.
4. Original headlines/notes; date only; outlet-name sources; no X profile links.
5. `is_material_depth` only when depth SoT should be flagged.
6. Update `rotation-queue.json` and `project-log.md`.

Full SOP: `docs/writers/TRAINING_CAMP_DESK.md`.

## Smoke

- `/pro/nfl/camp` shows **Camp Desk — Friday, Aug 21** (not empty, not an X timeline).
- Archive contains Monday Aug 17.
- Filter a quiet team: league wrap still up; no “No KosEdge camp notes”.
- Fantasy / survivor / season-engine math untouched.
