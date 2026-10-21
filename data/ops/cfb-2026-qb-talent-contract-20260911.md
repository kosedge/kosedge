# 2026 QB talent train/serve contract (research diagnostic)

**Date:** 2026-09-11  
**PR:** #539  
**Kill switch:** ON. 2025 sealed. No λ. No MATCHUP_RESPONSE change. No PLAY.

## Conclusion

**pipeline scale mismatch (train/serve skew)**

Hist-cal trained MATCHUP_RESPONSE=1.40 and the QB offense weight on a universe where every QB was unknown@50 (index ≈0.92). Live 2026 serves prior-year counting stats whose natural center is ~67 (index ≈1.20). The attempt-term and/or rank-preserving location diagnostic dropped W1/W2 residual below +3 while recruiting_channel_50 stayed ~+9. That is the same formula on a different feature contract — not evidence that 1.40 should become 1.18, and not a ship of median→50.

Pre-registered gate: attempt-term or rank-preserving location resid < +3.0 while recruiting_channel_50 stays ~+9.

- attempt_term_zero mean resid = **5.0543** → gate FAIL
- loc_shift_established_median_to_50 mean resid = **1.2221** → gate PASS
- recruiting_channel_50 mean resid = **8.958** → control IN BAND
- Mechanism survives this stage: **True**

## 1. Feature-contract audit

When `MATCHUP_RESPONSE` was raised 1.22 → **1.40** (2026-08-05 hist-cal, primary window 2023–24), every team's QB payload was:

```python
{"qb_class": "unknown", "qb_talent": 50.0, "ol_support": 50.0, "weapons_support": 50.0}
```

That produces `qb_situation_index` = **0.92** (class_mult 0.92), not 1.00. 50 is a **missing-value fill**. Counting stats were not an input. The writeup says so: grades efficiency/HFA/PPG/response, *not* that year's portal/QB class.

| Input | Hist-cal (train) | Live 2026 (serve) | Same def? | Same center? | Same missing? | Same time? |
|---|---|---|---|---|---|---|
| qb_talent | constant 50.0 (placeholder) | talent_from_qb_stats(2025 att/yds/td) + low-sample recruiting blend | False | False | False | False |
| pass_attempts / yards / tds | not an input | prior-year counting stats on ESPN-listed QB1 | False | False | False | False |
| completion_pct / efficiency EPA | not an input | not an input (YPA is the only efficiency proxy) | True | None | None | None |
| qb_class / class_mult | unknown → 0.92 for every team | incumbent 1.06 / portal 0.95 / open 0.87 / freshman 0.79 from ESPN class+attempt | False | False | False | False |
| supporting_cast (OL/weapons) | 50 / 50 | derived unit grades (recruiting-anchored ~60) | False | False | None | None |
| recruiting fallback | not used (talent never looks at recruiting) | att<80 blends to recruiting_class_score (floor often 55) | False | None | None | None |
| expert override / W1 confirm | not used | can change class / named QB1; talent still from pack stats | False | None | None | None |
| qb_situation_index downstream | ≈0.92 for every team (unknown@50@cast50) | mean ≈1.20, 58/136 at/above soft knee 1.25 | True | False | None | None |

Live formula (no completion term exists):

```text
if att<=0: 48 (52 if portal)
else: clamp(42 + min(22, att/22) + min(12, ypa·1.1) + min(10, td·0.35) + 2·portal, 35, 96)
if att<80: sqrt(att/80)·stats + (1-w)·recruiting
```

Saturation on official FBS (n=136):

- stats path (att≥80): 101
- zero 2025 attempts: 3
- attempt term at cap 22 (≥484 att): 4
- YPA term at cap 12: 3
- TD term at cap 10: 10
- talent floor 35 / cap 96: 0 / 0
- established-starter talent median: **70.31** (mean 69.6007, sd 8.2211)

A typical established starter is 42 + ~12–18 (attempts) + ~8 (YPA) + ~6 (TD) ≈ **67**. That is the formula's natural location, not a 2026-specific bug inside the arithmetic.

## 2. Term-level ablations (confirmatory W1/W2 books)

Not a fit. Deltas vs frozen. High-total tail = predicted total ≥ 68.

