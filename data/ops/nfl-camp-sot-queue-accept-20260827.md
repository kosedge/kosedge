# DepthSotWorkItem — gated desk workflow (2026-08-27)

**Ship as a gated workflow, not a pile of JSON.**

```
note → SOT FLAG / work item → human accept → pack → remat → receipt → board
```

Queue ≠ remat. Notes ≠ means. Remat fail ≠ accepted.

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

## Pass 3 — First live remats (after merge → staging → prod)

Do **not** accept all overdue T1s. Only:

```bash
python scripts/nfl/queue_camp_sot_flags.py --queue
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-CLE.json \
  --write --rematerialize --actor desk --reason 'Watson named QB1'
python scripts/nfl/queue_camp_sot_flags.py --accept \
  data/ops/nfl-daily-intel/queue/runtime/work-item-2026-08-26-HOU.json \
  --write --rematerialize --actor desk --reason 'Higgins season-ending; no WR1 crown'
# Confirm receipt pack_diff + line_delta; then safe remat weeks 1–18 if needed.
# Remaining T1s: --no-change or leave T2. ATL stays Pass.
```

If Watson/Higgins remat and the rest of the board does not twitch, the design is working.

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
