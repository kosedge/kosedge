# CFB Official Slate — Week 0 close on desk SoT (2026-08-31)

**Date:** 2026-08-31  
**Slate version:** `cfb-official-slate-v2-dual-20260831`  
**Desk SoT:** `apps/web/lib/data/cfb-official-slate-2026.json`  
**Engine schedule:** `services/model-service/.../cfb_official_schedule_2026.json` (`as_of=2026-08-31`)

## What changed

Week 0 FBS–FBS finals from the engine schedule were written into the UI official-slate artifact (scores + `status=final`). Desk `as_of` stamped `2026-08-31`. Publisher (`scripts/cfb/publish_official_slate_2026.py`) now:

- Takes `as_of` / `slate_version` from the engine schedule pack (never hardcodes 2026-08-17)
- Passes through `home_score` / `away_score` and marks `status=final` when the engine has finals

## Week 0 finals

| Away | Home | Score | Status |
|------|------|------:|--------|
| UNC | TCU | 15–10 | final |
| SJSU | USC | 26–42 | final |
| NCSU | UVA | 8–34 | final |
| HAW | STAN | 27–37 | final |
| NMSU | FSU | 17–34 | final |
| MEM | UNLV | 27–21 | final |

JVST @ fcs:NDSU and fcs:SAC @ EMU remain without scores (not locked on engine).

## Doctrine

Scores only. No power refit. No invented Open/Best. KEI pack unchanged this pass.
