# CFB Official Slate — in-house dual-source

**Date:** 2026-08-17
**Slate version:** `cfb-official-slate-v2-dual-20260817`
**Desk SoT:** `apps/web/lib/data/cfb-official-slate-2026.json` (copy in model-service)

## Sources

| Role | Source | Notes |
|------|--------|--------|
| Primary | ESPN public team schedule (`espn_team_schedule_public`) | Packaged `2026-08-13` · 889-game season file · not live-scraped this pass |
| Fact-check | The Odds API NCAAF events | Structured `/v4/sports/americanfootball_ncaaf/events` · already in stack |
| Tried / not used | CFBD `/games` | 401 without `CFBD_API_KEY` |
| Tried / not used | NCAA.com scoreboard JSON | 404 for 2026 week paths |
| Tried / not used | SportsDataverse 2026 parquet | Not a live 2026 schedule publish |
| Tried / not used | Wikipedia season page | Featured kickoffs only, not full FBS |

## Counts

| Week | Primary ESPN | Fact-check matched | Published | FBS–FBS |
|------|-------------:|-------------------:|----------:|--------:|
| 0 | 8 | 8 | 8 | 6 |
| 1 | 89 | 43 | 89 | 43 |
| **Total** | **97** | **51** | **97** | **49** |

Secondary events pulled: 111 · name-matched: 64
Fact-check error: none

## Conflicts (needs_review, ESPN time kept)

_None._

## Only in primary (published as `unconfirmed_secondary`)

- fcs:BCU @ UCF (W1)
- fcs:MRMK @ DEL (W1)
- fcs:WES @ KENNESAW (W1)
- fcs:ALB @ BUFF (W1)
- fcs:UAPB @ MIZZ (W1)
- fcs:EIU @ MINN (W1)
- fcs:IDHO @ UTAH (W1)
- fcs:INST @ PUR (W1)
- fcs:NCAT @ GAST (W1)
- fcs:LIU @ KU (W1)
- fcs:UNH @ SYR (W1)
- fcs:LAF @ CONN (W1)
- fcs:BRY @ ARMY (W1)
- fcs:TAR @ BGSU (W1)
- fcs:YSU @ UK (W1)
- fcs:SEMO @ ISU (W1)
- fcs:DUQ @ AFA (W1)
- fcs:URI @ TEM (W1)
- fcs:TNST @ UGA (W1)
- fcs:FUR @ TENN (W1)
- fcs:CIT @ CHAR (W1)
- fcs:TOW @ NAVY (W1)
- fcs:RGV @ UTSA (W1)
- fcs:ME @ APP (W1)
- fcs:UNA @ ARK (W1)
- fcs:ALCN @ USM (W1)
- fcs:NORF @ ODU (W1)
- fcs:APSU @ VAN (W1)
- fcs:ACU @ TTU (W1)
- fcs:NICH @ KSU (W1)
- fcs:IDST @ UTAHST (W1)
- fcs:HCU @ RICE (W1)
- fcs:MUR @ MTSU (W1)
- fcs:EKU @ JVST (W1)
- fcs:CHSO @ GASO (W1)
- fcs:SELA @ USA (W1)
- fcs:VMI @ VT (W1)
- fcs:NWST @ LT (W1)
- fcs:UTU @ BYU (W1)
- fcs:HAMP @ MD (W1)
- fcs:SDST @ NW (W1)
- fcs:LAM @ UL (W1)
- fcs:MORG @ ASU (W1)
- fcs:MERC @ NMSU (W1)
- fcs:NAU @ ARI (W1)
- fcs:PRST @ SDSU (W1)

## Only in secondary (not added)

- ARK @ UTAH (2026-09-12T16:00:00Z)
- ISU @ IOWA (2026-09-12T23:30:00Z)
- LSU @ MISS (2026-09-19T23:30:00Z)
- MIA @ ND (2026-11-08T00:30:00Z)
- MICH @ OSU (2026-11-28T17:00:00Z)
- MIZZ @ KU (2026-09-12T00:00:00Z)
- ORE @ OKST (2026-09-12T16:00:00Z)
- OSU @ IU (2026-10-17T16:00:00Z)
- OSU @ TEX (2026-09-12T23:30:00Z)
- OU @ MICH (2026-09-12T16:00:00Z)
- TEX @ OU (2026-10-10T16:00:00Z)
- UGA @ ALA (2026-10-11T00:00:00Z)
- UGA @ ARK (2026-09-19T16:00:00Z)


## Refresh

```bash
ODDS_API_KEY=… python scripts/cfb/publish_official_slate_2026.py
```

Re-run weekly (or when ESPN kickoffs move). Primary refresh still comes from the packaged ESPN season file; replace that file first if the team-schedule ingest is re-run.

## Doctrine

KosEdge slate is desk SoT. Sources are inputs. Sim / KEI math is unchanged.
