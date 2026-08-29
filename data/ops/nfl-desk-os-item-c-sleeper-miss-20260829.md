# Desk OS item C — Sleeper unmatched ID miss log (2026-08-29)

**After Desk OS item B (#314) on e253 (`33d4e3aa1fa4`).** Book off limits. No accepts. No roster rewrite.

## What

When `--scan-txns` / `--morning` maps Sleeper txn-feed events → pack and `map_feed_player_to_pack` returns `None`, **print** those misses.

## Scope

- Same events as `--scan-txns` (Sleeper IR/out/waived skill+OL with a team) — **not** the full Sleeper roster
- PFR rows ignored for this miss list (source must be `sleeper`)
- Matched players (gsis or team+name) are **not** listed

## Output

Stdout section:

```
=== Desk OS item C: Sleeper unmatched ID miss list (n=N; print only — no roster rewrite) ===
team  player  pos  event  sleeper_id  gsis_id  reason
```

Optional gitignored append:

`data/ops/nfl-daily-intel/cache/sleeper-unmatched-YYYY-MM-DD.jsonl`

## CLI

```bash
python scripts/nfl/queue_camp_sot_flags.py --scan-txns
python scripts/nfl/queue_camp_sot_flags.py --morning
```

## Does not

- Rewrite pack / identity map / roster graph
- Auto-accept
- Book ledger/grader
- CFB flake work
