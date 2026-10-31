# DIAGNOSIS — NFL IF compression vs current market (OWNER t4902u)

**Class:** `CONDITIONAL_DIAG` (engineering self-label). Alex RO grades separately.  
**Authority:** OWNER t4902u · CoS standing ops · **read-only** · no retune  
**IF tip:** `6ca03716` (`6ca03716fe52930332d5ffba302c312a651980cc`)  
**Compare seal:** `e19d6c3c` · table `bfa50665` · RESULTS `31cb1d89` · Odds T_now `2026-10-31T03:20:28Z`  
**Eng ≠edge ≠CLV ≠betting ≠CERT. NFL NO-GO · CERT=0.**

Replay of the sealed caller matches RESULTS exactly (margin_mu / total_mu / spread / wp / sigma / blend=0) for all three focus games. No simulator, weight, blend, or feature code was changed.

---

## Verdict (ranked)

| Rank | Class | Finding |
|---|---|---|
| **1 — PRIMARY** | **B** intentional shrinkage / prior / regularization **as designed** | W-L→narrow index, 0.35 EPA gain, ±6.5 efficiency cap, RZ regression subtract, HFA 1.05, totals prior 45.3, IF contract zeros KAV/injury/weather/travel. Practical Sunday envelope ≈ **9.35 pts**. Slate \|spread\| max **5.18**. DK −12.5 is outside observed IF range. |
| **2 — SECONDARY** | **C** empirically weak forecast (pipeline intact, low discrimination) | Primary strength is **win-loss only**, not opponent-adjusted EPA. 5g EPA diffs reach the simulator but are low-gain. Totals cannot express high-scoring games (ARI@DAL 46.95 vs DK 54.5). σ = 10.0068 on all 13 games. |
| **3 — REJECTED as causal** | **A** wiring / scaling defect | Home/away signs consistent. No silent zero of team diffs. No home/away flip. Single HFA. Units intact. Blend=0. Sealed replay bit-matches. |

**DATA_PARTIAL / week-7 vintage: REJECTED as the cause.** `rating_week=7` is the intended as-of for W8 (`rating_week = target_week − 1`). See §6.

Any proposed math / feature / weight / blend change is **Ryan escalate only**. Not implemented here.

---

## Signed gaps (IF − DraftKings current_post_seal)

