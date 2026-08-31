# Fantasy draft board — sourced availability sits (2026-08-31)

**Branch:** `cursor/nfl-fantasy-sit-unavailable-7d8a` → `deploy-vercel`  
**Scope:** Fantasy draft desk + mock only. No VOR/ADP retune. No production-spine remat. No KEI.

## Problem

Josh Jacobs (GB RB) is on the NFL Commissioner's Exempt List (2026-08-30). He is off the Packers 53 and cannot practice or attend games, but the live fantasy draft board still listed him as a normal pick. Cutdown weekend also parked other skill players on IR / PUP / NFI / suspended.

## Fix

Sourced sit book + filter on the shared desk loader (desk + mock):

| Piece | Path |
|-------|------|
| Sit book | `apps/web/data/fantasy/draft-availability-sits-2026.json` |
| Filter | `apps/web/lib/fantasy/draft-availability.ts` |
| Apply | `apps/web/lib/fantasy/load-desk.ts` (before ADP match + desk rank) |
| Pack hard-out | `enrich.ts` / `risk-signals.ts` / `nfl-surface-integrity.ts` also recognize `nfi` + `commissioner_exempt` |

Unavailable players are **removed** from the draftable list (not zeroed and left on the board).

## Board audit — sat (removed)

| Player | Team | Pos | Status | Source |
|--------|------|-----|--------|--------|
| Josh Jacobs | GB | RB | Commissioner's Exempt | [NFL.com](https://www.nfl.com/news/nfl-places-packers-rb-josh-jacobs-commissioner-exempt-list) · [ESPN](https://www.espn.com/nfl/story/_/id/49774523/packers-rb-josh-jacobs-placed-commission-exempt-list) |
| Luke Musgrave | GB | TE | Reserve/PUP | [Packers.com](https://www.packers.com/news/packers-announce-roster-moves-aug-30-2026) |
| Jayden Higgins | HOU | WR | Reserve/Injured (season) | [Texans.com](https://www.houstontexans.com/news/houston-texans-transactions-8-21-2026) · [NFL.com](https://www.nfl.com/news/texans-wr-jayden-higgins-torn-acl-out-2026-season) |
| Tank Dell | HOU | WR | Reserve/Injured DTR | [Texans.com 8/30](https://www.houstontexans.com/news/houston-texans-transactions-8-30-2026) |
| James Conner | ARI | RB | Reserve/Injured DTR | [PFT](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/cardinals-place-james-conner-on-ir-among-their-moves-to-53) |
| Tip Reiman | ARI | TE | Reserve/PUP | same PFT Cardinals 53 piece |
| Dillon Gabriel | CLE | QB | Reserve/Injured DTR | [Browns.com](https://www.clevelandbrowns.com/news/browns-announce-initial-53-man-roster-heading-into-the-2026-season) |
| Joe Royer | CLE | TE | Reserve/NFI | Browns.com |
| Calvin Austin III | NYG | WR | Reserve/Injured (season ACL) | [Giants.com](https://www.giants.com/news/calvin-austin-iii-injury-status-roster-new-york-giants) |
| Jordyn Tyson | NO | WR | IR-DTR | [Saints.com](https://www.neworleanssaints.com/news/new-orleans-saints-53-man-roster-cut-transactions-august-30-2026-nfl-season) |
| Devin Neal | NO | RB | IR | Saints.com |
| Mason Tipton | NO | WR | Reserve/PUP | Saints.com |
| Jeshaun Jones | MIN | WR | Reserve/Suspended | [Vikings.com](https://www.vikings.com/news/53-man-roster-2026-nfl-initial) |

## Checked — not on standard fantasy board (no sit needed)

| Player | Team | Status | Source |
|--------|------|--------|--------|
| Cade Mays | DET | Reserve/Injured | [Lions.com](https://www.detroitlions.com/news/lions-announce-roster-moves-x5389) |
| Brian Branch | DET | Reserve/PUP | Lions.com |
| Kerby Joseph | DET | Reserve/PUP | Lions.com |
| Giovanni Manu | DET | Reserve/NFI | Lions.com |
| Terrion Arnold | SEA | Commissioner's Exempt (verified) | [NFL.com](https://www.nfl.com/news/seahawks-sign-terrion-arnold-nfl-to-place-cb-on-commissioner-s-exempt-list) |
| Jonathon Cooper | DEN | Commissioner's Exempt | TSN/ESPN (camp desk) |
| Micah Parsons | GB | Reserve/PUP | Packers.com |

## Checked — left draftable (no minted status)

| Player | Note |
|--------|------|
| Alvin Kamara | MCL timeline without posted IR/PUP as of Aug 31 camp desk |
| Ashton Jeanty | Club counting on Week 1; kept off IR |
| Christian McCaffrey | In team work; no sit designation |
| George Kittle | Activated off Active/PUP |
| Alec Pierce | Off Active/PUP (Colts) |
| Jaydon Blue | Beat waive only — not sat |

## Tests

- `apps/web/__tests__/lib/fantasy/draft-availability.test.ts`
- `apps/web/__tests__/lib/fantasy/fantasy-draft-rank-board-smoke.test.ts` (Jacobs sit + desk rank)

## Out of scope

- No player-production rematerialize / Railway
- No ADP / VOR / desk-rank formula changes
- No camp-desk JSON rewrite
- No KEI
