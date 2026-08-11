# Trusted Source Index — KosEdge Content Employees

**Status:** Approved source list for NFL content, injury/news desks, market notes, and employee-style writing.  
**Updated:** 2026-08-06  
**Machine source:** `data/writers/nfl-trusted-sources.json`  
**Team beats:** `data/writers/nfl-beat-writers.json` / `.md` (in-repo). Full team-by-team beat writers + official team handles also live in `KosEdge_NFL_X_Contact_Index_v1.pdf` when available offline.

Prefer these accounts over random social noise.

---

## Usage rules

1. **Tier 1 first** for breaking / injury alerts.
2. **Confirm major claims** with a second reliable source when possible.
3. **Beat writers** for team-specific practice / lineup context.
4. **Medical accounts** for timeline interpretation — not rumor invention.
5. **Market accounts** for movement context — not blind copy.
6. **Always attribute** the source cleanly (`@handle` / outlet + link when available).
7. **On-site language:** use **market / consensus / books** — never “Vegas”.  
   Display `@PatrickE_Vegas` as market intel (do not surface “Vegas” wording on site).

Related: `employee-expertise-contract.md` (mandatory for all content employees), `research-standards.md`, `docs/writers/TRAINING_CAMP_DESK.md`.

---

## Tier 1 Alert (highest priority)

| Handle | Role / use |
|--------|------------|
| `@32BeatWriters` | Local practice / lineup intel |
| `@AdamSchefter` | Leaguewide breaking news |
| `@MySportsUpdate` | Fast NFL news aggregator |
| `@ProFootballDoc` | Injury analysis |
| `@FBInjuryDoc` | Recovery timelines / impact |
| `@NFLInjuryNws` | Fast injury headlines |
| `@RapSheet` | Breaking news / transactions |
| `@KevinRothWx` | Weather impact |
| `@PatrickE_Vegas` | Sharp money / book liability (**display as market intel**) |
| `@rotoworld_fb` | Injury / transaction wire |
| `@TomPelissero` | Injuries, transactions, discipline |
| `@UnderdogNFL` | Player news / practice notes |

---

## Breaking News / Insiders

- `@AlbertBreer`
- `@AroundTheNFL`
- `@JFowlerESPN`
- `@jjones9`
- `@Schultz_Report`
- `@MikeGarafolo`
- `@NFLonCBS`
- `@ProFootballTalk`

---

## Injury / Medical

- `@FantasyDPT`
- `@SportMDAnalysis`
- `@jmthrivept`
- `@DrJesseMorse`
- `@BangedUpBills`
- `@TheFantasyPT`
- `@Stephania_ESPN`

---

## Sharp / Market

Use for line movement, liability, and consensus context. Attribute cleanly; do not copy picks blindly. On-site copy: **market / consensus / books**.

- `@adamchernoff`
- `@BFawkes22`
- `@capjack2000`
- `@EvanHAbrams`
- `@RASPicks`
- `@robpizzola`
- `@RufusPeabody`
- `@spanky`
- `@SharpFootball`
- `@PatrickE_Vegas` *(Tier 1; market intel label on site)*

---

## Data / Usage / Analytics

- `@dwainmcfarland`
- `@FantasyProsNFL`
- `@kvalenzuela17`
- `@KevinCole___`
- `@MattFtheOracle`
- `@PFF_Fantasy`
- `@SethWalder`
- `@tejfbanalytics`

---

## Referee

- `@BenAustro`
- `@footballzebras`
- `@NFLFootballOps`
- `@NFLOfficiating`

---

## Beat writers + official team accounts

For local injury / practice / lineup confirmation:

1. **In-repo registry (preferred for tooling):**  
   `data/writers/nfl-beat-writers.json` · human index `data/writers/nfl-beat-writers.md`  
   Lookup: `python scripts/writers/beat-lookup.py --team BUF`
2. **External contact index:** `KosEdge_NFL_X_Contact_Index_v1.pdf` — full team-by-team beat list and official team handles.

Official injury reports and team sites outrank social rumor. Beat writers confirm practice / lineup context after Tier 1 alerts.

---

## Quick workflow (news / injury desk)

```text
1. Tier 1 alert fires (or aggregator ping)
2. Second source when claim moves a market or Week-1 lean
3. Beat lookup for the team + official report if injury/status
4. Medical account only to interpret recovery timeline (never invent)
5. Market account for open→current / liability context (optional)
6. Attribute every claim; ship with market/consensus/books wording
```
