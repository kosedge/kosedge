# NFL Enterprise Strength Spine — Lock Note — 2026-08-11

**Status:** Soft-launch ready · enterprise PR **not finished** (named waits below)  
**Gate:** enterprise-spine-lock (docs) after #199  
**Merge SHA (#199):** `ec0e8ccc56345f5e25b941bb368689a960faa1d3`  
**Base:** `deploy-vercel`  
**Active board:** `nfl-preseason-sim-2026-20260809T165350Z`  
**Engine (live):** `nfl-season-engine-v1.27-kicker-layer`

---

## Deploy verification (#199)

| Surface | Result | Evidence |
|---------|--------|----------|
| GitHub merge | MERGED | PR [#199](https://github.com/kosedge/kosedge/pull/199) → `ec0e8ccc…` @ 2026-08-12T00:42:40Z |
| Vercel `kosedge` | **success** | Status context “Deployment has completed” on merge SHA |
| Vercel `kosedge-vercel-push` | **success** | Same |
| Railway model-service | **success** | Actions run [31551148501](https://github.com/kosedge/kosedge/actions/runs/31551148501) — Railway up (api / worker / beat) |
| Prod ping | **ok** | `GET https://www.kosedge.com/api/ping` → `{"ok":true,…}` |
| Season engine | **live** | `/api/nfl/season-engine/status` → v1.27-kicker-layer, 32 depth teams, real mode |

---

## Complete (single strength spine)

One production board strength drives wins, week rates, win distributions, playoffs, SB, and soft-pile production. Product team id is **`LAR`** (no `LA` fork).

| Item | Notes |
|------|--------|
| LAR dual-path close | Week rates rescaled to board; path-bracket SB; id canonicalize — `nfl-strength-coherence-lar-20260811.md` |
| DET win_dist dual-path close | Hierarchical dist μ rebuilt to board — `nfl-strength-coherence-det-20260811.md` |
| Model PR desk (#198) | Method B Model PR · Ryan Adj · Active PR · Tuesday shrink doctrine — `nfl-power-ratings-desk-20260811.md` |
| Injury → KEI cadence (#199) | Thu/Fri/gameday windows; SoT → Active PR + KEI reprice; Model fair / Model PR frozen — `nfl-injury-kei-cadence-20260811.md` |
| Futures / Season Model columns | Aligned to same board + win_dist |
| Week 1 = 16 REG | Pack + wall chart + board invariant |
| Tag policy | PASS / LEAN / PLAY / BEST VALUE / ALERT / STAY AWAY; early bands; Tag = KEI vs Current |
| Kicker layer | v1.27 FG/XP in scoring path |
| Lineage badge | Edge Board / Season Model / Power / Boxes / Survivor |
| Preseason-complete smoke | Prior lock `nfl-preseason-complete-20260811.md` (32/32 checklist) |

**STRENGTH_ALIGN:** board ≈ week-rate Σ ≈ win_dist.mean (±0.35); no raw `LA`.

---

## Audit summary (2026-08-11)

Full table: [`nfl-strength-spine-audit-20260811.md`](./nfl-strength-spine-audit-20260811.md)

| | |
|--|--|
| Teams audited | **32** |
| Dual-path / id clean | **32** |
| Dual-path bugs left | **0** |
| Report-only | **DET** `low_wins_high_playoff` (division context under CHI; spine aligned at ~7.05 wins) |

No code fix required from this audit.

---

## Waits for kickoff (enterprise PR not “finished” until these)

| Wait | Notes |
|------|--------|
| **Live injury feed** | Manual SoT until automated feed; cadence job is ready |
| **CLV accumulation** | Post-close capture after Week 1 |
| **Tuesday PR after Week 1 finals** | Model PR shrink + publish; Ryan Adj discipline |
| **Rest / travel / weather → KEI** | Not yet in handicap stack |
| **Material SoT → full re-sim publish** | Cadence reprices KEI/Active PR; large availability shocks still need re-sim + publish |
| **Player yards vs prior-year** | Calibration / honesty pass |
| **Fantasy K** | Kicker in fantasy rankings/builder path |
| **Win-distribution middle class** | Soft-pile polarization (thin 7–10 / 10–12 bands) — report only; no eye-test edits |

Also deferred from preseason-complete: props/DFS activation when markets/salaries post; pointer metadata still labels v1.24 while live engine is v1.27 (cosmetic).

---

## North star (short)

```text
                    ┌─────────────────────────┐
                    │  Board strength (soft-  │
                    │  pile / production PF)  │
                    │  expected_wins · LAR id │
                    └───────────┬─────────────┘
           ┌────────────────────┼────────────────────┐
           ▼                    ▼                    ▼
    week_win_rates        win_distributions     player / defense
    (playoff MC)          (Season Model /       budgets (PF/PA,
                          Futures histogram)    yards / TDs)
           └────────────────────┬────────────────────┘
                                ▼
                     playoff % · SB % · board wins
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
     Model PR desk (#198)                  KEI / Edge (#199)
     Method B · Tuesday shrink             Injury SoT → Active PR
     Ryan Adj · Active PR                  + KEI reprice; tags vs Current
                                           Model fair / Model PR frozen
```

**Doctrine:** one strength story; Model research fair frozen midweek; Tag = KEI vs Current only.

---

## Explicit readiness statement

- **Soft-launch ready:** family / allowlist access; Week 1 desk; single spine; #199 cadence merged and deployed.
- **Enterprise PR not finished:** remaining items in **Waits for kickoff** must land (or be explicitly waived) before calling the enterprise strength / PR program complete.
- **No eye-test win overrides** and **no dual-path reopens** without a new audit.

---

## Related ops

- `nfl-preseason-complete-20260811.md` — soft-launch smoke lock  
- `nfl-strength-spine-audit-20260811.md` — this day’s 32-team audit  
- `nfl-power-ratings-desk-20260811.md` — #198  
- `nfl-injury-kei-cadence-20260811.md` — #199  
- `nfl-strength-coherence-lar-20260811.md` / `nfl-strength-coherence-det-20260811.md`

*Locked by: agent · 2026-08-12T01:40Z · merge `ec0e8ccc`*
