# CFB KEI calibrator — design (totals-first)

**Date:** 2026-09-03  
**Owner lock:** Ryan / CoS  
**Status:** Design only. No engine / KEI / pack / tagger code. No `apply_bias_guard` edits. No remat. No this-week pack recut.  
**Diagnosis:** `docs/CFB_TOTALS_HOT_AUDIT.md` (2026-09-01)  
**PLAY sits (tagger only):** `docs/CFB_TOTALS_PLAY_SIT.md`, `docs/CFB_SPREAD_PLAY_SIT.md`  
**Spread unused holdout (Task 2b/2c):** `data/ops/cfb-spread-tag-close-holdout-20260903.md` · `scripts/cfb/run_spread_tag_close_holdout.py`

---

## 1. Why now

PLAY sits hide busy chrome. They do **not** fix KEI identity.

| Surface | Today | Problem |
| --- | --- | --- |
| Totals Tag PLAY | Sat (`CFB_TOTALS_PLAY_ELIGIBLE = false`) | Board still paints Over-drunk KEI totals; LEAN/PASS chrome remains |
| Spread Tag PLAY | Sat (`CFB_SPREAD_PLAY_ELIGIBLE = false`) | Current `apply_bias_guard` is **RED** on unused 2025 Tag PLAY vs close |
| `kei_total` | **Identity** of `model_total` | Research-fair model published as market-facing O/U without a totals guard |
| `kei_spread_home` | Model + versioned bias guard (W0–2) | Guard exists but does not clear PLAY holdout |

W1 live stamp (ops card n=43): mean KEI−market **+8.12**, 37/6 Over/Under. Audit counterfactual: neutralize matchup ratio → gap **+2.16**. Base PPG 25.9 ≈ street; pace is cool. The failure is **matchup-response score inflation on sum-of-scores**, not a PPG knob and not a pace knob.

Sitting PLAY is correct product hygiene until unused holdouts green. The next honest step is a **versioned totals guard** behind the KEI publish boundary — same pattern as spreads — so `model_total` stays research-fair and `kei_total` may diverge only when measured.

This design does **not** unsat totals PLAY or spread PLAY.

---

## 2. Totals-first architecture

### Boundary (mirror spreads)

`apply_cfb_kei` today:

```text
kei_spread_home = model_spread + apply_bias_guard(...)   # W0–2 only
kei_total       = model_total                            # identity — no totals branch
```

Target shape (design; not implemented here):

```text
kei_total = model_total + totals_guard(...)
# OR multiplicative dampen applied to the published sum only
# (see candidate (b) below)
```

| Field | Contract |
| --- | --- |
| `model_total` | Research-fair. Never mutated by the guard. |
| `kei_total` | Published O/U. May diverge only behind a **versioned** totals guard. |
| `spread_home` / `kei_spread_home` | Unchanged by totals work. Totals guard must **not** rewrite team expected points that feed margin. |
| Version stamp | New constant analogous to `BIAS_GUARD_VERSION` (e.g. `cfb-totals-guard-vN-…`). Logged on every KEI row. |
| Week window | W0–2 only (same early window as spread bias guard). Off after week 2 until a later design says otherwise. |
| Flag | Kill switch off until unused GREEN (see §6). |

### `used_in_spread` analog for totals

Spreads already stamp:

- `used_in_spread: true` on published KEI
- `model_used_in_spread: false` on research model

Totals need the same honesty when `kei_total ≠ model_total`:

| Stamp (proposed) | Meaning |
| --- | --- |
| `used_in_total: true` | Published KEI total is the board O/U source |
| `model_used_in_total: false` | Research `model_total` is not the published line |
| `totals_guard_version` | Version string when guard applied; null/identity when off |

Exact field names can land with the implementation PR; the doctrine is: **document divergence**, do not hide it behind an equal Model/KEI paint.

### Hard rule — do not globally lower `MATCHUP_RESPONSE`

`MATCHUP_RESPONSE=1.40` (W1 softened ×0.90 → **1.26**) lives in `priors.py` and feeds **both** team expected points. Lowering it globally recuts **spreads** (margins) as well as totals. Totals Over-drunk and spread PLAY RED are separate problems; a global response cut conflates them and forces a pack remat.

Any matchup-response dampen for totals must act on the **published sum only** (or an equivalent post-compose residual on `kei_total`) such that:

```text
spread_home = away_exp − home_exp   # unchanged
kei_spread_home path                # unchanged by totals guard
```

Additive form that preserves margin identity:

```text
# Illustrative — not a code pick
# Let T0 = home_exp + away_exp = model_total
# Guard applies ΔT to the sum only:
kei_total = T0 + ΔT
# Team midpoint shift optional for display only; do not rewrite model_* scores.
```