Independent recompute. Sign: spread = home line (negative = home favored). Δspread > 0 = IF less home-bullish (closer to pick'em). Δwp = IF home_win_prob − DK proportional de-vig home. Matches COMPARE_TABLE `bfa50665`.

| Game | IF spr / DK | **Δspr** | IF tot / DK | **Δtot** | IF wp / DK de-vig | **Δwp** | IF fair ML / mkt de-vig fair |
|---|---|---:|---|---:|---|---:|---|
| TEN@CIN | −4.44 / −12.5 | **+8.06** | 45.71 / 46.5 | **−0.79** | 0.6218 / 0.8371 | **−0.2153** | −164 / −514 |
| IND@JAX | −3.64 / −10.0 | **+6.36** | 44.77 / 46.5 | **−1.73** | 0.6085 / 0.8000 | **−0.1915** | −155 / −400 |
| ARI@DAL | −2.38 / −7.0 | **+4.62** | 46.95 / 54.5 | **−7.55** | 0.5690 / 0.7221 | **−0.1531** | −132 / −260 |

De-vig check (independent): `q = implied / (p_h + p_a)`; TEN@CIN −675/490 → 0.8371; IND@JAX −500/380 → 0.8000; ARI@DAL −305/245 → 0.7221. Matches seal.

**Slate context (13 IF games, not a sample of quality):** spread range **−5.18 … +2.42**; totals **43.53 … 46.95**; wp **0.432 … 0.648**. Systematic pull toward pick'em, not three outliers.

---

## Market orientation + ML comparability

**PASS — same convention.**

- IF: `spread_home = −margin_mu`. Negative = home favored.
- DK: home point negative = home favored; away point is the opposite sign.
- All three games: both sides home-favored. No flip.
- ML: IF `home_win_prob = P(home_score − away_score > 0)` from 4000 gauss draws (margin==0 counted away; continuous so P(tie)≈0). Fair ML from that p. Market ML = game incl. OT, no push (tie void/refund ignored). Comparable as P(home wins). Not a settlement-rule artifact.
- Analytic check TEN@CIN: Φ(4.441 / (10.0068√2)) = 0.623 vs MC 0.622. If IF σ is applied to the **market** −12.5, Φ(12.5 / 14.15) = 0.811 vs DK de-vig 0.837. The remaining ~0.026 is book/σ shape, not a sign error. The **8-point spread gap** is the compression; wp follows.

---

## Mechanism (what actually produces the numbers)

### Path (intact)

```
through-W7 panel 340a06dd
  → T5 team_strength_from_record (W-L → offense/defense index)
  → T2/T3/T4 5g EPA / success / pressure / RZ diffs (home-centric)
  → build_contract_inputs (20 fields + rest; all else forbidden)
  → _build_matchup_adjustments + compute_nfl_projection_decomposition
  → μ_h, μ_a
  → MC N=4000, seed per game, market_blend=0
  → margin_mu / spread_home / total / wp
```

Wiring checks that **passed** on all three games:

- Home/away tokens match schedule (CIN/TEN, JAX/IND, DAL/ARI).
- Index diffs are non-zero and enter `off_def = (off / def_opp) − 1`.
- EPA diffs are non-zero and enter the matchup pack.
- HFA applied **once** = 1.05 (framework prior = HFA factor).
- Rest Sunday 7/7 both sides (UTC DOW heuristic; bye rest not added — recorded, not invented).
- No out-of-contract field populated (KAV/injury/weather/travel all `None`).
- `independent_fair.market_blend == 0`.

### B1 — Strength is W-L, compressed by construction

`nfl_data.team_strength_from_record`:

```
offense = clamp(0.90 + 0.22 × win%, 0.82, 1.18)
defense = clamp(0.92 + 0.20 × win%, 0.82, 1.20)
```

**32/32 teams** match this formula exactly. `t5_source = team_strength_from_record` on every row. No 2025 prior. League offense_index range **0.90–1.12** (width 0.22); defense **0.92–1.12** (width 0.20).

| Team | W-L | win% | off_idx | def_idx |
|---|---|---:|---:|---:|
| TEN | 1-6 | 0.143 | 0.931 | 0.949 |
| IND / ARI | 2-5 | 0.286 | 0.963 | 0.977 |
| DAL | 3-4 | 0.429 | 0.994 | 1.006 |
| CIN / JAX | 4-2 | 0.667 | 1.047 | 1.053 |

Then:

```
off_def = clamp((off / max(0.75, opp_def)) − 1, −0.25, +0.25)
base_eff = clamp((off_def_h − off_def_a) × 16 + 0.35 × spread_signal, −6.5, +6.5)
```

Index contribution **before EPA**: TEN@CIN 3.51 · IND@JAX 2.51 · ARI@DAL 0.96. The ±0.25 and ±6.5 clamps did **not** bind on these three. Compression is already in the **0.22-wide W-L map**, not a missing week of PBP.

### B2 — 5g EPA is present, then attenuated

TEN@CIN EPA is large (CIN off +0.142 vs TEN −0.176 → diff **+0.317**). That hits the **±0.30** component clamp (binds). RZ diff +0.218 hits the **±0.20** clamp (binds). Pack spread_signal = **2.81** (cap ±4.25, not binding). Only **0.35 × 2.81 = 0.99** is added to efficiency.

The pack also computes `home_points` / `away_points` (TEN@CIN +2.17 / −1.52). Those are **not added to μ**. Means come only from decomposition. Escalate to Ryan if that allocation was meant to stack; it is the current designed path, not a silent zero of the raw diffs.

### B3 — Designed regression **subtracts** the home edge

`regression_luck` = −(RZ component points) × 1.8, cap ±1.8.

TEN@CIN: CIN RZ TD rate 0.322 vs TEN 0.104 → RZ points 0.96 (after clamp) → **−1.264** on home margin. The model treats CIN’s finishing rate as luck and pulls the line **toward pick'em**.

Budget TEN@CIN (decomp 4.28 → MC 4.44):

| factor | pts | available |
|---|---:|---|
| base_efficiency (W-L + 0.35 EPA) | +4.49 | yes |
| HFA | +1.05 | yes |
| regression_luck | **−1.26** | yes |
| rest / situational | 0 | yes (Sunday 7/7) |
| KAV / injury / weather / travel | 0 | **no — contract/feeds** |
| **μ_h − μ_a** | **4.28** | |

IND@JAX: 2.78 + 1.05 − 0.04 = 3.79 (MC 3.64).  
ARI@DAL: 1.44 + 1.05 − 0.25 = 2.23 (MC 2.38). HFA is almost half the Dallas margin.

### B4 — IF contract cannot admit the rest of the framework

`ALLOWED_INPUT_FIELDS` = 20 efficiency + 8 context. Leftover NflGameInputs fields are **REJECT UNAPPROVED_HL**. So KAV (designed cap 3.5), injury (2.6), travel (1.75), weather (0.55) are structurally zero on this path. Not a dropped column in the panel — the caller forbids them.

Practical Sunday envelope (rest=0): **6.5 + 1.05 + 1.8 = 9.35**. Observed slate max \|IF spread\| = **5.18** (LAC@LAR). DK TEN@CIN −12.5 is **outside the observed IF range** and above every realized IF margin.

### B5 — Totals sit on a 45.3 prior

`base_total_points = 45.3`. Efficiency total cap ±5.0; totals pack cap ±4.2. Slate totals 43.53–46.95.

ARI@DAL: both defenses leak (def EPA allowed 0.111 / 0.156) and both pass-heavy (~0.64). IF total 46.95 vs DK **54.5** (Δ −7.55). The prior + caps cannot reach a mid-50s total. TEN@CIN and IND@JAX totals are close to DK (Δ −0.79 / −1.73) — spread compression is not a totals-unit bug.

### C — low discrimination with an intact pipeline

- Team differences **do** reach the simulator (index diffs, EPA diffs, RZ diffs all nonzero and signed home-centric).
- The mapping from those differences to points is low-gain by design (B), so the forecast is empirically flat vs a market that prices 7–12.5 favorites.
- σ identical on all 13 games (base 9.8 + tiny totals stdev; no injury/weather widen).
- This is **not** “the model has no inputs.” It is “the inputs are W-L + attenuated 5g EPA.”

---

## DATA_PARTIAL / week-7 vintage — tests

| Test | Result |
|---|---|
| Panel `as_of_week` | 7 (required) |
| 32/32 teams present | yes |
| Every team `as_of_week=7` | yes |
| Every team `games_in_window_5=5` | yes |
| Any `2025_prior_used` | **no** |
| T5 source | `team_strength_from_record` on 32/32 |
| Indices = W-L formula | 32/32 exact |
| JAX rolling_as_of | 6 — **intended bye** (`BYE_ROLLING_AS_OF`) |
| CIN games_played | 6 (bye somewhere in W1–W7); rolling 7; as_of 7 |
| `DATA_PARTIAL` meaning | through-**W8** 1/14 complete (TNF only). Operational E1 block. |
| Would W8 PBP fix compression? | Consuming W8 before those games finish is **leakage**. The W-L map + clamps + contract zeros would still bind on a sealed through-W8 panel. |

**Verdict:** treat `DIAGNOSTIC_IF_ONLY` / `DATA_PARTIAL` as **status labels**, not a causal explanation of the pick'em pull. Week-7 is the correct vintage for a W8 pregame IF.

---

## A — wiring items explicitly checked and rejected as the cause

1. **Sign convention** — IF and DK both home-line-negative = home favored. Δspread sign is IF − market.
2. **Home/away assignment** — no flip vs schedule.
3. **Silent zero** — index and EPA diffs nonzero at μ. Not zeroed.
4. **Double HFA** — one +1.05. Rest 0.
5. **Units** — indices ~1.0 (ratio). EPA is per-play (~±0.2). Weights (5.4, 16, …) convert to points. No yards/points mix-up found.
6. **Defaults/fills** — missing KAV/injury/weather are `None` → factor `available=False` → 0 pts. Not imputed ratings.
7. **Blend** — 0. This is Independent Fair. Compression is **pre-blend**.
8. **Unused `home_points`/`away_points`** — diagnostic leftover; means use decomp only. Documented for Ryan; not a flip and not implemented away.

---

## Ryan escalate only (do not implement)

Documented. No code, weight, or blend change in this PR.

1. T5 identity: W-L `team_strength_from_record` vs opponent-adjusted efficiency / KAV as the IF strength SoT.
2. EPA path gain (0.35) and component clamps; whether `home_points`/`away_points` were intended to add to μ.
3. `regression_luck` subtracting RZ rate (it **increases** pick'em pull on high-RZ favorites).
4. Whether the 20-field IF contract should remain KAV/injury-blind.
5. Totals prior 45.3 vs games the market prices mid-50s.

**Ban:** do not retune any of the above to DraftKings or any book. This packet is mechanism, not a matching target.

---

## Bans (this packet)

- No retune. No sportsbook matching. No Odds re-pull.
- No feature / weight / blend / math change.
- ≠edge ≠CLV ≠betting ≠CERT. NFL NO-GO. CERT=0.
- Coming Soon ON. Publication controls unchanged.

---

## Repro

```bash
# Must be run at IF tip 6ca03716 (eval_w8 caller + through-W7 panel).
# This PR is paper-only on deploy-vercel; TRACE.json is the sealed replay.
git checkout 6ca03716fe52930332d5ffba302c312a651980cc
PYTHONPATH=services/model-service python3 data/ops/nfl-if-compression-diag-t4902u/replay_trace.py
```

Uses existing `build_eval_request` → `build_contract_inputs` → `simulate_nfl_game_independent_fair`. Writes `TRACE.json` + `TRACE_*.md`. See `PINS.json` and `SHA256SUMS`.
