# CFB Official Slate — in-house dual-source (through W2)

**Date:** 2026-08-31
**Slate version:** `cfb-official-slate-v2-dual-20260831`
**Desk SoT:** `apps/web/lib/data/cfb-official-slate-2026.json` (copy in model-service)

This pass unlocked weeks 0–2 from the ESPN schedule SoT (`as_of=2026-08-31`).
No The Odds API pull (no credit burn). W0/W1 desk factcheck/status carried
forward from the prior artifact by `game_id`. W2 rows are ESPN-primary
`unconfirmed_secondary` — not invented agrees.

## Sources

| Role | Source | Notes |
|------|--------|--------|
| Primary | ESPN public team schedule (`espn_team_schedule_public`) | Packaged `2026-08-31` · 889-game season file · not live-scraped this pass |
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
| 2 | 86 | 0 | 86 | 47 |
| **Total** | **183** | **51** | **183** | **96** |

Secondary events pulled: 0 · name-matched: 0
Fact-check error: ODDS_API_KEY not set
Week 0 finals (scores from engine schedule): 6

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
- fcs:FAMU @ MIA (W2)
- fcs:VILL @ LOU (W2)
- fcs:NORF @ UVA (W2)
- fcs:RICH @ NCSU (W2)
- RUT @ BC (W2)
- MIZZ @ KU (W2)
- fcs:CP @ SJSU (W2)
- fcs:MERC @ UNM (W2)
- OU @ MICH (W2)
- ASU @ TAMU (W2)
- WSU @ KSU (W2)
- ORE @ OKST (W2)
- fcs:ETSU @ UNC (W2)
- ODU @ VT (W2)
- WAKE @ PUR (W2)
- fcs:HOW @ IU (W2)
- PSU @ TEM (W2)
- USF @ ARMY (W2)
- APP @ ECU (W2)
- fcs:WOF @ KENT (W2)
- WKU @ UGA (W2)
- fcs:UTM @ WVU (W2)
- fcs:COLG @ CMU (W2)
- fcs:HC @ M-OH (W2)
- fcs:STBK @ BALL (W2)
- ALA @ UK (W2)
- MSST @ MINN (W2)
- fcs:WEB @ COLO (W2)
- UCF @ PITT (W2)
- ARI @ BYU (W2)
- CAL @ SYR (W2)
- DUKE @ ILL (W2)
- EMU @ MSU (W2)
- MD @ CONN (W2)
- UTAHST @ WASH (W2)
- RICE @ ND (W2)
- UTSA @ TXST (W2)
- ULM @ UAB (W2)
- fcs:RMU @ AKR (W2)
- fcs:CCSU @ TOL (W2)
- fcs:SHU @ MASS (W2)
- fcs:WAG @ JMU (W2)
- UNLV @ UNT (W2)
- fcs:UCD @ SMU (W2)
- fcs:UNCO @ WYO (W2)
- fcs:ALST @ TROY (W2)
- DEL @ VAN (W2)
- fcs:CAM @ UF (W2)
- MEM @ BOISE (W2)
- BUFF @ FIU (W2)
- JVST @ OHIO (W2)
- fcs:GWEB @ LIB (W2)
- fcs:MONM @ WMU (W2)
- fcs:TOW @ SCAR (W2)
- TENN @ GT (W2)
- fcs:WCU @ CIN (W2)
- fcs:SOU @ HOU (W2)
- BGSU @ NEB (W2)
- fcs:SUU @ CSU (W2)
- TLSA @ SHSU (W2)
- fcs:ILST @ NIU (W2)
- USA @ TULN (W2)
- fcs:WES @ ARST (W2)
- GAST @ KENNESAW (W2)
- MTSU @ MRSH (W2)
- fcs:LIN @ MOST (W2)
- SDSU @ UCLA (W2)
- fcs:WIU @ WIS (W2)
- USM @ AUB (W2)
- OSU @ TEX (W2)
- TTU @ ORST (W2)
- ISU @ IOWA (W2)
- GASO @ CLEM (W2)
- NAVY @ FAU (W2)
- LT @ LSU (W2)
- fcs:FOR @ CCU (W2)
- CHAR @ MISS (W2)
- fcs:PV @ BAY (W2)
- fcs:GRAM @ TCU (W2)
- fcs:TXSO @ UTEP (W2)
- fcs:NDSU @ AFA (W2)
- ARK @ UTAH (W2)
- fcs:SAC @ FRES (W2)
- fcs:MTST @ NEV (W2)
- UL @ USC (W2)
- NMSU @ HAW (W2)

## Only in secondary (not added)

_None._


## Refresh

```bash
ODDS_API_KEY=… python scripts/cfb/publish_official_slate_2026.py
```

Re-run weekly (or when ESPN kickoffs move). Primary refresh still comes from the packaged ESPN season file; replace that file first if the team-schedule ingest is re-run.
`as_of` / slate_version follow the engine schedule pack — never hardcode 2026-08-17.

## Doctrine

KosEdge slate is desk SoT. Sources are inputs. Sim / KEI math is unchanged.
Final scores pass through from the engine schedule when present. Never invent Open/Best.