Multiplicative “dampen on the sum only” form (candidate b):

```text
# Inflated portion ≈ T0 − T_neutral, where T_neutral uses matchup ratio → 1
# kei_total = T_neutral + λ * (T0 − T_neutral)   # λ ∈ (0,1], totals-only
# Equivalent: kei_total = T0 − (1−λ) * matchup_inflation
# Must not change away_exp − home_exp used for spreads.
```

---

## 3. Candidate guards to evaluate (not pick in code)

Evaluate on the unused-holdout protocol (§4). Do **not** ship a pick from W1 street chase.

### (a) Level offset from unused early-week KEI−close

Constant (or week-bucket) additive haircut on `kei_total` fit from early-week residuals vs close.

- Pros: Simple; mirrors “capped slice of residual” spirit of spread bias guard.
- Cons: Blind to mismatch; peers and cupcakes get the same cut. Audit shows peers still ~+4.5 Over but cupcakes louder — a flat offset may under/over-correct by bucket.
- Role: **Fallback** if (b) fails unused GREEN bars.

### (b) Totals-only matchup-response dampen — **primary hypothesis**

Dampen only the matchup-inflated portion of the **sum**, leaving research `model_total` and spread path intact.

Evidence (audit 2026-09-01):

| Counterfactual | Mean KEI−market |
| --- | ---: |
| Actual W1 | +8.12 |
| Matchup ratio → 1 | **+2.16** (Δ −5.96) |
| Pace → 1 | +8.30 (pace cool) |
| `2 × LEAGUE_TEAM_PPG` | −0.75 vs street |

Primary failure mode is `(off/def)^response` lifting favorite scoring more than it suppresses the dog — both sides still score → sum hot. A totals-only λ on that inflation is the mechanism-aligned fix.

### (c) Mismatch-bucket offsets

Additive offsets by `|model_spread|` buckets (peer / mod / big / cupcake), fit on contaminated seasons.

- Pros: Matches audit shape (cupcake louder).
- Cons: More knobs; easy to overfit contaminated years; still leaves peer Over residual unless combined with (b).
- Role: Secondary research slice; only promote if (b) alone leaves a clear mismatch residual on unused and bucket offsets clear the same GREEN bars without worsening peer MAE.

**Recommendation for first eval:** (b) primary; (a) fallback; (c) exploratory only after (b)/(a).

---

## 4. Unused-holdout protocol

### Join (same as Task 2b)

Reuse the spread Tag close holdout spine:

| Input | Source |
| --- | --- |
| Close + scores | SportsDataverse `espn_cfb_betting` + box / linescores (same join as `run_spread_tag_close_holdout.py`) |
| Model | Hist-cal proxy universe (`run_historical_backtest`) — prior-year ratings + league-avg roster/QB |
| Spread KEI (for any joint runs) | `apply_bias_guard(model, week)` — **do not edit** in this design phase |
| Totals KEI (eval) | Identity baseline vs candidate totals guard on `model_total` |
| Market | **Close only** |

Script pointer: `scripts/cfb/run_spread_tag_close_holdout.py` (spread Tag). Totals eval should twin that join / year labels; implementation is out of scope for this design PR.

### Honesty — proxy KEI ≠ live 2026 roster

Hist-cal proxy understates live Over-drunk. Live 2026 uses real ESPN roster + QB + units + SP+ carry, which widens O/D ratios. Unused 2025 GREEN on proxy is a **necessary** gate, not a claim that live W1 will look identical. Live will be hotter; that is why we do not chase this week’s street and why PLAY stays sat until a separate stricter bar.

### Fit / eval years

| Label | Years | Role |
| --- | --- | --- |
| **Fit (contaminated)** | **2023–2024** | Hist-cal knobs used these as primary; fit totals-guard coefficients here only |
| **Eval (unused)** | **2025** | Primary GREEN/RED. Do not retune from 2025. |

### CLV

CLV unavailable (close-only SDV series; no owned open≠close). **Label it. Do not mint CLV.** Grade vs close only.

### GREEN — enable `kei_total` divergence (W0–2 only)

All three must hold on **unused 2025** early weeks (W0–2), candidate vs identity:

| Gate | Bar |
| --- | --- |
| Level | \|mean(KEI_total − close_total)\| ≤ **1.0** |
| MAE | MAE not worse than identity by **> 0.3** |
| Direction | mean gap not Over-drunk (**>+2**) |

Flag stays **off** until all three clear. Passing this gate allows publishing `kei_total ≠ model_total` behind the versioned guard. It does **not** unsat Tag PLAY.

