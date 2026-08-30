# NFL Camp Desk cadence lock — weekday vs Monday (2026-08-30)

**Owner:** Ryan (confirmed)  
**Scope:** OS / docs only. No live camp JSON, season-preview body, or `/pro/desk` handicap rewrites.

## Lock

| Slot | Rule |
|------|------|
| Weekday (Tue–Fri) | Real-news clubs only; quiet skip or pulse; ~6pm ET; **NEVER** 32-card hero dump |
| Monday | Full-32 camp package (news + pulse for quiet) **plus** weekly team-preview **NUMBER** pass |
| Injury day | Same-day weekday file |
| Camp cards | Date-only (no writer byline) |
| PHI byline (going forward) | Avery Cole — coverage/docs pointer; Monday pass owns the file |
| Empty shelf | “Desk updating” = UI fallback only — **not** a substitute for shipping |

Writers on NFL also-covers: Casey NFC North; Avery NFC East + South; Reese AFC North + West; Morgan NFC West; Taylor AFC East + South.

Monday NUMBER pass inherits HOUSE vs STREET (pull KEI if printed, never mint, stamp at pull). Riley gates numbers not voice.

## SoT files

- `docs/writers/TRAINING_CAMP_DESK.md`
- `content/writers/camp-desk-2026/README.md`
- `style-bible.md` · `.cursor/rules/ai-writer-team.mdc`
- `content/writers/season-previews-2026/INDEX.md` (PHI → Avery)
- `content/writers/camp-desk-2026/rotation-queue.json` (rule string)

## Schema — `preview_delta` (singular)

Loader `apps/web/lib/nfl-camp-desk-daily.ts` reads **`preview_delta` only**. Plural `preview_deltas` is ignored (`2026-08-26.json` shipped 15 under the plural key — never collected). Monday packages must use singular; copy Monday shape for that field from `2026-08-17.json`, not Aug 26. OS/docs note only — do not rewrite live Aug 26 JSON in the cadence lock PR.
