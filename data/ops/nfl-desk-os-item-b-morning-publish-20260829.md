# Desk OS item B — morning loop + KEI publish hard-block (2026-08-29)

**After Desk OS item A (#309) on e253 (`b7cb42aa88c8`).** Book off limits. No accepts. No flake. No Sleeper miss-log.

## Morning loop (one command)

```bash
python scripts/nfl/queue_camp_sot_flags.py --morning
```

Expands to:

1. `--scan-txns` — free txn feed vs pack (propose only)
2. `--scan-report` — week-of injury report T1s (propose only)
3. `--alert-t1` — exit 1 if any T1 (camp + report + txn) is still open past next KEI publish

Equivalent explicit form:

```bash
python scripts/nfl/queue_camp_sot_flags.py --scan-txns --scan-report --alert-t1
```

## `--scan-txns` (lands #300)

- Module: `nfl_txn_sot_scan.py`
- CLI: `queue_camp_sot_flags.py --scan-txns` (+ `scripts/nfl/ingest_nfl_transactions.py`)
- Opens `proposed_patch` only. **No auto-accept.** No inventing starters. No PUP-as-IR.

## KEI publish hard-block

`injury_kei_reprice.py` (midweek / friday_final / gameday / fixture) **refuses live publish** when any T1 is overdue (SLA or past KEI window) without `accept` / `no_change` / `reject`.

What it rejects:

| Condition | Result |
|-----------|--------|
| Open/queued/overdue **T1** past KEI publish deadline | refuse (exit 1) |
| Open/queued/overdue **T1** with `overdue=True` (12h SLA) | refuse (exit 1) |
| T1 already `accepted` / `no_change` / `reject` | allow |
| `--dry-run` with blockers | print blockers; **no write**; exit 0 |

Sources scanned for the gate: camp desk + injury-report + txn.

```bash
# Live publish — blocked when overdue T1s sit
python scripts/nfl/injury_kei_reprice.py --window friday_final

# Dry-run still computes but prints the would-block list
python scripts/nfl/injury_kei_reprice.py --window friday_final --dry-run
```

## Out of scope

Desk OS item C (Sleeper miss log), D (CFB flake), E (defense accepts), F (weather glance). No Book ledger/grader work.
