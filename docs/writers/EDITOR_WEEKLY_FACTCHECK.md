# Editor Weekly Fact-Check — NFL previews & articles

**Owner:** Riley Nash (Editor)  
**Cadence:** Every Monday after Camp Desk / preview refresh, and after any market-moving desk publish.

**Scope (LOCKED 2026-08-30):** Market **numbers** only. Do **not** edit voice, prose, or rhythm. Distinct writer voices stay UNLOCKED — see `style-bible.md` / `riley-nash.md`.

**House vs Street (LOCKED 2026-08-30 — Ryan):** Writers are the Kos Edge desk. Lean is HOUSE vs STREET. Riley gates **KEI stamps like juice** — a KEI / house number with no live print is a **numbers bug**. Stamp audits at the board the writer pulled; do not force same-day chase rewrites when the street moved after file time.

## Command

```bash
python scripts/writers/preview-market-factcheck.py \
  --as-of YYYY-MM-DD \
  --write-ops
```

Optional: `--fix` applies market stamps only after human review of the printed mismatch table.

## SoT

| Layer       | Source                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------- |
| Live street | DraftKings win totals (RotoWire / DK Network consensus) — **web scan required**             |
| Live house  | Kos Edge / KEI (or projections / fantasy / futures as relevant) — **pull or mark no print** |
| Model       | `data/ops/nfl-web-launch-bundle.json` → `team_regular_season_outcomes.csv` `expected_wins`  |
| Copy        | `content/writers/season-previews-2026/*.md`                                                 |

## Pass rules (do not skip)

1. Print mismatch table (team · stated · live street · house / KEI · Model E[wins] · Δ).
2. Send the table to the desk owner / user before silent bulk edits when Δ ≥ 1.0 win on the primary market.
3. Fix primary market in title, Market line, Handicapper’s Note, and lede asks — **house + street**.
4. Recalibrate lean: thin |fair − market| (~≤0.5) or material Model↔market conflict → **Pass**.
5. **KEI gate:** if chrome claims a KEI / house number but there is no live print → treat as a numbers bug (clear / mark **no house print**; never leave a minted figure).
6. Do **not** rewrite a filed piece solely because the street moved after stamp time (e.g. total 9 → 9.5). Flag drift for the reader / owner; stamp stays unless the owner asks for a new file.
7. Write `data/ops/nfl-preview-factcheck-YYYYMMDD.md`.

## Integration

Writers ship copy in their own voices. Editor closes the **numbers** loop only (street + house). See `riley-nash.md` and `.cursor/rules/ai-writer-team.mdc`.
