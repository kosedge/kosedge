# NFL Camp Desk + Monday team-preview refresh

**Date:** 2026-08-17 (Monday)  
**Device:** Mobile product pass  
**Constraint:** No Odds API historical / no `/Volumes/KosEdgeData/raw/odds/**` (Mac owns archive)

## Problems fixed

1. Camp Desk was empty on production — Aug 12 notes aged out of the 72h window over the weekend.
2. Team previews still attributed as **July 29** via missing `Date` + `DEFAULT_ARTICLE_DATE`.
3. Camp UI branded a collapsed **“Wire · ESPN”** block.
4. Writer doctrine needed an explicit trusted-X + multi-source rule for Camp/Monday refresh.

## Shipped

| Deliverable | Detail |
|-------------|--------|
| Camp Desk day file | `content/writers/camp-desk-2026/2026-08-17.json` — league wrap + **all 32** team notes |
| Loader | `apps/web/lib/nfl-camp-desk.ts` bundles Aug 17 (+ keeps Aug 12 in tree) |
| UI | `/pro/nfl/camp` — “Citation headlines” (not Wire ESPN); Trusted X beat map with handles |
| Previews | All 32 `content/writers/season-previews-2026/*.md` get `**Date:** August 17, 2026` + Monday Bottom line / What matters most |
| Default date | `DEFAULT_ARTICLE_DATE` → `August 17, 2026` |
| Writer doctrine | `docs/writers/TRAINING_CAMP_DESK.md` + beat registry notes: **Camp/Monday refresh uses trusted X list + multi-source** |
| Cadence | Rotation queue: full 32 every Monday in camp/season |

## Material depth (refreshed hard)

| Team | Why |
|------|-----|
| MIN | Murray named starter + short debut; preview open-battle framing updated |
| ATL | Penix still no 11-on-11 (Monday Stefanski) |
| CLE | Post-Bears QB split still open; Sanders starts next |
| WAS | Mariota right MCL — out rest of preseason |
| HOU | Mertz ACL IR; Rypien signed QB3 |
| NYJ | Geno ankle precaution; Klubnik sample; Hall groin |

## Still thin (honest short pulses)

Quiet clubs after Preseason Week 1 got short Pass notes (no filler essays): MIA, DEN, LV, NO, DET, ARI, SEA, JAX, and similar. Next midweek pulse queue: SF · LAR · SEA · NO · DET · MIA · LV · JAX · TEN · CAR.

## Credits / API

- Desk sources: trusted X index (`data/writers/nfl-beat-writers.json`), club sites, AP, Athletic/local, NBC/PFT, NFL.com learnings.
- Public citation feed may still hydrate from the existing ESPN article fetcher under the hood — **UI no longer brands it as Wire ESPN**.
- No historical Odds API calls. No odds warehouse writes.

## Smoke checklist

- [ ] `/pro/nfl/camp` shows `Camp Desk — Monday, Aug 17` and KosEdge cards (not empty)
- [ ] Zero visible “Wire · ESPN” copy
- [ ] Trusted X handles visible on beat map
- [ ] `/pro/nfl/previews/MIN` (and 3–4 others) show **August 17, 2026**
- [ ] MIN bottom line reflects named starter, not open battle