### GREEN — unsat totals PLAY (separate, stricter)

| Gate | Bar |
| --- | --- |
| Tag O/U PLAY-band ATS vs close | ≥ **52.38%** with **n ≥ 60** (NFL bar) |
| ROI | Beats **−110** |

Until then: `CFB_TOTALS_PLAY_ELIGIBLE` / `TOTALS_PLAY_ELIGIBLE` stay **false**. LEAN ≥ 2.5 may still fire. This design does not flip those flags.

---

## 5. Spreads second

Only after a totals guard is **decided** (shipped or explicitly rejected with unused evidence).

### Baseline to beat

Current `apply_bias_guard` (`cfb-bias-guard-v1-histcal-20260805`) on unused 2025 Tag PLAY vs close (Task 2b/2c):

| Band | n | ATS | ROI (−110) |
| --- | ---: | ---: | ---: |
| PLAY all (≥4.0) | 349 | **48.7%** | **−7.0%** |
| PLAY [4.0, 7.0) | 170 | **49.4%** | **−5.7%** |
| PLAY ≥ 7.0 | 179 | **48.0%** | **−8.3%** |

A new spread guard **v2** must beat **this** unused Tag table — not look busier, not retune the 4.0 floor from a red split, not lock cap7 from RED 2c.

### GREEN — enable / consider unsatting spread PLAY

Eval new guard vs **current** `apply_bias_guard` on unused 2025 Tag PLAY:

| Gate | Bar |
| --- | --- |
| ATS | ≥ **52.4%** with **n ≥ ~200** |
| ROI | **> −110** on PLAY |

If MAE improves but PLAY stays coin-flip → **do not ship**.  
No cap7 lock from the RED 2c split.  
`CFB_SPREAD_PLAY_ELIGIBLE` stays false until unused GREEN **and** Ryan/CoS flip (existing sit doc).

Do **not** edit `apply_bias_guard` in the totals-first implementation pass; spread v2 is a later, separate eval.

---

## 6. Sequence / kill switch

```text
1. Design (this doc)                         ← you are here
2. Totals guard research harness (unused)    ← future PR; flag OFF
3. Pick (b) or fallback (a) on unused GREEN  ← still flag OFF in product
4. Implementation: versioned totals guard
   behind kill switch (default OFF)
5. Enable divergence only when §4 GREEN
   (W0–2); no this-week pack recut
6. Totals PLAY unsat only on stricter §4 bar
7. Spread guard v2 research only after
   totals decision; beat unused Tag table
8. Spread PLAY unsat only on §5 GREEN + CoS
```

**Kill switch:** product flag off until unused GREEN. Identity `kei_total = model_total` remains the live path while the flag is off.

**No this-week pack recut.** Do not chase W1 street. Stamp-at-pull doctrine stands for the current pack.

---

## 7. Out of scope (this design / follow-on research)

| Item | Why out |
| --- | --- |
| W0 slate close / book close ops | Separate ops track |
| Odds / Edge Board cache | Product infra, not calibrator design |
| G5 coverage | Coverage, not KEI residual |
| Calibrator implementation | This PR is markdown only |
| `apply_bias_guard` edits | Spreads second; do not touch |
| Pack remat / KEI mint | No recut |
| Unsat PLAY flags | Separate CoS flip after GREEN |
| Global `MATCHUP_RESPONSE` cut | Recuts spreads |
| Minting CLV from close-only data | Honesty |

---

## File index (context)

| Path | Role |
| --- | --- |
| `docs/CFB_TOTALS_HOT_AUDIT.md` | Why totals are Over-drunk; matchup-response diagnosis |
| `docs/CFB_TOTALS_PLAY_SIT.md` | Totals PLAY sat (tagger) |
| `docs/CFB_SPREAD_PLAY_SIT.md` | Spread PLAY sat (tagger) |
| `data/ops/cfb-spread-tag-close-holdout-20260903.md` | Unused 2025 spread Tag RED table |
| `scripts/cfb/run_spread_tag_close_holdout.py` | Task 2b join / year labels |
| `services/.../cfb_kei.py` | `apply_cfb_kei`, `apply_bias_guard`, identity `kei_total` |
| `services/.../priors.py` | `MATCHUP_RESPONSE`, early soften |
| `data/ops/cfb-kei-rules-2026.md` | House rules / bias guard doctrine |

---

## CoS one-liner

**Totals-first versioned KEI guard (matchup-inflation dampen on the sum only); fit 2023–24 / eval unused 2025; flag off until \|mean gap\|≤1 and MAE/Over bars clear; PLAY stays sat; spreads only after totals decision and must beat the RED unused Tag table — no W1 pack recut.**
