# NFL Overview destination pages — 2026-08-11

Soft-launch pages behind Overview Betting Desk / Fantasy links.

## Routes

| Route | Backing | Empty behavior |
|-------|---------|----------------|
| `/pro/nfl/props` | Model `nfl/props/board` for **2026 W1** (query override allowed) | Honest empty: markets + hooks not live; CTAs Edge Board · Game Boxes · Edges. **No** archive-week / “Try 2025 W1” CTAs. |
| `/pro/nfl/awards` | Model award projections (`mvp`, `opoy` only) | Honest empty until materialization; races without rows are **omitted** (no DPOY/OROY placeholder tabs). Lineage when present. |
| `/pro/nfl/fantasy/guillotine` | Desk copy + optional safe-floor / high-upside from `loadFantasyDraftDesk` | Live desk page even if lists thin; preseason banner when board is sim fallback. |
| `/pro/nfl/fantasy/sleepers` | Fantasy ranks + FantasyPros ADP via same desk loader | Late-round / Value Δ list; unmatched ADP → **—**; preseason banner when applicable. |

## Nav / IA

- Fantasy primary nav stays active on Guillotine + Sleepers (`/pro/nfl/fantasy/*`).
- Props / Awards sit under Betting Desk parent IA; page CTAs point to Edge Board / Season Model / Power Ratings as appropriate.
- Overview Fantasy hints updated (no “route reserved” copy).

## Mobile

- Props / Awards / Sleepers: card list on small screens, table from `md`/`sm` up.
- Guillotine: stacked explanation + name lists; touch-friendly CTAs.

## Smoke (local / preview)

```bash
# Expect 200 (auth/paywall follows existing Pro patterns — no new walls)
curl -sS -o /dev/null -w "%{http_code} props\n" http://127.0.0.1:3000/pro/nfl/props
curl -sS -o /dev/null -w "%{http_code} awards\n" http://127.0.0.1:3000/pro/nfl/awards
curl -sS -o /dev/null -w "%{http_code} guillotine\n" http://127.0.0.1:3000/pro/nfl/fantasy/guillotine
curl -sS -o /dev/null -w "%{http_code} sleepers\n" http://127.0.0.1:3000/pro/nfl/fantasy/sleepers
curl -sS -o /dev/null -w "%{http_code} overview\n" http://127.0.0.1:3000/pro/nfl/overview
```

**2026-08-11 local smoke:** all five URLs **200**. Overview hrefs present for all four destinations. Props + Awards showed honest **model unreachable** banners (no archive-week CTAs, no placeholder “Soon” tabs). Guillotine + Sleepers rendered preseason-sim desk content (safe floor / upside + late-round value board).

Overview links: Props → `/pro/nfl/props`, MVP/Awards → `/pro/nfl/awards`, Guillotine → `/pro/nfl/fantasy/guillotine`, Sleepers → `/pro/nfl/fantasy/sleepers`.

## Non-goals (unchanged)

Full props engine, DFS salaries, new season-sim award races, tag policy changes.
