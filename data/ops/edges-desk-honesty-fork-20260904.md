# Edges desk honesty fork — #8 Phase C last slice

**Date:** 2026-09-04  
**Cite:** Phase B candidate #5 · #4 E4 · Edge Board Product Center  
**Branch tip base:** quarantine scrub @ `3550921b`

## Symptom

`/pro/{sport}/edges` (shared SSR — CFB/NBA/siblings) shipped **model-vs-market** framing that forked Edge Board research-fair honesty:

| Surface | Before |
| --- | --- |
| `/pro/cfb/edges` | “Thresholded model-vs-market separations…” + “matchups with model-vs-market separation…” |
| `/pro/nba/edges` | same shared copy |
| `/edge-board/cfb` | “KEI vs market. Model is research-fair. Tags never use Model vs market.” |
| `/pro/nfl/edges` | H1 “Model vs Market Edges” |

## Fix (bounded honesty only)

- Shared constants: `apps/web/lib/edges-desk-honesty.ts`
- Shared page + NFL client consume demoted-desk framing; Edge Board remains decision center
- Routes stay **live** (no 308 of `/pro/{sport}/edges`)
- Source-lock: `apps/web/__tests__/lib/edges-desk-honesty.test.ts`

## Locks honored

No redesign · no thrash · no remat · no PLAY invent · no Conf invent · no props philosophy UI · CoS owns merge.
