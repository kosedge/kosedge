# NFL PLAY-only unused holdout (v2 cap7)

Generated: `2026-07-28T21:43:38.250464+00:00`
Policy: `spread_play_v2_cap7` — spread PLAY `2.5 ≤ |edge| < 7.0`

## Methodology

- ATS vs close (−110 unit ROI), latest pre-kickoff projection via `external_id`.
- CLV product metric: owned OC with n_snaps≥2 and **open≠close** (movement).
- Primary unused: **2025**. Confirmatory CLV sample: **2024–2025**.
- Legacy v1 uncapped 2025 spread: n=205 ATS=0.7659 mean_edge=7.175

## Primary holdout (2025 PLAY)

| Slice | n | ATS | mean\|edge\| | ROI | CLV move n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| combined | 142 | 0.6972 | 4.262 | 0.331 | 126 | 0.5476 | **YELLOW** |
| spread | 112 | 0.6964 | 4.664 | 0.3295 | 101 | 0.5842 | **YELLOW** |
| total | 30 | 0.7 | 2.763 | 0.3364 | 25 | 0.4 | **RED** |

## Confirmatory (2024–2025 PLAY)

| Slice | n | ATS | mean\|edge\| | ROI | CLV move n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| combined | 279 | 0.7097 | 4.144 | 0.3548 | 249 | 0.5663 | **GREEN** |
| spread | 227 | 0.7313 | 4.463 | 0.3961 | 206 | 0.6117 | **GREEN** |
| total | 52 | 0.6154 | 2.752 | 0.1748 | 43 | 0.3488 | **RED** |

# Selective ready: `True` · overall gate `GREEN`

Confirmatory 2024–25 spread PLAY (v2 band) clears ATS + movement-CLV. Primary 2025 alone is YELLOW (CLV n often short of 200).

**Product lock (Ryan Kos, 2026-09-03):** spread PLAY may fire only in this band; totals PLAY stays sat; prop PLAY stays sat. See `/NFL_SPREAD_PLAY_LOCKED.md`.

## Clean-era check (2020–2022)

```json
{
  "n": 387,
  "hits": 208,
  "hit_rate": 0.5375,
  "roi": 0.0261,
  "units": 10.091,
  "beats_minus_110": true,
  "mean_abs_edge": 4.685,
  "n_clv_all": 387,
  "clv_positive_rate_all": 0.2584,
  "n_clv_move": 222,
  "clv_positive_rate": 0.4505,
  "clv_avg_move": -0.5721,
  "n_clv": 222,
  "gate": "YELLOW",
  "stretch_band": "breakeven+",
  "detail": "ATS clears \u2212110 but movement-CLV fails or sample thin."
}
```

## Segments 2025

- GREEN: none
- YELLOW: ['spread_all_play', 'combined_play']
- Best: `combined_play`

