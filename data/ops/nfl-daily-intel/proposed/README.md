# DepthSotWorkItem proposals (Camp Desk → one depth pack)

Open `is_material_depth` / SOT FLAG tickets. **Notes stay copy.**

```
note → work item → human accept structured fields → rematerialize → receipt
```

```bash
python scripts/nfl/queue_camp_sot_flags.py --scan
python scripts/nfl/queue_camp_sot_flags.py --queue --tier T1
python scripts/nfl/queue_camp_sot_flags.py --accept <file> --write --rematerialize
```

- `proposed_patch` is a suggestion only — never auto-applied.
- Accept is the only gate that may write the pack or rematerialize.
- T3 Pass: `--accept --allow-empty` to clear without a pack write.
- No second SoT. See `data/ops/nfl-camp-sot-queue-accept-20260827.md`.
