# CFB live odds → Postgres (beat path)

**Date:** 2026-09-05  
**Why:** Celery `pull_odds_snapshot` previously persisted NFL/NBA/WNBA/MLB/NCAAB only. CFB Edge Board joined The Odds API at request time and never wrote `odds_snapshots` for `americanfootball_ncaaf`.

## Change

- `SPORT_MAP` includes `americanfootball_ncaaf` → league `cfb`
- Optional job query `sport_keys=americanfootball_ncaaf` for a CFB-only pull (credit-friendly)
- Football season year: Aug–Dec → calendar year; Jan–Feb → prior tip year

## One-shot (after Railway ships this)

```bash
curl -sS -X POST \
  "$MODEL_SERVICE_URL/api/jobs/pull-odds-snapshot?sport_keys=americanfootball_ncaaf"
```

Then verify:

```sql
SELECT COUNT(*) AS snaps, MAX(captured_at) AS latest
FROM odds_snapshots os
JOIN games g ON g.id = os.game_id
JOIN seasons s ON s.id = g.season_id
JOIN leagues l ON l.id = s.league_id
WHERE l.code = 'cfb';
```

## Not this pass

- Ch3 confirmation join (QB starters) — separate PR
- Historical densify (`enterprise_training_pull.py --sports cfb`) — already supported
- Edge Board trust / KEI math — unchanged
