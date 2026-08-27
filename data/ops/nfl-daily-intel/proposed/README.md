# Camp Desk → depth SoT proposals

Open material-depth flags from Camp Desk (`is_material_depth`) land here as
**proposals**. They are not applied until a human accepts.

```bash
# Scan overdue / open flags
python scripts/nfl/queue_camp_sot_flags.py --scan

# Write/refresh proposals in this folder
python scripts/nfl/queue_camp_sot_flags.py --queue

# Review a file, edit overrides if needed, then accept → pending/
python scripts/nfl/queue_camp_sot_flags.py --accept data/ops/nfl-daily-intel/proposed/camp-flag-YYYY-MM-DD-TEAM.json

# Accept + write the one depth pack (then rematerialize weeks 1–18)
python scripts/nfl/queue_camp_sot_flags.py --accept <file> --write
```

Rules:

- Extends daily intel / rematerialize — **no second SoT**.
- Drafts may suggest `injury_status` / `competition_status` only.
- Never invent `depth_order` or new starters from prose.
- Weekly operate lists these as `human_required`; it does not auto-write.
