# Truth-chain audit — schedule → UI → articles

**Owner:** Engineering (plumbing) + CoS (product/UI article surface)  
**Status:** Step 1 scaffold (2026-09-04) — inventory + fixture CI entry  
**Hard constraints:** Do **not** invent KEI, rematerialize, or flip `CFB_*_PLAY_ELIGIBLE`.

This document is the map. The harness (`scripts/ops/truth_chain_audit.py`)
inventories public surfaces that show model numbers, tags, QBs, or market lines
and checks that required provenance fields exist on fixture payloads.

---

## Chain (authoritative order)

```text
schedule → teams → players → injuries → transactions
       → market (book feed)
       → model run (pack / bundle / KEI pull — never mint)
       → UI surfaces (boards, hubs, team pages)
       → articles / desk copy (Editor Fact Gate for NEW filings)
```

| Stage            | What must be true                                                                 | Typical SoT / provenance                                      |
| ---------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Schedule         | Games exist with season/week/date; no orphan odds                                 | League schedule pack / official slate                         |
| Teams            | Abbr ↔ full name stable                                                           | Team dictionary / season engine team table                    |
| Players          | Identity ids stable; no invented names                                            | Depth / roster universe                                       |
| Injuries         | Status stamped with as-of; rumor ≠ SoT                                            | Injury report ingest                                          |
| Transactions     | Moves stamped; Camp Desk for named claims                                         | Transaction ingest + Camp Desk                                |
| Market           | Book line with book + as-of; trust gate before edge                               | Odds API cache / warehouse; CFB `trustCfbMarket`              |
| Model run        | Number carries **run id** and/or **as-of** when required                          | Pack id, bundle stamp, KEI pull timestamp                     |
| UI               | Display uses same tagger / SoT as Edge Board; no hardcoded PLAY bypass            | `cfbEdgeTag`, NFL decision engine, packaged depth             |
| Articles         | NEW copy → Editor Fact Gate; filed stamps stay                                    | `docs/writers/EDITOR_FACT_GATE.md`                            |

---

## Public surface inventory (step 1)

Surfaces that show **model numbers, tags, QBs, or market**. Expand in later steps.

| Route / surface                         | Fields shown                         | SoT / tagger                                              | Provenance required                          |
| --------------------------------------- | ------------------------------------ | --------------------------------------------------------- | -------------------------------------------- |
| `/` homepage Edge Board (`variant=home`)| Edge pts + Tag                       | `buildHomePreviewRows` → `cfbEdgeTag`                     | Sit flags; no stamped PLAY                   |
| `/pro/cfb/edge-board` + assemble API    | KEI, market, edge, tag               | `applyCfbTrustedMarketToRows` + `cfbEdgeTag`              | Trust reason; no PLAY while sit flags false  |
| `/pro/cfb/edges`                        | Matchup edges                        | Same CFB trusted-market path                              | As-of / assemble provenance when live        |
| `/pro/*/odds` (Odds Compare)            | Book lines                           | Odds feed                                                 | Empty state must not leak ops/env language   |
| `/pro/nfl/model` + team overview        | Season model / QB context            | Packaged depth + season-engine launch bundle              | Depth snapshot id; model pack stamp          |
| `/pro/nfl/teams/[team]/*`               | Depth QB1, camp claims               | `nfl_depth_chart_2026_w1.json` (packaged); Camp Desk live | Snapshot id; Camp as-of                      |
| NFL Edge Board / fair lines             | Fair, market, action                 | `nfl-edge-board-from-fair-lines` + dead-tier remap        | Lines as-of; publish≡action after remap      |
| Writer previews / articles              | Market + Model numbers               | Bundle `expected_wins` + street at file time              | Editor Fact Gate; no minted KEI              |

### NFL season-model QB SoT (named for deferred fix)

Authoritative **packaged** QB1 universe for `/pro/nfl/model` and team depth/overview:

1. **Canonical file (model-service):**  
   `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json`
2. **Web package mirror:**  
   `apps/web/lib/fantasy/data/nfl-depth-chart-2026-w1.json`  
   (`snapshot_id`: `nfl-depth-2026-w1-20260813T120000Z`)
3. Honesty stamp: `apps/web/lib/nfl-surface-honesty.ts` — packaged depth is **not** live Camp Desk.

Named QB1s in that snapshot (2026-09-04 audit): ATL=Tua Tagovailoa, PIT=Aaron Rodgers, CLE=Deshaun Watson, LV=Kirk Cousins, NYJ=Geno Smith, MIA=Malik Willis. Full QB universe refresh is **deferred** — do not invent QBs in UI.

---

## Harness

```bash
# Fixture-only (CI-safe; no live prod secrets)
python3 scripts/ops/truth_chain_audit.py \
  --fixture data/ops/truth-chain-fixtures/step1_inventory.json
```

**FAIL when:** a fixture number field that declares `requires_run_id` or `requires_as_of` lacks that provenance.

**PASS when:** inventory is complete and every gated number carries required provenance keys on the fixture.

Step 2+ (not this PR): crawl live assemble payloads, homepage HTML tags, and article stamps under the same schema.

---

## Related doctrine

- `docs/CFB_SPREAD_PLAY_SIT.md` / `docs/CFB_TOTALS_PLAY_SIT.md` — PLAY sit
- `docs/writers/EDITOR_FACT_GATE.md` — NEW copy fact gate
- `AGENTS.md` — production branch contract (`deploy-vercel` only)
