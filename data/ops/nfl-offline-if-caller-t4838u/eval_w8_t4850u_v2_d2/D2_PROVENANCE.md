# D2 provenance note t4862u — add-only

Alex RO CONDITIONAL `10ca67fe`. Paper add-only under existing #667 DRAFT auth
(caller eng ACCEPTED t4841u · EVAL_ONLY lineage). ≠merge ≠emit ≠E1 ≠FREE_PUBLIC
≠Odds ≠C10 ≠Railway.

**Does not rewrite** `eval_w8_t4850u/` or `eval_w8_t4850u_v2/`.

## Bind (three SHAs, do not collapse)

| Role | sha8 | full |
|---|---|---|
| Packet / content tip | `6ca03716` | `6ca03716fe52930332d5ffba302c312a651980cc` |
| PR head stamp | `1d8b089b` | `1d8b089bcea5e6b3573e837bc17266d6c18ef1b6` |
| Sealed invoke HEAD | `426bd1d9` | `426bd1d9e7d3eed4e9bf1166caa2b558862e7551` |
| Lineage base | `b6d019b0` | `b6d019b051f13156354504097d1635b64ab7ceae` |

`eval_w8_t4850u_v2/INVOKE_STDOUT.txt` line 3 is `HEAD=426bd1d9e7d3eed4e9bf1166caa2b558862e7551`.
That is the parent v1 tip at write time. It is **not** rewritten.

Two-commit stamp: content `6ca03716` then MANIFEST stamp `1d8b089b`.
`MANIFEST.json` `packet_tip` / `pr_head` remain `6ca03716`. Branch tip after stamp
was `1d8b089b`.

## Why the in-packet MANIFEST diff was stale

`--write-packet` ran while HEAD was still `426bd1d9` and v2 sources were untracked,
so the first `diff_vs_b6d019b0` omitted `*_v2.py`. Stamp `1d8b089b` later refreshed
the in-packet file list, but D2 SoT is this regenerated add-only diff against
packet tip `6ca03716`, not a rewrite of the sealed MANIFEST.

## Regenerated diff vs `b6d019b0` (includes `*_v2.py`)

- `DIFF_b6d019b0_to_6ca03716.name-only.txt`
- `DIFF_b6d019b0_to_6ca03716.stat.txt`
- also `DIFF_b6d019b0_to_1d8b089b.*` (PR-head stamp)

`*_v2.py` present at packet tip:

- `scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py`
- `services/model-service/src/services/nfl_offline_if_eval_w8_v2.py`
- `services/model-service/tests/test_nfl_offline_if_eval_w8_t4850u_v2.py`

## Script bind at `6ca03716`

See `SCRIPT_BIND_6ca03716.json`.

| path | git blob | sha256 |
|---|---|---|
| `scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py` | `a6f249d0ca517dd05ede3c1a303acd4b9607c863` | `d1582231a014f717bc85e8bba634410bcb70a862776b2db0b9929106948d3314` |
| `services/model-service/src/services/nfl_offline_if_eval_w8_v2.py` | `f1675348af9c27e50d3ec201a9f81d07259901b1` | `a6ccb178b5c5c136e5aae8bc5ee0d31c1fe3ebe91268b8e6b51f59a828a989a3` |
| `services/model-service/src/services/nfl_offline_if_eval_w8.py` | `77f34a83608097942233fdc618f96822a4879810` | `f4c5aba02695e5fc11baac5b1ebe3f7b292b3742611bf6716659f05051ba872d` |

Cmd at that tip:

`PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py --write-packet`

## Holds

IF blend=0 · rating_week=7 · through-W7 `c674da77` · 13 games · TNF excluded ·
DIAGNOSTIC · `public_delivery=false` · W9 untouched · W8 STANDBY / #663 schedule
untouched · v1 and v2 packets sealed.

NFL NO-GO · CERT=0 · Coming Soon ON · ≠FREE_PUBLIC ≠BETTING ≠E1 ≠merge.