| Variant | QB talent mean/sd/p50 | off-idx mean/sd | mean T | mean/med resid | MAE | tail n / mean resid |
|---|---:|---:|---:|---:|---:|---:|
| frozen | 66.7495/9.0043/67.125 | 1.2143/0.1893 | 61.9579 | 9.1357/8.315 | 9.425 | 18 / 16.3783 |
| attempt_term_zero | 56.4169/4.444/55.776 | 1.1473/0.1702 | 57.8766 | 5.0543/5.13 | 6.319 | 7 / 13.1486 |
| attempt_term_uncapped | 66.6159/9.1297/66.6776 | 1.2131/0.1896 | 61.8884 | 9.0662/8.315 | 9.3582 | 18 / 16.2511 |
| ypa_term_zero | 59.5624/7.9253/59.7392 | 1.1705/0.1863 | 59.3983 | 6.5761/6.265 | 7.4081 | 11 / 15.1655 |
| td_term_zero | 62.6294/6.2656/64.0476 | 1.1924/0.1822 | 60.6359 | 7.8137/7.375 | 8.2828 | 13 / 15.97 |
| portal_bump_zero | 66.0022/8.9679/65.7001 | 1.2093/0.1898 | 61.6573 | 8.8351/8.135 | 9.1702 | 16 / 16.1681 |
| clamp_off | 66.5928/9.0937/66.6776 | 1.2131/0.1895 | 61.886 | 9.0638/8.315 | 9.3558 | 18 / 16.2478 |
| zero_att_default_50 | 66.5928/9.0937/66.6776 | 1.2131/0.1895 | 61.886 | 9.0638/8.315 | 9.3558 | 18 / 16.2478 |
| lowsample_blend_off | 64.8222/10.7741/66.0136 | 1.2012/0.1926 | 61.1767 | 8.3544/7.45 | 8.7571 | 17 / 15.9535 |
| class_to_unknown | 66.7495/9.0043/67.125 | 1.1758/0.1803 | 59.6884 | 6.8662/7.025 | 7.3887 | 11 / 15.5782 |
| class_mult_identity | 66.7495/9.0043/67.125 | 1.2232/0.1775 | 62.4194 | 9.5972/9.2 | 9.685 | 19 / 16.3568 |
| loc_shift_established_median_to_50 | 46.4395/9.0043/46.815 | 1.0786/0.1835 | 54.0443 | 1.2221/0.99 | 4.9983 | 2 / 9.495 |
| loc_shift_all_median_to_50 | 49.6245/9.0043/50.0 | 1.1015/0.1867 | 55.3938 | 2.5716/2.375 | 5.2667 | 3 / 11.0167 |
| hist_contract_qb | 50.0/0.0/50.0 | 1.0601/0.1407 | 52.5623 | -0.2599/-0.295 | 3.9739 | 0 / — |
| recruiting_channel_50 | 64.77/10.7518/66.0137 | 1.1197/0.1526 | 61.7802 | 8.958/7.81 | 9.3398 | 20 / 16.69 |

## 3. Before / after distributions (key variants)

### frozen

- qb_talent: mean 66.7495 sd 9.0043 p10 54.615 p50 67.125 p90 78.625
- offense_index: mean 1.2143 sd 0.1893 p10 0.9958 p50 1.1955 p90 1.4732

### attempt_term_zero

- qb_talent: mean 56.4169 sd 4.444 p10 51.4042 p50 55.776 p90 62.3128
- offense_index: mean 1.1473 sd 0.1702 p10 0.9486 p50 1.1321 p90 1.3895

### loc_shift_established_median_to_50

- qb_talent: mean 46.4395 sd 9.0043 p10 34.305 p50 46.815 p90 58.315
- offense_index: mean 1.0786 sd 0.1835 p10 0.8812 p50 1.044 p90 1.3298

### hist_contract_qb

- qb_talent: mean 50.0 sd 0.0 p10 50.0 p50 50.0 p90 50.0
- offense_index: mean 1.0601 sd 0.1407 p10 0.8828 p50 1.0457 p90 1.2726

### recruiting_channel_50

- qb_talent: mean 64.77 sd 10.7518 p10 50.0932 p50 66.0137 p90 78.6277
- offense_index: mean 1.1197 sd 0.1526 p10 0.9157 p50 1.0983 p90 1.3381

## 4. What this is not

- Median→50 improving W1/W2 is **not** a ship criterion. If it only works because it restores the hist-cal *fill* on a path that now has real stats, that is pipeline mismatch evidence.
- Not a λ / MATCHUP_RESPONSE / PLAY proposal.
- 2025 residuals were not scored.

JSON: `cfb-2026-qb-talent-contract-20260911.json`
