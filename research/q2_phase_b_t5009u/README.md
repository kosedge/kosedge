# Q2 Phase B EXEC (t5009u) — DEV_RESEARCH

**CERT=0 · NFL NO-GO · no merge/deploy/pub/bet · no self-ACCEPT of keep**

Opponent-adjusted as-of team strength (`margin = h + s_home − s_away`, ridge)
fitted on DEV 2013–16 REG W2–17 only. Config is hashed and sealed *before*
any EVAL 2018–22 row is read. Keep/stop is reported exactly per
`Q2_EVAL_SPEC_CLARIFY` tip `349e081e` §6. Result returns via **Alex RO → CoS**.

## Authority pins (box-verified sha256 prefixes)

| File | tip |
|---|---|
| OWNER CLEAR / CoS ACCEPT | `9c37d348` |
| CoS ORDER | `dc78aa4e` |
| Phase A design | `2702b295` |
| Eval spec clarify | `349e081e` |
| games.csv (primary) | `4fe1cdd7` |
| As-of kickoff rule | `cf514078` |

## Reproduce

Requires Python 3.10+ and `numpy` (no pandas / scipy).

```bash
# 1) Confirm games.csv pin
sha256sum research/q2_phase_b_t5009u/data/games_4fe1cdd7.csv | cut -c1-8
# expect: 4fe1cdd7

# 2) Unit guards (leakage / wl_diff / season firewall)
python3 research/q2_phase_b_t5009u/tests/test_q2pb_guards.py -v

# 3) DEV fit → seal FROZEN_CONFIG → optional one EVAL look
python3 research/q2_phase_b_t5009u/run_q2_phase_b.py \
  --games research/q2_phase_b_t5009u/data/games_4fe1cdd7.csv \
  --outcomes research/q2_phase_b_t5009u/data/outcomes_2013_2022_score_only.csv \
  --out ops/nfl_enterprise_green_t4359u
```

The runner **stream-filters by season**. Phase 1 materializes 2013–16 only.
EVAL 2018–22 rows are not opened unless DEV passes both early-stop gates.
2017 is history-only (prior into 2018) and is never a fit or EVAL row.
2023 is unused (reserve). 2024–25 are never loaded.

## Data notes

`games.csv` tip `4fe1cdd7` has identity, kickoff, entering W-L records, and
market spread. It does **not** have `home_score` / `away_score` (design 2702b295
listed scores; the CoS-verified file does not).

Public finals for 2013–2022 were copied into
`data/outcomes_2013_2022_score_only.csv` (six columns only). Source file hash
`1ee90fac` is the gated hist index — **not** used as the experiment frame.
2023–26 rows and every trailing/packaged/EPA/error column were dropped.
See `data/OUTCOME_JOIN_NOTE.md`. Alex RO must confirm this is not gate
`83646d78` scored reuse.

`wl_diff` is **recomputed as-of** (current-season win% home − away; kickoff <
target). `games.csv` has no `wl_diff` column; `record_entering_*` is a mapping
cross-check only.

EPA/PBP (`6ee24b44`) is **SKIPPED/UNAVAILABLE** on this VM. Primary signal is
margin strength. S1/EPA-trail was not revived.

## Outputs (sealed 0444 + `.sha256`)

Under `ops/nfl_enterprise_green_t4359u/`:

- `FROZEN_CONFIG_Q2PB_t5009u.md` / `.json`
- `DEV_EARLY_STOP_Q2PB_t5009u.md` **or** `EVAL_ONELOOK_Q2PB_t5009u.md`
- hours log + reusable components list

## Prohibited (honored)

2017/2023/2024–25 in fits or EVAL rows · scored reuse of `1ee90fac` as an
index · `trailing_*` · S1 revive · math/eval rule changes · merge/deploy/pub/bet
· prod writes · Stage C · new data acquisition.
