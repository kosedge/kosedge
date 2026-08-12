# NFL Camp Desk — daily first-party product

Date: 2026-08-12  
Branch: `feat/nfl-camp-desk-daily`  
Doctrine: ESPN/beats are sources. KosEdge is the desk. Thin info = PASS.

## Cadence

| Slot | Spec |
|------|------|
| Every day | League wrap + every team with **real** news |
| Full 32 | ≥3–4 pulse passes per week via `content/writers/camp-desk-2026/rotation-queue.json` |
| Empty team day | Skip. No filler essay. |
| Freshness | Newest `desk_date` first. During camp, hide items older than **72h** unless `pinned` |

## Template (cards)

**League wrap** — `Camp Desk — {Weekday}, {Mon} {D}`  
Bottom line · 5–8 storylines · What to watch · Sources

**Team note** — `{Team} camp — {Mon} {D}`  
Bottom line (1–2 sentences) · Key points (2–4) · What to watch (1 line) · Sources  
~80–180 words. Date-only KosEdge byline. No personal writer credit on cards.

Store: `desk_date`, `team_ids[]`, `source_type: kosedge-desk`, `is_material_depth`.

If `is_material_depth`: flag for the existing SoT / depth job. **Do not** publish a new `active_run` from prose.

Market mentions stay **Pass** unless a KEI path already supports a tag. No PLAY/LEAN from camp vibes.

## Source rules

- Cite ESPN / beat / official / trusted X in **Sources**.
- Do not voice-paste third-party headlines as the product.
- No hallucinated quotes.
- Wire (ESPN API) is collapsed on Camp Desk and also 72h-capped.

## Live day shipped

`content/writers/camp-desk-2026/2026-08-12.json`

- League wrap: Wednesday, Aug 12
- Team notes: MIN, ATL, CLE, NYG, GB, CIN
- SoT flags: MIN (Murray named starter), ATL (QB availability still dual), CLE (Fano to LT1; QB still unset)

## Weekly preview delta (scaffold)

Touch **Bottom line / The number / lean** only — no full 32 rewrite.

| Team | Status | Fields | Reason |
|------|--------|--------|--------|
| MIN | flagged | bottom_line, the_number | Murray named starter Tuesday. Preview still reads as an open battle. |
| ATL | flagged | bottom_line | Derby still frozen by availability. Keep Pass. |

No previews rewritten in this PR.

## Smoke

Camp Desk top card is KosEdge-dated **Wednesday, Aug 12** (or yesterday if you are inside 72h), not a week-old ESPN title. PRESEASON badge on. Wire is collapsed.
