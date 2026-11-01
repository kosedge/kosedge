# t5075u G2 DIAGNOSTIC — frozen protocol (PRE-COMPUTE)

**CERT=0 · NFL NO-GO · DRAFT #686 family · research only.**
Cite OWNER_CLEAR **00159454** / CoS ORDER **2ce38509** under **d7e0a6bc**.
Joint consume head **43b5a622**. Not a new planning cycle.

This protocol and the companion `FROZEN_MANIFEST.json` are bound
**before** any outcome parse or metric execution against `50bda875`.
Alex pre-compute verify is required before ONE diagnostic run.
Do not treat this file as a look, a second Q2 EVAL, or a cert lift.

## Role

Consumed-data **descriptive** diagnostics only.

- No PASS / FAIL-as-cert / edge / retune / selection / PLAY / LEAN
- No fitting, forecast regen, IF-draw synthesis, or candidate rewrite
- No Q2 EVAL `03a4dd90` reopen; no LOOK invocation; no counter rewrite
- No other seasons or evaluations scored
- 34 COND and J14 NOT_EMITTED stay visible

## Pins (re-hashed on #686 @ 43b5a622)

| Prefix | Path |
|---|---|
| `5076421e` | `joint/artifacts/Q2S_JOINT_W7W17.json` |
| `ce6b1244` | `joint/artifacts/Q2S_JOINT_DRAWS_W7W17.npz` |
| `32e97434` | `phase4/artifacts/IF_MUS_W7W17.json` |
| `55d8c8bc` | `phase4/artifacts/q2s_rows_w7w17.json` |
| `50bda875` | `pins/outcomes_2013_2022_score_only.csv` |

Identity boundary (cited, not re-invoked):

| Tip | Role |
|---|---|
| `8bea4ca3` | LOOK (cited tip; not a file on this tree) |
| `bd51eb3e` | ACCEPT (cited tip; not a file on this tree) |
| `013d270a` | `phase4/artifacts/LOOK_CONSUMED.json` (checksum only) |
| `03a4dd90` | Q2 EVAL — CLOSED |

## Identity + read boundary

- Join key = `(season, week, home, away)` exactly as the consumed look.
- Eligible set = the **same 141** 2017 REG W7–17 identities on the joint
  consume artifact (joint row order). 24 T2 sealed stay out.
- `50bda875` may be byte-hashed at freeze. It is **parsed only after**
  Alex pre-compute GO binds this manifest. Only the 141 identities enter
  metrics. Other CSV rows (other seasons/weeks) are not scored.
- Refuse: n≠141, duplicates, missing eligible keys, identities outside
  2017 W7–17, 2024–25 protected open, EVAL-season scoring, examined-70
  reopen, silent subset.
- Missing pin or identity mismatch → STOP, record blocker. Fallback =
  approved pin / identity / read-boundary **fixtures**. No invented data.

## Forecast fields (persisted; do not regenerate)

| Source | Margin | Total | Home-win p | Distribution |
|---|---|---|---|---|
| Joint | `mean_D` | `mean_S` / `total_raw` | `home_wp` | paired `H`,`A` draws |
| Point-candidate | `margin_mu_q2s` | **UNAVAILABLE** | **UNAVAILABLE** (`no_candidate_probabilities`) | none |
| IF | `if_margin_mu` | `if_total_mu` | `if_forecast_wp_home` | **UNAVAILABLE** (`IF_MUS` means-only; do not regen) |

## Actuals (after Alex GO only)

- `margin = home_score − away_score`
- `total = home_score + away_score`
- `home_win = 1` if margin>0 else `0` if margin<0
- Actual ties (`margin==0`) are **excluded** from binary scores; tie count reported

## Metrics (descriptive)

1. **MAE / RMSE** on margin and total for joint; point-candidate and IF
   counterparts **where persisted**. Missing → `UNAVAILABLE`.
2. **Paired descriptive diffs** (not a selection rule):
   - MAE: `mean(|pred_a−act| − |pred_b−act|)` (= MAE_a − MAE_b)
   - RMSE: difference of RMSEs (RMSE is not a per-game mean)
   - Pairs: joint−IF, joint−point, point−IF when both sides exist
3. **Fixed per-week summaries** for REG weeks **7–17** inclusive (11
   blocks). Missing/empty week = refuse. Per block: n, MAE/RMSE and
   paired MAE diffs where available. No per-week bootstrap. No sign rule.
4. **Home-win Brier + log loss** from **persisted** probabilities.
   - Exclude actual ties; report `n_ties` and `n_binary`
   - Log-loss clip only: `[1/(2N), 1−1/(2N)]` with **N=4000**
     (`eps=1/8000`). Originals retained. Report `n_probs_clipped`.
   - Disclose: IF WP stored at **legacy 4-decimal** rounding; joint WP =
     `#(D>0)/N` with forecast-side D=0 counted away (not an actual-tie rule)
5. **Joint draws only:** empirical CRPS on margin `H−A` and total `H+A`;
   equal-tail **50/80/90%** coverage + mean width.
   - CRPS(F̂,y) = n⁻¹ Σ|xᵢ−y| − (2n²)⁻¹ ΣᵢΣⱼ|xᵢ−xⱼ|
   - Equal-tail α: quantiles `((1−α)/2, 1−(1−α)/2)`
6. IF distribution comparison = **UNAVAILABLE**. Do not synthesize draws.

## Execution chain

1. Locate pins by sha256 prefix @ `43b5a622`
2. Freeze input + code hashes + this protocol (**this step**)
3. STOP — Alex pre-compute verify
4. Metrics + synthetic/guard tests (no real outcome join in tests)
5. After Alex GO bound to this manifest: **ONE** diagnostic execution
6. STOP — Alex independent RO → CoS scoped ACCEPT
7. `CURSOR_DONE` is written only if that one run completes

Default `run.py` without a matching Alex GO receipt = refuse, no parse.

## Hard stops

No merge / deploy / C10 / cert / pub / betting lift.
No new pulls / P2 / source / spend.
No shadow scoring / live capture.
No 2024–25 protected open.
Original forecast artifacts are not rewritten.
