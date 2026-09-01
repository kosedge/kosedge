# WNBA Chapter 1 — team prior shell brief

**Phase:** Pack a temporary team prior. **No** Edge tags, **no** props, **no** emit onto `/edge-board/wnba`.  
**Depends on:** [#377](https://github.com/kosedge/kosedge/pull/377) merged (Ch0 pick A)  
**Stamp:** `wnba-season-engine-v0.1`  
**Chosen:** `WNBA_TEAM_CARRY_SHRINK = 0.85`  
**Pack:** `wnba_team_prior_2026.json`  
**Scorecard:** [`docs/WNBA_CH1_TEAM_PRIOR_SCORECARD.md`](./WNBA_CH1_TEAM_PRIOR_SCORECARD.md)  
**Leave alone:** NBA v0.1 · CFB · NFL · Aug-1 leftover fair-lines `401857105` / `401857106`

---

## Formula

```text
team' = league_mean + s * (team_2026_ytd − league_mean)
```

One `s` for the league. Paper-sim set `{0.70, 0.80, 0.85, 0.90}` — **picked 0.85** (order-preserving, modest compression). Own constant **`WNBA_TEAM_CARRY_SHRINK`** — do **not** reuse NBA `TEAM_CARRY_SHRINK`.

**Why 2026 YTD, not 2025:** week-of-Sep with ~40 of 44 RS games in. 2025 is a different roster; 2025 belongs on players in Ch2.

This is a **shell**. Chapter 2 is 3y player × 2026 minutes (grid sums to **200**). Not a props desk. Not a board emit.

---

## Allowlist (this PR)

| Item                              | Path                                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------ |
| `WNBA_TEAM_CARRY_SHRINK` + reader | `services/model-service/src/services/wnba_season_engine/priors.py` · `team_prior.py` |
| 2026 YTD snapshot pack            | `…/wnba_season_engine/data/wnba_team_prior_2026.json`                                |
| Rebuild script                    | `scripts/wnba/build_team_prior_ch1.py`                                               |
| Tests + CI                        | `tests/test_wnba_team_prior_ch1.py` · WNBA-only path in `pr-check.yml`               |
| Docs                              | this brief + scorecard                                                               |

---

## Source note

Intended SoT path from Ch0 audit: stats.wnba.com Advanced via `wnba_data.py`. In this build env `stats.wnba.com` timed out and `data.wnba.com` returned 403. Pack stamped from Basketball-Reference WNBA 2026 **advanced-team** (ORtg / DRtg / NRtg / Pace) — same concepts. Rebuild prefers WNBA Stats when egress works.

**Expansion (TOR / POR):** YTD + shrink only. No invented 2025 row (`expansion_ytd_only: true`).

---

## Forbidden (honored)

- Writing KEI onto `/edge-board/wnba`
- Blending Aug 1 leftover fair-lines (`401857105` / `401857106`)
- NBA shrink / home +2.0 / B2B −1.5
- Player RAPM / minute grid (Ch2)
- Team `if` / Finals bump
- NBA / CFB / NFL packs

---

## Gates

- Every 2026 team has a row (15)
- League mean net ≈ 0 after shrink (offset documented)
- 2026 top/bottom don’t invert into lottery favorites
- Live CON@ATL market row untouched
- NBA HOU/OKC KEI still ≈ +4.2 / −4.2 (pack `−4.16` home OKC opener)
- CFB BALL@OSU still −40.5

---

## Done

One `s` chosen, pack on disk, board leftover still leftover.  
**Stop.** Chapter 2 is next — not a props desk, not a board emit.
