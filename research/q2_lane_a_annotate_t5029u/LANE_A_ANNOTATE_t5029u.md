# t5029u Lane A CLEAR_ANNOTATE — implementation note

**DEV_RESEARCH · CERT=0 · NFL NO-GO · DRAFT only.**  
**NOT a forecast quality claim.**

Implements the bounded Lane A **shape** from #683 `eabd49a6` §4 as a **passive reader**, after OWNER card `20dd7940` CLEAR_ANNOTATE / work-package `2db90f76` / guardrails `52c79ee6`.

This is **annotate-only**. It is not a strength join. Alex formula `fa36c679` is **not** authorized. #681 §8 is **not** amended. Stage C is **not** opened.

## Bound (what ran)

1. **Read** #682 sidecar artifact `inputs/q2_asof_sidecar_t5018u.json` (head `7d89a974` / ACCEPT `d17b30fa`). Do not recompute `asof_for_targets`. Do not rewrite `emit_q2_asof_sidecar.py`.
2. **Join** to frozen IF/demo rows by `game_id` if both sides have it; else `Game.key` = `(season, week, home, away)`. No fuzzy name/market/week join.
3. **Emit** DEV*RESEARCH labels beside the IF/demo row. Copy sidecar `q2*\*` fields. Copy IF/demo strength / margin / L0 fields **unchanged**.
4. **Refuse** missing identity, mismatched identity, pin mismatch, leakage (`assert_asof_leakage`), 2024–25, scored `1ee90fac` columns, or any attempt to expand past the frozen 2013 REG W2 manifest.
5. **Stop.** No simulator. No Layer-3. No promotion into `margin_mu`.

## Soft N1–N4 (consumption conditions; still HELD)

- **N1:** Cursor ORDER box tip `09f70480` (chat once cited `8a4bd0ab`) — prefer `09f70480`.
- **N2:** measure this work against wiring card `013ec7f8` (supersedes `1e71808d`).
- **N3:** blended caller-of-record name at this tip is `routes/nfl.py` (not `tasks.py`). This PR does not edit it.
- **N4:** no scored `1ee90fac` columns. Games pin may mention `1ee90fac` as keep-identical provenance only.

Cite additional ORDER / CLEAR tips here when CoS posts them.
