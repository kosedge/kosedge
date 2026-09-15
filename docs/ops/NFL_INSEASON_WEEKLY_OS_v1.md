# NFL In-Season Weekly OS v1

**Lock:** Ryan / CoS · 2026-09-15  
**Status:** SPEC. Product chrome in this lock (Club Desk rename, mock hide, current-week helper) ships with the matching PR. Ratings / stats / KE pipelines stay **parked** until their own inventory lands.  
**Does not change:** Edge Board math, KEI mint, PLAY stamps, CFB kill-switch, Line Curve, #516.

Camp is over. Customer chrome must not read as a training-camp desk or a Week 1 pin.

---

## Current week (product SoT)

Implementation: `apps/web/lib/nfl-current-week.ts`.

```
currentWeek = the REG week whose first kickoff has occurred
           OR the upcoming week after the previous week's last game is FINAL.

After the last game of week W is FINAL → default becomes W+1.
```

- Schedule SoT is the canonical 2026 REG pack (`nfl-canonical-schedule`).
- Box FINAL is not joined on this helper. A game is treated FINAL once `kickoff + 4h` has passed.
- **Fail closed** if the week cannot be proven. Do **not** silently show Week 1.
- Monday package = recap of W (Sunday clubs) + preview of W+1. MNF clubs drop Tuesday.
- As of Tue 2026-09-15, proven current week is **Week 2**.

Surfaces that must use this helper (not a hard-pin):

- Weekly Slate window / overview slate chrome
- Club Desk week badge
- Fantasy DFS default week
- `getTonightGames("nfl")` filter (does **not** recut assemble / Edge Board)

Out of scope for the helper: Edge Board assemble default, Edges PLAY tags, CFB week pins.

---

## Club Desk cadence

Customer name: **Club Desk**. Canonical route: `/pro/nfl/club`.  
Legacy `/pro/nfl/camp` redirects. Content folder `content/writers/camp-desk-2026/` may stay until a path alias.

| Slot | Ships | Notes |
| --- | --- | --- |
| **Monday** | Recap of week W (all Sunday clubs) + preview of W+1 | Not a 32-card dump unless news warrants. NUMBER pass still Monday. |
| **Tuesday** | MNF clubs drop | After last game of W is FINAL, product week is W+1. |
| **3pm ET news** | Real-news clubs only | Quiet skip. Same weekday rule as camp OS — real news, not 32 essays. |

Writer SoT for notes remains `docs/writers/TRAINING_CAMP_DESK.md` until that file is renamed. Product chrome says Club Desk.

---

## After each FINAL

1. Ingest box / PBP for that game (existing ingest jobs — do not invent a new pipeline here).
2. Rolling form uses **W−1 only**. Do not blend the rest of the season into “form” copy.
3. Injuries / inactives: rematerialize or **fail closed** (existing SOP). Do not show a stale active when the suppress store is empty.

---

## After MNF / Tuesday AM — power ratings / KE snapshot

**Gated.** Until a KE Ratings Engine exists:

- Stamp `as_of` honestly on Power Ratings / KE surfaces.
- Do **not** fake a live KE refresh from off numbers.
- Tuesday power-ratings runbook (`docs/runbooks/nfl-tuesday-power-ratings.md`) remains the desk procedure when Ryan runs it. This OS does not authorize an automatic KE recut.

---

## Fantasy

- In-season landing is **DFS** (this week’s slate). `/pro/nfl/fantasy` redirects to `/pro/nfl/dfs`.
- Mock rooms under `/pro/nfl/fantasy/mock` are **hidden** (honest “drafts are over” page). Engine stays in-repo.
- DFS slate rebuilds on week flip via the current-week helper. No Week 1 default.
- Draft board remains at `/pro/nfl/fantasy/draft` (not in primary nav).

---

## Edges — PARKED

Until KE efficiency exists:

- **No new PLAY publishes** from current off numbers.
- **Do not recut Edge Board** as part of this OS.
- CFB kill-switch remains **ON**.
- Numbers-only on parked surfaces. No “play this” chrome.

This is not a model refit, not a 2025 CFB PBP job, and not a KEI mint.

---

## Honesty

- Club Desk week chrome uses the proven current week, or fail-closed copy — never a Preseason badge after REG has started.
- Depth charts stay packaged/model, labeled **not live Club Desk**.
- Power Ratings / KE `as_of` must match the last real snapshot. No invented Tuesday print.
