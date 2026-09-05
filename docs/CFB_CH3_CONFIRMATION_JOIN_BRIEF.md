# CFB Chapter 3 — confirmation join brief

**Phase:** Info-loop wiring. **Not** a ratings pass. **Not** a fit.  
**Depends on:** [#361](https://github.com/kosedge/kosedge/pull/361) merged (`0612421f`)  
**Stamp frozen:** `cfb-season-engine-v0.15-power-sot` + 1C–1E + `EFF_CARRY_SHRINK=0.85`  
**Companion audit:** [`docs/CFB_CH3_CONFIRMATION_JOIN_AUDIT.md`](./CFB_CH3_CONFIRMATION_JOIN_AUDIT.md)

---

## Why this, not a fit

Phase 0 (#361) already named the hole: 1C–1E exists, but runtime did not re-read a week-scoped confirmed starter. Neutral flag is shared. `rest_travel` is **not** on the stack (later class). Rebuild group is already handled by s=0.85.

A fit PR stays blocked until W1 grades exist and one lever is chosen. This PR is doctrine step 2 — **confirmation**: make the existing QB path see this week’s starter. Not a second QB knob.

---

## Allowlist (done)

1. Audit where 1C–1E reads roster/QB today — see audit (paths + OSU sample).
2. Join current W1 confirmed starter into **that same path**. One SoT:
   - `cfb_qb_confirmed_starters_w1_2026.json`
   - `qb_confirmed_starters.apply_confirmed_starter`
   - Wired in `loaders._team_state_from_payload` + `preseason_prior` after expert override
3. If the starter is unchanged vs the prior 1C–1E input → KEI unchanged (seeded `matched_1c1e_input`).
4. Docs note: **`rest_travel` is a later class, not this PR.**

**`--kei-only`:** not run. Zero identity moves → **no emit**.

---

## Pipeline (do not fork)

```text
packaged ESPN qb
  → apply_qb_situation_override   (class honesty)
  → apply_confirmed_starter       (W1 identity lock)
  → build_qb_situation            (1C–1E only)
  → compose_team_projection
```

---

## Forbidden (honored)

- New QB model / 1C–1E revert / parallel talent path
- `EFF_CARRY_SHRINK` / `STRENGTH_NOISE` / `MATCHUP_RESPONSE`
- team `if` in compose
- `rest_travel` coefficients
- rebuild-offense add-on on top of 0.85
- W1 card regen
- fitting UNC@TCU or HAW@STAN
- Utah

---

## Gates

- OSU #1 · BALL@OSU WP ≥ 0.90 · Utah 6.2% (untouched)
- Membership still only ORE↔MISS / ND↔TEX
- Published KEI identical for every team whose W1 starter already matched the 1C–1E input
- **PR result: zero moves, no emit**

---

## Done

Join exists and is live on universe load. Pack write / KEI emit skipped (nobody’s confirmed starter differed from the baked 1C–1E input). Stop until Sat 9/5 harness step 4. **Fit is still not next.**
