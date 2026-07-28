# NFL PLAY-only unused holdout

Generated: `2026-07-28T20:34:06.373270+00:00`

## Pre-registered policy

- Spread PLAY: `|edge| ≥ 2.5`
- Total PLAY: `2.5 ≤ |edge| < 3.0`
- Primary holdout season: **2025**
- Floors: ATS ≥ 0.5238 (stretch 0.55), CLV+ ≥ 0.55 with n≥200 (segment soft n≥40)

## Primary holdout (2025 PLAY)

| Slice | n | ATS | ROI | CLV n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| combined | 232 | 0.7586 | 0.4483 | 119 | 0.4958 | **YELLOW** |
| spread | 206 | 0.7621 | 0.455 | 105 | 0.5333 | **YELLOW** |
| total | 26 | 0.7308 | 0.3951 | 14 | 0.2143 | **RED** |

**Overall selective gate:** `YELLOW` · betting_product_selective_ready=`False`

Best shrink segment: `spread_edge_5.0_plus` → `{
  "n": 138,
  "hits": 115,
  "hit_rate": 0.8333,
  "roi": 0.5909,
  "units": 81.545,
  "beats_minus_110": true,
  "n_clv": 69,
  "clv_positive_rate": 0.5072,
  "clv_avg": 0.0217,
  "gate": "YELLOW",
  "stretch_band": "60pct+",
  "detail": "ATS clears \u2212110 but CLV fails or missing."
}`

## GREEN / YELLOW segments (2025)

- GREEN: none
- YELLOW: ['spread_all_play', 'spread_edge_5.0_plus', 'spread_home', 'spread_away', 'combined_play']

## Prior evidence (2020–2024 PLAY, not unused)

```json
{
  "combined": {
    "n": 1073,
    "hits": 669,
    "hit_rate": 0.6235,
    "roi": 0.1903,
    "units": 204.182,
    "beats_minus_110": true,
    "n_clv": 633,
    "clv_positive_rate": 0.3507,
    "clv_avg": -0.4163,
    "gate": "YELLOW",
    "stretch_band": "60pct+",
    "detail": "ATS clears \u2212110 but CLV fails or missing."
  },
  "spread": {
    "n": 980,
    "hits": 621,
    "hit_rate": 0.6337,
    "roi": 0.2097,
    "units": 205.545,
    "beats_minus_110": true,
    "n_clv": 600,
    "clv_positive_rate": 0.35,
    "clv_avg": -0.455,
    "gate": "YELLOW",
    "stretch_band": "60pct+",
    "detail": "ATS clears \u2212110 but CLV fails or missing."
  },
  "total": {
    "n": 93,
    "hits": 48,
    "hit_rate": 0.5161,
    "roi": -0.0147,
    "units": -1.364,
    "beats_minus_110": false,
    "n_clv": 33,
    "clv_positive_rate": 0.3636,
    "clv_avg": 0.2879,
    "gate": "RED",
    "stretch_band": null,
    "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
  }
}
```

## Walk-forward by season (locked tags)

