# Camp Desk SoT flags → queue → accept (2026-08-27)

**Scope:** model + queue + accept only. No public UI.

## Why

Camp Desk `is_material_depth` / `sot_flag` were UI-only. Lines only move when
structured fields hit the one depth pack. This wires the flags into the
existing daily-intel path so overdue SoT flags are tracked and accepted
overrides can unblock Week 1 / props / KEI without a second map.

## Path

```
Camp Desk JSON (is_material_depth)
  → scan / draft (nfl_camp_sot_queue)
  → data/ops/nfl-daily-intel/proposed/camp-flag-*.json
  → human --accept [--write]
  → pending/ + apply_intel_overrides → nfl_depth_chart_2026_w1.json
  → rematerialize weeks 1–18 (safe rebuild)
```

| Piece | Path |
|-------|------|
| Model | `services/model-service/src/services/nfl_camp_sot_queue.py` |
| CLI | `scripts/nfl/queue_camp_sot_flags.py` |
| Proposed queue | `data/ops/nfl-daily-intel/proposed/` |
| Accept → apply | existing `apply_daily_intel_overrides` / `apply_intel_overrides` |
| Operate hook | `run_weekly_operate` depth_injury stage lists proposals |

## Rules

- Drafts: `injury_status=out` / `competition_status` only when flag text + pack name match.
- Never draft `depth_order` / new rows / starter crowns from thin language.
- `--queue` does not write the pack. `--accept` without `--write` only stages pending/.
- After `--write`: rematerialize via safe entrypoint (weeks 1–18). Do not bare `season=` rebuild.

## Commands

```bash
python scripts/nfl/queue_camp_sot_flags.py --scan
python scripts/nfl/queue_camp_sot_flags.py --queue --only-overdue
python scripts/nfl/queue_camp_sot_flags.py --accept data/ops/nfl-daily-intel/proposed/camp-flag-2026-08-26-CLE.json --write
```
