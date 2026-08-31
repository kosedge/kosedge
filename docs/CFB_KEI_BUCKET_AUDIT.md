# CFB KEI vs close — spread-bucket audit (Phase 0)

**Phase:** 0 (READ ONLY)  
**Branch:** `cursor/cfb-kei-bucket-audit-3ca1`  
**Base:** `deploy-vercel` @ market-visible (`1ac41f21`+) tip `b1dbd878`  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**KEI / WP / shock / Utah / band 12:** untouched.

---

## W0 KEI rows (all FBS with kei_spread_home) — copy from bundled pack

Source: `apps/web/lib/data/cfb-kei-w0-w1-2026.json` (`as_of=2026-08-31`).

| pair       | kei_spread_home | kei_total | away @ home            |
| ---------- | --------------: | --------: | ---------------------- |
| `UNC@TCU`  |      **−20.39** |     54.15 | North Carolina @ TCU   |
| `SJSU@USC` |          −34.24 |     69.70 | San José State @ USC   |
| `NCSU@UVA` |           −5.30 |     60.58 | NC State @ Virginia    |
| `HAW@STAN` |      **+10.90** |     53.72 | Hawai'i @ Stanford     |
| `NMSU@FSU` |          −16.06 |     61.62 | New Mexico State @ FSU |
| `MEM@UNLV` |           −4.66 |     67.77 | Memphis @ UNLV         |

**n = 6** FBS W0 with KEI (required set complete). FCS W0 in pack have `kei_spread_home=null` (optional).

Finals (official slate `status=final`, scores not invented into KEI):

| pair     | score (away–home) | home margin |
| -------- | ----------------- | ----------: |
| UNC@TCU  | 15–10             |      **−5** |
| SJSU@USC | 26–42             |         +16 |
| NCSU@UVA | 8–34              |         +26 |
| HAW@STAN | 27–37             |         +10 |
| NMSU@FSU | 17–34             |         +17 |
| MEM@UNLV | 27–21             |      **−6** |

TCU KEI still **≈ −20.4**. Do not drag toward −8.5.

---

## Can Odds API historical be called with this key? (endpoint + yes/no)

**Yes.**

|                 |                                                                                                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Endpoint        | `GET https://api.the-odds-api.com/v4/historical/sports/americanfootball_ncaaf/odds?date=…`                                                                                                 |
| Probe           | `date=2026-08-29T16:00:00Z` → **HTTP 200**, ~203 KB body (this environment, `ODDS_API_KEY` set)                                                                                            |
| In-repo usage   | `scripts/odds/enterprise_training_pull.py` (`historical/sports/{sport}/odds`) · `services/model-service/.../cfb_warehouse/odds_lake.py` labels source `the-odds-api-historical-enterprise` |
| Live board path | `apps/web/lib/odds-api.ts` uses **current** `/v4/sports/.../odds` only — not historical                                                                                                    |

Phase 1 may pull historical at kickoff (or last pre-kick snapshot) for W0 closes **without scraping DK**. Label `source=odds_api_historical`.

---

## Existing close archive on disk? (path or none)

**Yes — desk book snapshot (not last-tick Odds close):**

| Path                                | Role                                                            |
| ----------------------------------- | --------------------------------------------------------------- |
| `data/ops/book/cfb-2026-08-29.json` | Week 0 desk ledger · `posted_at=2026-08-29T16:23:44Z` · 8 games |
| Field                               | `market_spread_home` (home-signed)                              |

| pair            |    kei | market_spread_home (snapshot) | trust_reason  |
| --------------- | -----: | ----------------------------: | ------------- |
| UNC@TCU         | −20.39 |                      **−7.5** | absurd_vs_kei |
| SJSU@USC        | −34.24 |                         −38.5 | best          |
| NCSU@UVA        |  −5.30 |                          −4.0 | best          |
| HAW@STAN        | +10.90 |                      **−4.0** | absurd_vs_kei |
| NMSU@FSU        | −16.06 |                         −31.5 | absurd_vs_kei |
| MEM@UNLV        |  −4.66 |                          −4.0 | best          |
| JVST@NDSU (FCS) |      — |                          −6.5 | no_kei        |
| SAC@EMU (FCS)   |      — |                          −8.5 | no_kei        |