```json
{
  "2020": {
    "combined": {
      "n": 206,
      "hits": 115,
      "hit_rate": 0.5583,
      "roi": 0.0658,
      "units": 13.545,
      "beats_minus_110": true,
      "n_clv": 119,
      "clv_positive_rate": 0.2269,
      "clv_avg": -1.6975,
      "gate": "YELLOW",
      "stretch_band": "55pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "spread": {
      "n": 196,
      "hits": 109,
      "hit_rate": 0.5561,
      "roi": 0.0617,
      "units": 12.091,
      "beats_minus_110": true,
      "n_clv": 116,
      "clv_positive_rate": 0.2241,
      "clv_avg": -1.7414,
      "gate": "YELLOW",
      "stretch_band": "55pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "total": {
      "n": 10,
      "hits": 6,
      "hit_rate": 0.6,
      "roi": 0.1455,
      "units": 1.455,
      "beats_minus_110": true,
      "n_clv": 3,
      "clv_positive_rate": 0.3333,
      "clv_avg": 0.0,
      "gate": "RED",
      "stretch_band": "60pct+",
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    }
  },
  "2021": {
    "combined": {
      "n": 226,
      "hits": 113,
      "hit_rate": 0.5,
      "roi": -0.0455,
      "units": -10.273,
      "beats_minus_110": false,
      "n_clv": 121,
      "clv_positive_rate": 0.2562,
      "clv_avg": -0.5413,
      "gate": "RED",
      "stretch_band": null,
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    },
    "spread": {
      "n": 209,
      "hits": 106,
      "hit_rate": 0.5072,
      "roi": -0.0318,
      "units": -6.636,
      "beats_minus_110": false,
      "n_clv": 113,
      "clv_positive_rate": 0.2478,
      "clv_avg": -0.5796,
      "gate": "RED",
      "stretch_band": null,
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    },
    "total": {
      "n": 17,
      "hits": 7,
      "hit_rate": 0.4118,
      "roi": -0.2139,
      "units": -3.636,
      "beats_minus_110": false,
      "n_clv": 8,
      "clv_positive_rate": 0.375,
      "clv_avg": 0.0,
      "gate": "RED",
      "stretch_band": null,
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    }
  },
  "2022": {
    "combined": {
      "n": 210,
      "hits": 118,
      "hit_rate": 0.5619,
      "roi": 0.0727,
      "units": 15.273,
      "beats_minus_110": true,
      "n_clv": 108,
      "clv_positive_rate": 0.2222,
      "clv_avg": -0.912,
      "gate": "YELLOW",
      "stretch_band": "55pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "spread": {
      "n": 188,
      "hits": 108,
      "hit_rate": 0.5745,
      "roi": 0.0967,
      "units": 18.182,
      "beats_minus_110": true,
      "n_clv": 99,
      "clv_positive_rate": 0.2323,
      "clv_avg": -0.9596,
      "gate": "YELLOW",
      "stretch_band": "55pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "total": {
      "n": 22,
      "hits": 10,
      "hit_rate": 0.4545,
      "roi": -0.1322,
      "units": -2.909,
      "beats_minus_110": false,
      "n_clv": 9,
      "clv_positive_rate": 0.1111,
      "clv_avg": -0.3889,
      "gate": "RED",
      "stretch_band": null,
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    }
  },
  "2023": {
    "combined": {
      "n": 206,
      "hits": 148,
      "hit_rate": 0.7184,
      "roi": 0.3716,
      "units": 76.545,
      "beats_minus_110": true,
      "n_clv": 167,
      "clv_positive_rate": 0.479,
      "clv_avg": 0.1587,
      "gate": "YELLOW",
      "stretch_band": "60pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "spread": {
      "n": 186,
      "hits": 137,
      "hit_rate": 0.7366,
      "roi": 0.4062,
      "units": 75.545,
      "beats_minus_110": true,
      "n_clv": 164,
      "clv_positive_rate": 0.4695,
      "clv_avg": 0.1037,
      "gate": "YELLOW",
      "stretch_band": "60pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "total": {
      "n": 20,
      "hits": 11,
      "hit_rate": 0.55,
      "roi": 0.05,
      "units": 1.0,
      "beats_minus_110": true,
      "n_clv": 3,
      "clv_positive_rate": 1.0,
      "clv_avg": 3.1667,
      "gate": "RED",
      "stretch_band": "55pct+",
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    }
  },
  "2024": {
    "combined": {
      "n": 225,
      "hits": 175,
      "hit_rate": 0.7778,
      "roi": 0.4848,
      "units": 109.091,
      "beats_minus_110": true,
      "n_clv": 118,
      "clv_positive_rate": 0.5085,
      "clv_avg": 0.6441,
      "gate": "YELLOW",
      "stretch_band": "60pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "spread": {
      "n": 201,
      "hits": 161,
      "hit_rate": 0.801,
      "roi": 0.5292,
      "units": 106.364,
      "beats_minus_110": true,
      "n_clv": 108,
      "clv_positive_rate": 0.5185,
      "clv_avg": 0.6713,
      "gate": "YELLOW",
      "stretch_band": "60pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "total": {
      "n": 24,
      "hits": 14,
      "hit_rate": 0.5833,
      "roi": 0.1136,
      "units": 2.727,
      "beats_minus_110": true,
      "n_clv": 10,
      "clv_positive_rate": 0.4,
      "clv_avg": 0.35,
      "gate": "RED",
      "stretch_band": "55pct+",
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    }
  },
  "2025": {
    "combined": {
      "n": 232,
      "hits": 176,
      "hit_rate": 0.7586,
      "roi": 0.4483,
      "units": 104.0,
      "beats_minus_110": true,
      "n_clv": 119,
      "clv_positive_rate": 0.4958,
      "clv_avg": -0.0504,
      "gate": "YELLOW",
      "stretch_band": "60pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "spread": {
      "n": 206,
      "hits": 157,
      "hit_rate": 0.7621,
      "roi": 0.455,
      "units": 93.727,
      "beats_minus_110": true,
      "n_clv": 105,
      "clv_positive_rate": 0.5333,
      "clv_avg": 0.1048,
      "gate": "YELLOW",
      "stretch_band": "60pct+",
      "detail": "ATS clears \u2212110 but CLV fails or missing."
    },
    "total": {
      "n": 26,
      "hits": 19,
      "hit_rate": 0.7308,
      "roi": 0.3951,
      "units": 10.273,
      "beats_minus_110": true,
      "n_clv": 14,
      "clv_positive_rate": 0.2143,
      "clv_avg": -1.2143,
      "gate": "RED",
      "stretch_band": "60pct+",
      "detail": "ATS below \u2212110 or sample below MIN_SEGMENT_N."
    }
  }
}
```

## Honesty

Full PLAY universe gate=YELLOW; best shrink segment=spread_edge_5.0_plus (YELLOW). Do NOT claim ~60% or subscription GREEN unless a pre-registered segment clears ATS+CLV with adequate n.

