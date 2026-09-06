# Desk ATS / ROI record (machine SoT)

Public product record for stamped **desk PLAY / LEAN** tickets only.

| Path | Role |
| ---- | ---- |
| `cfb/2026/ledger.jsonl` | Append-friendly CFB ticket ledger (SoT) |
| `cfb/2026/summary.json` | Deterministic season-to-date rollup (rebuild from ledger) |
| `nfl/2026/ledger.jsonl` | Empty skeleton — copyable pattern; no fake grades |

## Contract (short)

1. Eligible: desk PLAY/LEAN from writer packages / stamped desk SoT only. Edge Board Tag PLAYs not on the desk card do **not** count.
2. Line + juice: best available pre-kick among designated Compare Odds books; stamp `as_of`. Never invent flat −110.
3. Missing pre-kick juice → **DATA GAP** for that ticket’s ROI contribution; still show ATS W/L/P when line known.
4. Pushes: `profit_u = 0`; exclude stake from risked denominator.
5. Totals only when desk tagged PLAY/LEAN total.
6. Stake until changed: PLAY = 1.0u, LEAN = 0.5u.

Full contract + morning job: `docs/DESK_ATS_ROI_RECORD.md`.

## Rebuild summary

```bash
python3 scripts/desk-record/rebuild_summary.py --sport cfb --season 2026
```

Page `/record/cfb` reads the ledger (and uses summary when present). Morning update = settle prior-day ET tickets into the ledger → rebuild summary → commit/push.
