# WEEK_SUBSET_AUDIT — t4915u Lane S

**DEV_RESEARCH / RETRO_FIT exploratory.** CERT=0. NFL NO-GO.
Question: does any apparent signal concentrate in one week or a small subset?
Machine twin: `WEEK_SUBSET_AUDIT.json`.

Week counts (sealed 70): W2=14, W3=16, W4=16, W5=14, W6=10.

Flags below are **descriptive** (pre-specified in the runner; not a cutoff search):

1. Overall Spearman CI excludes 0, but at most one week CI excludes 0 (n_weeks defined ≥ 3).
2. Dropping a week flips LOO Spearman sign vs overall.
3. Dropping a week moves Spearman by ≥ 0.10.
4. One week |ρ|≥0.35 while every other week |ρ|<0.15, and |overall|≥0.15.

On this sample, (1) and (4) never fire for a *useful* overall (every overall CI includes 0). Most flags are (2)/(3) around a near-zero overall — expected with week n=10–16. They do **not** recover a hidden useful signal.

## Per-signal week Spearman vs realized_margin

All week CIs include 0 unless noted.

| Signal | W2 | W3 | W4 | W5 | W6 | LOO min / max | same sign | flag |
|---|---:|---:|---:|---:|---:|---|---|---|
| wl_home_wpct | **0.537**‡ | −0.115 | −0.055 | −0.265 | **−0.679**‡ | −0.242 / 0.118 | no | yes |
| wl_away_wpct | 0.376 | 0.493 | 0.040 | −0.054 | −0.469 | 0.095 / 0.266 | yes | yes |
| wl_diff | 0.100 | −0.436 | −0.038 | −0.124 | −0.038 | −0.201 / 0.003 | no | yes |
| wl_index_off_diff | 0.100 | −0.489 | −0.002 | −0.094 | −0.132 | −0.205 / 0.006 | no | yes |
| wl_index_def_diff | −0.100 | 0.489 | 0.044 | 0.147 | 0.132 | 0.001 / 0.211 | yes | yes |
| wl_index_net | 0.100 | −0.436 | 0.002 | −0.069 | −0.057 | −0.195 / 0.010 | no | yes |
| epa_off_diff † | 0.004 | 0.137 | −0.052 | 0.044 | 0.200 | 0.056 / 0.109 | yes | no |
| epa_def_diff † | −0.156 | −0.479 | 0.371 | 0.042 | −0.200 | −0.245 / 0.059 | no | yes |
| epa_net_diff † | −0.218 | −0.369 | 0.327 | −0.099 | 0.127 | −0.152 / 0.124 | no | yes |
| success_off_diff † | −0.238 | 0.231 | 0.286 | 0.095 | 0.018 | 0.090 / 0.252 | yes | yes |
| success_def_diff † | −0.310 | −0.435 | 0.384 | −0.077 | 0.200 | −0.220 / 0.061 | no | yes |
| success_net_diff † | −0.310 | −0.325 | 0.505 | 0.022 | 0.273 | −0.053 / 0.187 | no | yes |
| matchup_diff_off_epa_5g † | 0.004 | 0.137 | −0.052 | 0.044 | 0.200 | 0.056 / 0.109 | yes | no |
| matchup_diff_success_rate_5g † | −0.310 | −0.325 | 0.505 | 0.022 | 0.273 | −0.053 / 0.187 | no | yes |

† RETRO_FIT / DEV_RESEARCH only (A1).
‡ Week CI excludes 0: `wl_home_wpct` W2 [0.066, 0.874]; W6 [−0.902, −0.155]. Opposite signs. This is a **level** (home win% alone), not a matchup diff, and the two weeks cancel in the pooled 70 (overall 0.024, CI crosses 0). Dropping W2 flips LOO sign (−0.242).

## Material notes (not a search)

- **W-L signed family** (`wl_diff`, `wl_index_off_diff`, `wl_index_net`): pooled ρ ≈ −0.13. Dropping **W3** moves LOO to ~0 and flips sign. W3 itself is ρ ≈ −0.44 with CI still including 0. No week CI excludes 0. Not a concentrated useful signal — a noisy negative pool that W3 tugs.
- **epa_off_diff / matchup_diff_off_epa_5g**: no concentration flag. LOO range only 0.053 (0.056–0.109), all positive, every week CI includes 0. Cleanest stability; still fails the pooled CI test.
- **success_net / matchup success**: W4 ρ=0.505, CI [−0.009, 0.848] (touches 0 from above). Dropping W4 flips LOO sign. Not a sealed useful subset.
- Week SU splits are n=1–11 per side. Several 0.0 / 1.0 rates sit on n≤2. Reported in JSON; not interpretable as discrimination.

## Answer

No frozen signed strength signal shows a week-stable association with realized margin. Apparent week spikes sit inside wide CIs. `wl_home_wpct` is the only series with week CIs excluding 0, and those two weeks **disagree in sign**. Concentration flags on other series are LOO wobble around a null overall, not evidence that “the signal is in week k.”