**Label if used as close proxy:** `source=desk_book_snapshot_2026-08-29` · `not_official_odds_api_close`.  
Operator journalism boards cited −8.5 TCU / −4 STAN — snapshot has TCU **−7.5** (same band; do not invent −8.5 into code defaults).

Warehouse `closing_lines.parquet` is produced by `scripts/cfb/ingest_historical_warehouse.py` for **past seasons** research — **not** checked in as a 2026 W0 close SoT on this VM.

---

## Bucket edges to use (quote if code has them; else use brief table)

**No CFB KEI-vs-close bucket table in product code.** Trust band is unrelated:

```ts
// apps/web/lib/cfb-trusted-market.ts
export const CFB_ABSURD_VS_KEI_PTS = 12; // trust wipe, not residual buckets
```

**Phase 1 uses the brief table** (|spread| from **close if present else KEI**):

| bucket  | \|spread\| |
| ------- | ---------- |
| pick    | 0–3        |
| short   | 3–7        |
| mid     | 7–14       |
| long    | 14–21      |
| cupcake | 21+        |

Family labels for reading: **A** = cupcake (≥21 book or KEI) · **mid** = 3–14 · **pick** ≤3 · other.

---

## Allowlist

1. `scripts/cfb/cfb_dump_kei_buckets.py` (or `--week 0 --buckets` on dump)
2. `data/ops/cfb-kei-bucket-YYYYMMDD.json`
3. Optional: historical Odds pull **or** desk book `market_spread_home` with explicit `source=` label — **no invented numbers**
4. `docs/CFB_KEI_BUCKET_SCORECARD.md`
5. Tests: BALL@OSU KEI still **−42.2** · TCU KEI still **≈ −20.4**

### Forbidden

`apply_cfb_kei` · power SoT · WP/shock · `if "TCU"` / Hawaii · inventing closes · PLAY card · Utah · NFL/CBB/MLB

---

## Blocker if no close source

**No blocker.** Two real sources exist:

1. Odds API historical (proven 200 in this env)
2. Checked-in desk book `data/ops/book/cfb-2026-08-29.json`

Prefer (1) for kick-time close when Phase 1 runs; fall back to (2) with `desk_book_snapshot` label. Template-only path is unnecessary unless historical fails at Phase 1 runtime.

---

## Phase 0 gate (residuals already visible — measure only)

| pair     |  kei_h | snap mkt_h |  kei − mkt | sign vs cupcake pattern                                |
| -------- | -----: | ---------: | ---------: | ------------------------------------------------------ |
| UNC@TCU  | −20.39 |       −7.5 | **−12.89** | KEI **longer** fav than book (mid miss)                |
| HAW@STAN | +10.90 |       −4.0 | **+14.90** | polarity wild — Stanford market fav, KEI likes Hawai'i |
| SJSU@USC | −34.24 |      −38.5 |  **+4.26** | KEI **shorter** than book (cupcake-direction)          |
| NMSU@FSU | −16.06 |      −31.5 | **+15.44** | KEI shorter than long book                             |
| NCSU@UVA |  −5.30 |       −4.0 |  **−1.30** | mid/short, \|gap\| &lt; 3                              |
| MEM@UNLV |  −4.66 |       −4.0 |  **−0.66** | tight                                                  |

**Hypothesis for Phase 1 scorecard (do not fit):** mid-band TCU/HAW miss is **not** the same sign as Family A cupcake “KEI short of a longer book.” One curve vs two is the measurement deliverable.

Ready for Phase 1 dump + five questions. No line changes.
