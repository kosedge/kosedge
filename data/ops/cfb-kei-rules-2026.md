# CFB KEI rules — 2026 season source of truth

Version: `cfb-kei-v1.0-2026w0`  
Bias guard: `cfb-bias-guard-v1-histcal-20260805`  
Date: 2026-08-17

## Doctrine

- **Model** = research fair. Never gut-edited. `used_in_spread=false`.
- **KEI** = published line = model + versioned menu + measured bias guard. `used_in_spread=true`.
- **Market** = information only. Never auto-author of KEI.
- **Edge / Tag** = KEI vs best market only.
- Early season (calendar weeks 0–2): PLAY at **4.0** pts, LEAN at **2.5**, PASS default.
- No volume targets. Honest PASS is success.

## Handicap menu (order)

| Factor | KEI action |
|--------|------------|
| QB situation | In model compose — not restacked |
| Trench / OL | In model units — not restacked |
| Returning production / portal / experience | In roster_strength — not restacked |
| Coaching continuity | In model week adj — not restacked |
| HFA / neutral / night | In model — not restacked |
| Rest / travel | Label when missing. Apply only with a current-path fact. |
| Injuries / outs | Packaged depth only. Banner: not a live injury feed. |
| **Bias guard** | Only default numeric KEI delta. See below. |
| Market disagreement | If \|KEI − open\| ≥ 6 → INVESTIGATE in drivers. Do not move KEI to open. |

## Bias guard

Hist-cal 2026-08-05: home favorites ~+6.8 too soft vs close; home dogs too bullish. We do **not** copy the close.

- Home favorite: −1.20 pts (larger favorite), cap 1.50
- Home dog: +1.00 pts, cap 1.50
- Remaining shorts (\|line\| 1.0–7.5): shrink 12% toward pick'em, cap 1.25
- After week 2: guard off

Held diagnostic (8 short home-favs, books 4.5 pts bigger than model): raw model would PLAY vs that book; KEI does not. Signs preserved. Not a long-run ATS profit claim.

## FCS

No FBS-equivalent precision. PASS. No invented KEI.

## Intel cadence

Midweek report → Friday lock → gameday inactives. Material QB/OL news → SoT note → KEI reprice same day. Model core does not change midweek.

## Proof

Every published KEI should log model snapshot + open when captured (`proof_layer`, sport=cfb). Close + result + CLV + ATS grade via existing CFB performance endpoints.
