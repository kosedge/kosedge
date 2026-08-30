# Camp Desk day files

Dated KosEdge packages for `/pro/nfl/camp`.

## Add tomorrow’s package

1. Research from the trusted beat index (`data/writers/nfl-beat-writers.json`) plus official/team sites, AP, local beats, RotoWire, VSiN-class. **Do not** scrape tweets or paste X profile links into the product.
2. Copy `2026-08-21.json` (weekday / `package: daily`) or `2026-08-17.json` (Monday full-32 / `package: monday`).
3. Save as `YYYY-MM-DD.json` in this folder. Set `"package": "daily"` (weekday) or `"package": "monday"`.
4. Original headlines + notes. **Date only — no writer byline.** Credit outlet names in `sources` (article URLs, never `x.com` / `twitter.com`).
5. `is_material_depth: true` only when roster/depth should hit the intel path. Never invent a starter in SoT from prose.
   Handoff (notes never write numbers): `python scripts/nfl/queue_camp_sot_flags.py --scan` → `--queue` → `--accept|--reject|--no-change`.
   Runtime queue is gitignored — do not commit day dumps. See `data/ops/nfl-camp-sot-queue-accept-20260827.md`.
6. Update `rotation-queue.json` only when a quiet club needs a **pulse** line (not a force-rotate of all 32 on weekdays). Update `project-log.md`.
7. Full SOP: `docs/writers/TRAINING_CAMP_DESK.md` (cadence SoT). Historical ship notes: `data/ops/nfl-camp-desk-daily-cadence-20260821.md`.

### Schema — `preview_delta` (singular)

Loader SoT: `apps/web/lib/nfl-camp-desk-daily.ts` reads **`preview_delta`** only (`file.preview_delta ?? []`). Plural **`preview_deltas` is ignored**.

- Monday (and weekday) packages must use the **singular** key.
- Copy Monday shape for that field from **`2026-08-17.json`**, not `2026-08-26.json` (Aug 26 shipped `preview_deltas` — 15 deltas never collected).
- Do not rewrite live Aug 26 JSON in the cadence OS PR; fix on the next Monday ship if still needed.

The Camp Desk loader reads every `YYYY-MM-DD.json` in this folder. No code change required for a new day.

## Cadence (LOCKED 2026-08-30 — Ryan)

Weekday ≠ Monday. Execution lock — not a new product. **Daily ≠ 32 essays.**

| Slot                  | File shape                                                                                                                                                                                                             |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Weekday (Tue–Fri)** | League wrap + clubs with **real** news only (`package: daily`). Quiet clubs **skip** or a short **pulse** line. **NEVER** a 32-card hero dump. Cutoff **~6pm ET**.                                                     |
| **Monday**            | Full 32 (news cards + pulse for quiet) + league wrap (`package: monday`, see `2026-08-17.json`) **plus** weekly team-preview **NUMBER** pass (Riley gates numbers; HOUSE vs STREET — pull KEI if printed, never mint). |
| **Injury day**        | Same-day weekday file — do not wait for Monday.                                                                                                                                                                        |

Writers on NFL also-covers: Casey NFC North; Avery NFC East + South; Reese AFC North + West; Morgan NFC West; Taylor AFC East + South. Camp cards stay date-only.

“Desk updating” is UI fallback for an empty shelf — **not** a substitute for shipping the weekday or Monday package.

During preseason the site always shows the newest file. Notes older than 72 hours move to Archive unless they are still the latest package.
