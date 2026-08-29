# DepthSotWorkItem — gated desk workflow (2026-08-27)

**Ship as a gated workflow, not a pile of JSON.**

```
note → SOT FLAG / work item → human accept → pack → remat → receipt → board
```

Queue ≠ remat. Notes ≠ means. Remat fail ≠ accepted.

**CLI entrypoint (real):** `python scripts/nfl/queue_camp_sot_flags.py`  
(Not `nfl_camp_sot_queue.py` — that module lives under model-service.)

## Pass 1 — Mergeable PR

| In git | Not in git |
|--------|------------|
| model, CLI, accept/reject, remat gate, tests, internal ops API | `camp-flag-*.json` / `work-item-*.json` day dumps |

Runtime queue: `data/ops/nfl-daily-intel/queue/runtime/` (gitignored).

## Pass 2 — Enterprise bar

| Need | Status |
|------|--------|
| Single SoT | Live depth pack only |
| Gate | Accept only pack + remat write |
| Audit | actor, reason, pack before/after sha, remat_run_id, pack_diff, line_delta |
| Idempotency | note_id + team_id + as_of |
| Failure | Remat fail → pack rollback, disposition `remat_failed`, ticket stays open |
| SLA | T1: 12h **or** before next KEI publish (Thu/Fri 16:00 ET) |
| Access | `x-kosedge-secret` on `/nfl/ops/depth-sot/*`; **no public accept UI** |
| Ops | `--scan` / `--alert-t1` (exit 1 if T1 sits through a publish) |

## Operator commands (authoritative)

```bash
# queue today's desk into runtime dir (gitignored); default = newest desk_date
python scripts/nfl/queue_camp_sot_flags.py --queue

# open / overdue summary (no --list flag — use --scan; filter with --tier on --queue)
python scripts/nfl/queue_camp_sot_flags.py --scan
python scripts/nfl/queue_camp_sot_flags.py --scan --json

# dry-run accept (pack_diff + line_delta preview; pack/queue untouched)
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-CLE.json --dry-run
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-HOU.json --dry-run

# real accept (staging pack path first; prod only when user says prod)
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-CLE.json \
  --write --rematerialize --actor desk --reason 'Watson named QB1; competition closed'
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-HOU.json \
  --write --rematerialize --actor desk --reason 'Higgins season-ending; no WR1 crown'

# close noise (no remat)
python scripts/nfl/queue_camp_sot_flags.py --no-change path.json --actor desk --reason 'thin camp / Pass'
python scripts/nfl/queue_camp_sot_flags.py --reject path.json --actor desk --reason 'wrong read'

# overnight SLA
python scripts/nfl/queue_camp_sot_flags.py --alert-t1
```

Flags that do **not** exist: `--date`, `--list`, `--status`. Use `--scan` / `--json` and path-based `--accept`.

## Pass 3 — First live remats (after merge → staging → prod)

Do **not** accept all overdue T1s. Only CLE Watson + HOU Higgins.

```bash
python scripts/nfl/queue_camp_sot_flags.py --queue
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-CLE.json --dry-run
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-HOU.json --dry-run
# Then --write --rematerialize on staging only (see above).
# Confirm receipt pack_diff + line_delta; ATL dual-QB stays Pass (no accept).
# Remaining T1s: --no-change or leave open.
```

If Watson/Higgins remat and ATL does not twitch, the gate works.

## Pass 4 — Daily loop

1. Desk copy publishes  
2. `--queue` upserts items  
3. Review T1 in minutes  
4. accept / reject / no_change  
5. Remat  
6. Next morning: `--alert-t1` → zero unexplained overdue T1s  

Weekly grade: time-to-accept T1, remat success, pack updates → CLV (not wrap prose).

## Do not

- Auto-apply `proposed_patch`
- Let notes write KEI
- Merge dated JSON dumps
- Public accept UI before this API is boring
- Clear the badge by accepting all 10 T1s
- Call production accept until user says `prod`
