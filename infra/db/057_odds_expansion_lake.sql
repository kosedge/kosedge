-- 057_odds_expansion_lake.sql
-- Canonical lake projection over existing append-only odds_snapshots.
-- Does NOT create a parallel write table. Does NOT overwrite vintages.
-- OPEN / CURRENT / CLOSE are derived in application code from captured_at history.

CREATE OR REPLACE VIEW odds_lake_v1 AS
SELECT
  sp.code AS sport,
  lg.code AS league,
  se.season_year AS season,
  g.id AS canonical_game_id,
  g.external_id AS provider_event_id,
  sb.code AS book,
  mk.code AS market_type,
  side.side,
  side.line,
  side.price,
  os.created_at AS retrieved_at,
  os.captured_at AS market_as_of,
  g.start_time AS event_start,
  os.source AS source,
  os.id AS snapshot_id
FROM odds_snapshots os
JOIN games g ON g.id = os.game_id
JOIN seasons se ON se.id = g.season_id
JOIN leagues lg ON lg.id = se.league_id
JOIN sports sp ON sp.id = lg.sport_id
JOIN sportsbooks sb ON sb.id = os.sportsbook_id
JOIN markets mk ON mk.id = os.market_id
CROSS JOIN LATERAL (
  SELECT *
  FROM (
    VALUES
      (
        'away',
        CASE
          WHEN mk.code IN ('spread', 'spreads') THEN os.spread_away
          WHEN mk.code IN ('total', 'totals') THEN os.total_points
          ELSE NULL
        END,
        CASE
          WHEN mk.code IN ('total', 'totals') THEN os.over_price
          ELSE os.price_away
        END
      ),
      (
        'home',
        CASE
          WHEN mk.code IN ('spread', 'spreads') THEN os.spread_home
          WHEN mk.code IN ('total', 'totals') THEN os.total_points
          ELSE NULL
        END,
        CASE
          WHEN mk.code IN ('total', 'totals') THEN os.under_price
          ELSE os.price_home
        END
      ),
      (
        'over',
        CASE WHEN mk.code IN ('total', 'totals') THEN os.total_points ELSE NULL END,
        os.over_price
      ),
      (
        'under',
        CASE WHEN mk.code IN ('total', 'totals') THEN os.total_points ELSE NULL END,
        os.under_price
      )
  ) AS v(side, line, price)
) AS side
WHERE
  (mk.code IN ('spread', 'spreads') AND side.side IN ('away', 'home'))
  OR (mk.code IN ('total', 'totals') AND side.side IN ('over', 'under'))
  OR (mk.code IN ('moneyline', 'h2h') AND side.side IN ('away', 'home'));

COMMENT ON VIEW odds_lake_v1 IS
  'P0 Odds Expansion lake: long-format projection of append-only odds_snapshots. Never overwrite vintages.';

CREATE INDEX IF NOT EXISTS idx_odds_snapshots_game_book_market_captured
  ON odds_snapshots (game_id, sportsbook_id, market_id, captured_at);
