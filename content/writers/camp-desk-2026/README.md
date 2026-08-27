# Camp Desk day files

Dated KosEdge packages for `/pro/nfl/camp`.

## Add tomorrow’s package

1. Research from the trusted beat index (`data/writers/nfl-beat-writers.json`) plus official/team sites, AP, local beats, RotoWire, VSiN-class. **Do not** scrape tweets or paste X profile links into the product.
2. Copy `2026-08-21.json` (daily) or `2026-08-17.json` (Monday, all 32).
3. Save as `YYYY-MM-DD.json` in this folder. Set `"package": "daily"` or `"package": "monday"`.
4. Original headlines + notes. Date only — no writer byline. Credit outlet names in `sources` (article URLs, never `x.com` / `twitter.com`).
5. `is_material_depth: true` only when roster/depth should hit the intel path. Never invent a starter in SoT from prose.
   Handoff (notes never write numbers): `python scripts/nfl/queue_camp_sot_flags.py --scan` → `--queue` → `--accept|--reject|--no-change`.
   Runtime queue is gitignored — do not commit day dumps. See `data/ops/nfl-camp-sot-queue-accept-20260827.md`.
6. Update `rotation-queue.json` `next_pulse` for quiet clubs. Update `project-log.md`.
7. Full SOP: `docs/writers/TRAINING_CAMP_DESK.md` and `data/ops/nfl-camp-desk-daily-cadence-20260821.md`.

The Camp Desk loader reads every `YYYY-MM-DD.json` in this folder. No code change required for a new day.

## Cadence

| Slot | File shape |
|------|------------|
| Daily (camp) | League wrap + every team with **real** news (skip quiet clubs) |
| Monday | Full 32 + league wrap (see `2026-08-17.json`) |
| Injury day | Same-day daily file — do not wait for Monday |

During preseason the site always shows the newest file. Notes older than 72 hours move to Archive unless they are still the latest package.
