# Chapter 2 Phase 2B — 2025 SP+ carry shrink (global)

**Repo:** `kosedge/kosedge`  
**Base:** after Phase 2A eff-pack audit

2A locked:

- Compose `off_eff`/`def_eff` = **final-2025 SP+** z-scored to 5–95
- Pack: `cfb_efficiency_snapshot_2025_carry_2026.json` · `prior_year=2025` · **no 2026 games**
- Warehouse PBP adj is **research_prior only** — not the line
- UNC **24.92** (SP+ off 17.2, #124) and STAN **28.18** (18.5, #117) are **2025 corpses**
- TCU **64.74** / HAW **50.21** are the same carry (strong / average)
- Portal/QB 2026 does **not** rematerialize eff

Do not set `MATCHUP_RESPONSE=1.00`. Do not `if Stanford`.

---

## This PR (docs / gate rewrite only)

Phase 0: print `off_eff` for OSU, BALL, TCU, UNC, HAW, STAN, plus top-7. No edits.

Paper-sim ∈ {0.70, 0.80, 0.85} **before** any pack write. **No invented s** (not 0.40, not 0.98).

```text
off_eff' = 50 + shrink * (off_eff_2025 - 50)
def_eff' = 50 + shrink * (def_eff_2025 - 50)
```

**This revision does not ship the shrink.** Operator decision: rewrite the power canary, re-read the existing paper-sim, then gate the fit PR.

---

## Canaries (operator rewrite 2026-08-31)

### Keep

| Gate      | Rule                                                                                     |
| --------- | ---------------------------------------------------------------------------------------- |
| OSU #1    | Live `build_power_sot` rank 1 = OSU                                                      |
| BALL@OSU  | WP ≥ 0.90 (cupcake)                                                                      |
| Polarity  | STAN off_eff ↑ from 28.18; UNC ↑ from 24.92; TCU ↓ from 64.74; TCU raw margin &lt; 16.48 |
| Forbidden | no team-if; no `MATCHUP_RESPONSE`; no 1C–1E revert; no PBP SoT swap                      |
| s set     | only {0.70, 0.80, 0.85}                                                                  |

### Drop

Exact top-7 **order** (ORE↔MISS / ND↔TEX moving is the shrink working on 0.0002 / 0.003 baseline gaps).

### Replace with

**Top-7 membership** vs baseline `{OSU, ORE, MISS, MIA, IU, TAMU, ND}`:

- May change **only** on the two documented near-ties: **ORE↔MISS** (order) and **ND↔TEX** (TEX may replace ND).
- If any **other** name enters or leaves the seven → still **BLOCKER**.

### Rejected operator forks

1. ~~OSU #1 + same seven membership~~ — still fails every paper-sim s (TEX in). Relabel does not open the set.
2. ~~Park corpses in Chapter 3 situation~~ — W0 finals already ran the corpse test (UNC 15–10 vs TCU KEI −17.68; STAN 37–27 vs HAW KEI +7.62). Sticky 2025 SP+ carry is the 2A mechanism.

**Chosen path: 2** — fix canary to near-ties, then **s=0.85 alone** if it passes; else **s=0.85 + existing early `STRENGTH_NOISE` / year-shock** (one lever, one s). Not a search. If that pair knocks a non-tie out → Chapter 2 blocker (Utah-style). Do not sneak via `WEIGHT_OFF_EFF` or roster blend.

---

## Forbidden

Team branches. `WEIGHT_OFF_EFF` / `MATCHUP_RESPONSE`. QB packager. Enabling PBP adj as live KEI SoT. Revert 1C/1D/1E. Utah / NFL/CBB/MLB. Invented s outside {0.70, 0.80, 0.85}.
