"""MLB enterprise ops: densify, CLV (incl. run-line), quality, board health helpers."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import text

from .mlb_board_health import evaluate_mlb_board_health
from .mlb_odds_firewall import (
    DEFAULT_PREFERRED_BOOK,
    densify_bookmakers_csv,
    filter_spread_rows_for_firewall,
    firewall_summary,
    normalize_book_code,
    select_preferred_book_row,
)
from .mlb_prop_edge_policy import PLAY_STAKE_ELIGIBLE


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _american_implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    try:
        american = float(price)
    except (TypeError, ValueError):
        return None
    if american == 0:
        return None
    if american < 0:
        return abs(american) / (abs(american) + 100.0)
    return 100.0 / (american + 100.0)



def rank_thin_densify_dates(
    scored_rows: Sequence[tuple],
    *,
    max_dates: int,
) -> List[date]:
    """Rank (game_date, thin_score) rows for densify targeting (tests + callers)."""
    limit = max(1, int(max_dates))
    cleaned: List[tuple[date, int]] = []
    for row in scored_rows:
        if not row:
            continue
        d, score = row[0], int(row[1] or 0)
        if isinstance(d, date) and score > 0:
            cleaned.append((d, score))
    cleaned.sort(key=lambda item: (-item[1], item[0]))
    return [d for d, _ in cleaned[:limit]]


def mlb_game_dates_for_densify(
    session: Any,
    *,
    start_date: date,
    end_date: date,
    max_dates: int,
    prioritize_thin: bool = True,
) -> List[date]:
    """Return MLB game dates to densify, thin-first when requested.

    Thin dates: games already have mlb_market_projections + mlb_market_outcomes
    but lack open-ish (<= start-6h) or close-ish (>= start-3h) odds history.
    Falls back to remaining slate dates (ASC) to fill max_dates.
    """
    limit = max(1, int(max_dates))
    if prioritize_thin:
        thin_rows = session.execute(
            text(
                """
                WITH base AS (
                  SELECT g.id, g.game_date, g.start_time
                  FROM games g
                  JOIN seasons s ON s.id = g.season_id
                  JOIN leagues l ON l.id = s.league_id
                  WHERE l.code = 'mlb'
                    AND g.game_date BETWEEN :start_date AND :end_date
                    AND EXISTS (
                      SELECT 1 FROM mlb_market_projections p WHERE p.game_id = g.id
                    )
                    AND EXISTS (
                      SELECT 1 FROM mlb_market_outcomes o WHERE o.game_id = g.id
                    )
                ),
                odds AS (
                  SELECT os.game_id,
                         MIN(os.captured_at) AS first_c,
                         MAX(os.captured_at) AS last_c
                  FROM odds_snapshots os
                  WHERE os.game_id IN (SELECT id FROM base)
                  GROUP BY os.game_id
                ),
                scored AS (
                  SELECT
                    b.game_date,
                    CASE
                      WHEN o.game_id IS NULL
                        OR NOT (
                          o.first_c <= COALESCE(b.start_time, b.game_date::timestamptz)
                            - INTERVAL '6 hours'
                        )
                      THEN 1 ELSE 0
                    END AS miss_open,
                    CASE
                      WHEN o.game_id IS NULL
                        OR NOT (
                          o.last_c >= COALESCE(b.start_time, b.game_date::timestamptz)
                            - INTERVAL '3 hours'
                        )
                      THEN 1 ELSE 0
                    END AS miss_close
                  FROM base b
                  LEFT JOIN odds o ON o.game_id = b.id
                )
                SELECT game_date,
                       SUM(miss_open + miss_close) AS thin_score
                FROM scored
                GROUP BY game_date
                HAVING SUM(miss_open + miss_close) > 0
                ORDER BY thin_score DESC, game_date ASC
                LIMIT :limit
                """
            ),
            {"start_date": start_date, "end_date": end_date, "limit": limit},
        ).fetchall()
        dates = [r[0] for r in thin_rows if isinstance(r[0], date)]
        if len(dates) >= limit:
            return dates[:limit]
        taken = set(dates)
        fill_rows = session.execute(
            text(
                """
                SELECT DISTINCT g.game_date
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                WHERE l.code = 'mlb'
                  AND g.game_date BETWEEN :start_date AND :end_date
                ORDER BY g.game_date ASC
                """
            ),
            {"start_date": start_date, "end_date": end_date},
        ).fetchall()
        for r in fill_rows:
            d = r[0]
            if isinstance(d, date) and d not in taken:
                dates.append(d)
                taken.add(d)
                if len(dates) >= limit:
                    break
        return dates[:limit]

    rows = session.execute(
        text(
            """
            SELECT DISTINCT g.game_date
            FROM games g
            JOIN seasons s ON s.id = g.season_id
            JOIN leagues l ON l.id = s.league_id
            WHERE l.code = 'mlb'
              AND g.game_date BETWEEN :start_date AND :end_date
            ORDER BY g.game_date ASC
            """
        ),
        {"start_date": start_date, "end_date": end_date},
    ).fetchall()
    dates = [r[0] for r in rows if isinstance(r[0], date)]
    return dates[:limit]


def persist_mlb_densify_run(
    session: Any,
    *,
    bookmakers: str,
    markets: str,
    start_date: date,
    end_date: date,
    preferred_book: str,
    requests_attempted: int,
    requests_skipped_cached: int,
    snapshots_inserted: int,
    status: str,
    payload: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO mlb_odds_densify_runs (
              sport_key, bookmakers, markets, start_date, end_date, preferred_book,
              requests_attempted, requests_skipped_cached, snapshots_inserted, status, payload
            ) VALUES (
              'baseball_mlb', :bookmakers, :markets, :start_date, :end_date, :preferred_book,
              :requests_attempted, :requests_skipped_cached, :snapshots_inserted, :status,
              CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "bookmakers": bookmakers,
            "markets": markets,
            "start_date": start_date,
            "end_date": end_date,
            "preferred_book": normalize_book_code(preferred_book),
            "requests_attempted": int(requests_attempted),
            "requests_skipped_cached": int(requests_skipped_cached),
            "snapshots_inserted": int(snapshots_inserted),
            "status": status,
            "payload": json.dumps(payload),
        },
    )


def persist_mlb_quality_snapshot(
    session: Any,
    *,
    run_date: date,
    model_version: str,
    pipeline_stage: str,
    payload: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO mlb_model_quality_snapshots (
              run_date, model_version, pipeline_stage,
              sample_size, brier_ml, mae_total_runs,
              avg_ml_clv, avg_total_clv, avg_spread_clv, ece, payload
            ) VALUES (
              :run_date, :model_version, :pipeline_stage,
              :sample_size, :brier_ml, :mae_total_runs,
              :avg_ml_clv, :avg_total_clv, :avg_spread_clv, :ece, CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "run_date": run_date,
            "model_version": model_version,
            "pipeline_stage": pipeline_stage,
            "sample_size": int(payload.get("sample_size") or 0),
            "brier_ml": payload.get("brier_ml"),
            "mae_total_runs": payload.get("mae_total_runs"),
            "avg_ml_clv": payload.get("avg_ml_clv"),
            "avg_total_clv": payload.get("avg_total_clv"),
            "avg_spread_clv": payload.get("avg_spread_clv"),
            "ece": payload.get("ece"),
            "payload": json.dumps(payload),
        },
    )


def persist_mlb_board_health(
    session: Any,
    *,
    run_date: date,
    model_version: str,
    health: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO mlb_board_health_snapshots (
              run_date, model_version, publish_ready, payload
            ) VALUES (
              :run_date, :model_version, :publish_ready, CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "run_date": run_date,
            "model_version": model_version,
            "publish_ready": bool(health.get("publish_ready_ops")),
            "payload": json.dumps(health),
        },
    )


def compute_mlb_clv_with_spread(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
    preferred_book: str = DEFAULT_PREFERRED_BOOK,
) -> Dict[str, Any]:
    """CLV for moneyline, total, and spread/run-line with DK-first firewall."""
    preferred = normalize_book_code(preferred_book)
    rows = session.execute(
        text(
            """
            WITH latest_proj AS (
              SELECT DISTINCT ON (mp.game_id)
                mp.game_id,
                mp.fg_home_win_prob,
                mp.fair_fg_total,
                mp.fair_fg_spread_home,
                COALESCE(
                  mp.fg_home_cover_prob_run_line,
                  (mp.projection->'markets'->>'fg_home_cover_prob_run_line')::numeric
                ) AS fg_home_cover_prob_run_line,
                COALESCE(
                  mp.fg_margin_mean,
                  (mp.projection->'markets'->>'fg_margin_mean')::numeric
                ) AS fg_margin_mean
              FROM mlb_market_projections mp
              JOIN games g ON g.id = mp.game_id
              WHERE mp.model_version = :model_version
                AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
              ORDER BY mp.game_id, mp.created_at DESC
            ),
            snap AS (
              SELECT
                os.game_id,
                m.code AS market_code,
                sb.code AS book_code,
                os.price_home,
                os.price_away,
                os.spread_home,
                os.total_points,
                os.captured_at,
                FIRST_VALUE(os.captured_at) OVER (
                  PARTITION BY os.game_id, m.code, sb.code ORDER BY os.captured_at ASC
                ) AS first_captured,
                FIRST_VALUE(os.captured_at) OVER (
                  PARTITION BY os.game_id, m.code, sb.code ORDER BY os.captured_at DESC
                ) AS last_captured
              FROM odds_snapshots os
              JOIN markets m ON m.id = os.market_id
              JOIN sportsbooks sb ON sb.id = os.sportsbook_id
              JOIN games g ON g.id = os.game_id
              JOIN seasons s ON s.id = g.season_id
              JOIN leagues l ON l.id = s.league_id
              WHERE l.code = 'mlb'
                AND m.code IN ('moneyline', 'total', 'spread')
                AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
            )
            SELECT
              lp.game_id,
              lp.fg_home_win_prob,
              lp.fair_fg_total,
              lp.fair_fg_spread_home,
              lp.fg_home_cover_prob_run_line,
              lp.fg_margin_mean,
              snap.market_code,
              snap.book_code,
              snap.price_home,
              snap.price_away,
              snap.spread_home,
              snap.total_points,
              snap.captured_at,
              snap.first_captured,
              snap.last_captured
            FROM latest_proj lp
            LEFT JOIN snap ON snap.game_id = lp.game_id
            """
        ),
        {"model_version": model_version, "lookback_days": int(lookback_days)},
    ).fetchall()

    by_game: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        m = dict(row._mapping)
        gid = str(m["game_id"])
        game = by_game.setdefault(
            gid,
            {
                "game_id": gid,
                "fg_home_win_prob": _to_float(m["fg_home_win_prob"]),
                "fair_fg_total": _to_float(m["fair_fg_total"]),
                "fair_fg_spread_home": _to_float(m["fair_fg_spread_home"]),
                "fg_home_cover_prob_run_line": _to_float(m["fg_home_cover_prob_run_line"]),
                "fg_margin_mean": _to_float(m["fg_margin_mean"]),
                "ml_rows": [],
                "total_rows": [],
                "spread_rows": [],
            },
        )
        market_code = m.get("market_code")
        if not market_code:
            continue
        entry = {
            "book_code": m.get("book_code"),
            "price_home": m.get("price_home"),
            "price_away": m.get("price_away"),
            "spread_home": _to_float(m.get("spread_home")),
            "total_points": _to_float(m.get("total_points")),
            "captured_at": m.get("captured_at"),
            "first_captured": m.get("first_captured"),
            "last_captured": m.get("last_captured"),
            "is_open": m.get("captured_at") == m.get("first_captured"),
            "is_close": m.get("captured_at") == m.get("last_captured"),
        }
        if market_code == "moneyline":
            game["ml_rows"].append(entry)
        elif market_code == "total":
            game["total_rows"].append(entry)
        elif market_code == "spread":
            game["spread_rows"].append(entry)

    items: List[Dict[str, Any]] = []
    ml_vals: List[float] = []
    total_vals: List[float] = []
    spread_vals: List[float] = []
    books_seen: List[str] = []
    spreads_kept = 0
    spreads_dropped = 0

    for game in by_game.values():
        item: Dict[str, Any] = {"game_id": game["game_id"]}

        open_ml_candidates = [r for r in game["ml_rows"] if r.get("is_open")]
        close_ml_candidates = [r for r in game["ml_rows"] if r.get("is_close")]
        open_ml = select_preferred_book_row(open_ml_candidates, preferred_book=preferred)
        close_ml = select_preferred_book_row(close_ml_candidates, preferred_book=preferred)
        if open_ml:
            books_seen.append(str(open_ml.get("book_code") or ""))
        model_home = game["fg_home_win_prob"]
        ml_clv = None
        ml_pick = None
        if (
            model_home is not None
            and open_ml
            and close_ml
            and open_ml.get("price_home") is not None
            and open_ml.get("price_away") is not None
            and close_ml.get("price_home") is not None
            and close_ml.get("price_away") is not None
        ):
            open_home_prob = _american_implied_prob(int(open_ml["price_home"]))
            if open_home_prob is not None:
                ml_pick = "home" if model_home > open_home_prob else "away"
                if ml_pick == "home":
                    ml_clv = (_american_implied_prob(int(close_ml["price_home"])) or 0.0) - (
                        _american_implied_prob(int(open_ml["price_home"])) or 0.0
                    )
                else:
                    ml_clv = (_american_implied_prob(int(close_ml["price_away"])) or 0.0) - (
                        _american_implied_prob(int(open_ml["price_away"])) or 0.0
                    )
                ml_vals.append(ml_clv)
        item["ml_pick"] = ml_pick
        item["ml_clv"] = round(ml_clv, 5) if ml_clv is not None else None
        item["preferred_ml_book"] = open_ml.get("book_code") if open_ml else None

        open_tot_candidates = [r for r in game["total_rows"] if r.get("is_open") and r.get("total_points") is not None]
        close_tot_candidates = [r for r in game["total_rows"] if r.get("is_close") and r.get("total_points") is not None]
        open_tot = select_preferred_book_row(open_tot_candidates, preferred_book=preferred)
        close_tot = select_preferred_book_row(close_tot_candidates, preferred_book=preferred)
        fair_total = game["fair_fg_total"]
        total_clv = None
        total_pick = None
        if fair_total is not None and open_tot and close_tot:
            open_total = float(open_tot["total_points"])
            close_total = float(close_tot["total_points"])
            total_pick = "over" if fair_total > open_total else "under"
            total_clv = (close_total - open_total) if total_pick == "over" else (open_total - close_total)
            total_vals.append(total_clv)
        item["total_pick"] = total_pick
        item["total_clv"] = round(total_clv, 4) if total_clv is not None else None

        raw_spread_open = [r for r in game["spread_rows"] if r.get("is_open")]
        raw_spread_close = [r for r in game["spread_rows"] if r.get("is_close")]
        kept_open = filter_spread_rows_for_firewall(raw_spread_open)
        kept_close = filter_spread_rows_for_firewall(raw_spread_close)
        spreads_kept += len(kept_open)
        spreads_dropped += max(0, len(raw_spread_open) - len(kept_open))
        open_sp = select_preferred_book_row(kept_open, preferred_book=preferred)
        close_sp = select_preferred_book_row(kept_close, preferred_book=preferred)
        fair_spread = game["fair_fg_spread_home"]
        if fair_spread is None and game["fg_margin_mean"] is not None:
            fair_spread = -round(float(game["fg_margin_mean"]) * 2.0) / 2.0
        spread_clv = None
        spread_pick = None
        if fair_spread is not None and open_sp and close_sp and open_sp.get("spread_home") is not None:
            open_line = float(open_sp["spread_home"])
            close_line = float(close_sp["spread_home"]) if close_sp.get("spread_home") is not None else open_line
            # Model more bullish on home => wants a larger (more negative) home number.
            # Positive CLV when close moves toward model relative to open.
            if fair_spread < open_line:
                spread_pick = "home"
                spread_clv = open_line - close_line
            else:
                spread_pick = "away"
                spread_clv = close_line - open_line
            spread_vals.append(spread_clv)
        item["spread_pick"] = spread_pick
        item["spread_clv"] = round(spread_clv, 4) if spread_clv is not None else None
        item["open_spread_home"] = open_sp.get("spread_home") if open_sp else None
        item["close_spread_home"] = close_sp.get("spread_home") if close_sp else None
        item["preferred_spread_book"] = open_sp.get("book_code") if open_sp else None
        items.append(item)

    summary = {
        "model_version": model_version,
        "lookback_days": int(lookback_days),
        "count": len(items),
        "sample_size": float(len(items)),
        "avg_ml_clv": round(sum(ml_vals) / len(ml_vals), 5) if ml_vals else None,
        "avg_total_clv": round(sum(total_vals) / len(total_vals), 5) if total_vals else None,
        "avg_spread_clv": round(sum(spread_vals) / len(spread_vals), 5) if spread_vals else None,
        "ml_sample_size": len(ml_vals),
        "total_sample_size": len(total_vals),
        "spread_sample_size": len(spread_vals),
        "firewall": firewall_summary(
            preferred_book=preferred,
            books_seen=sorted({b for b in books_seen if b}),
            spreads_kept=spreads_kept,
            spreads_dropped_alt=spreads_dropped,
        ),
        "items": items,
    }
    return summary


def upsert_mlb_clv_attribution(
    session: Any,
    *,
    model_version: str,
    clv_summary: Dict[str, Any],
) -> int:
    written = 0
    for item in clv_summary.get("items") or []:
        game_id = item.get("game_id")
        if not game_id:
            continue
        markets = [
            ("moneyline", item.get("ml_pick"), item.get("ml_clv"), None),
            ("total", item.get("total_pick"), item.get("total_clv"), None),
            ("spread", item.get("spread_pick"), item.get("spread_clv"), item.get("open_spread_home")),
        ]
        for market_code, side, clv_value, open_line in markets:
            if clv_value is None:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO mlb_clv_attribution (
                      game_id, model_version, market_code, preferred_book,
                      open_line, close_line, model_side, clv_value, payload
                    ) VALUES (
                      :game_id, :model_version, :market_code, :preferred_book,
                      :open_line, :close_line, :model_side, :clv_value, CAST(:payload AS jsonb)
                    )
                    ON CONFLICT (game_id, model_version, market_code) DO UPDATE SET
                      preferred_book = EXCLUDED.preferred_book,
                      open_line = EXCLUDED.open_line,
                      close_line = EXCLUDED.close_line,
                      model_side = EXCLUDED.model_side,
                      clv_value = EXCLUDED.clv_value,
                      payload = EXCLUDED.payload
                    """
                ),
                {
                    "game_id": game_id,
                    "model_version": model_version,
                    "market_code": market_code,
                    "preferred_book": item.get("preferred_spread_book")
                    if market_code == "spread"
                    else item.get("preferred_ml_book"),
                    "open_line": open_line if market_code == "spread" else None,
                    "close_line": item.get("close_spread_home") if market_code == "spread" else None,
                    "model_side": side,
                    "clv_value": clv_value,
                    "payload": json.dumps(item),
                },
            )
            written += 1
    return written


def build_board_health_from_db(
    session: Any,
    *,
    model_version: str,
    lookback_days: int = 14,
    quality: Optional[Dict[str, Any]] = None,
    holdout_sample_size: Optional[int] = None,
) -> Dict[str, Any]:
    proj_rows = session.execute(
        text(
            """
            SELECT DISTINCT ON (mp.game_id)
              mp.fg_home_win_prob,
              mp.fair_fg_total,
              mp.fg_total_mean,
              mp.fair_fg_spread_home,
              COALESCE(
                mp.fg_home_cover_prob_run_line,
                (mp.projection->'markets'->>'fg_home_cover_prob_run_line')::numeric
              ) AS fg_home_cover_prob_run_line
            FROM mlb_market_projections mp
            JOIN games g ON g.id = mp.game_id
            WHERE mp.model_version = :model_version
              AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
            ORDER BY mp.game_id, mp.created_at DESC
            """
        ),
        {"model_version": model_version, "lookback_days": int(lookback_days)},
    ).fetchall()
    projections = [dict(r._mapping) for r in proj_rows]

    coverage = session.execute(
        text(
            """
            WITH slate AS (
              SELECT g.id
              FROM games g
              JOIN seasons s ON s.id = g.season_id
              JOIN leagues l ON l.id = s.league_id
              WHERE l.code = 'mlb'
                AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
                AND g.game_date < CURRENT_DATE
            )
            SELECT
              (SELECT COUNT(*) FROM slate) AS games_n,
              (SELECT COUNT(*) FROM slate sl JOIN mlb_market_outcomes mo ON mo.game_id = sl.id) AS outcomes_n,
              (
                SELECT COUNT(DISTINCT os.game_id)
                FROM odds_snapshots os
                JOIN slate sl ON sl.id = os.game_id
              ) AS odds_n,
              (
                SELECT COUNT(DISTINCT os.game_id)
                FROM odds_snapshots os
                JOIN sportsbooks sb ON sb.id = os.sportsbook_id
                JOIN slate sl ON sl.id = os.game_id
                WHERE lower(sb.code) = 'draftkings'
              ) AS dk_n
            """
        ),
        {"lookback_days": int(lookback_days)},
    ).fetchone()
    games_n = int(coverage.games_n or 0) if coverage else 0
    outcomes_n = int(coverage.outcomes_n or 0) if coverage else 0
    odds_n = int(coverage.odds_n or 0) if coverage else 0
    dk_n = int(coverage.dk_n or 0) if coverage else 0
    quality = quality or {}
    return evaluate_mlb_board_health(
        projection_rows=projections,
        outcome_coverage_rate=(outcomes_n / games_n) if games_n else None,
        odds_coverage_rate=(odds_n / games_n) if games_n else None,
        dk_snapshot_rate=(dk_n / games_n) if games_n else None,
        brier_ml=_to_float(quality.get("brier_ml")),
        mae_total_runs=_to_float(quality.get("mae_total_runs")),
        holdout_sample_size=holdout_sample_size,
        props_play_stake_eligible=PLAY_STAKE_ELIGIBLE,
    )


def densify_snapshot_datetimes(
    game_dates: Sequence[date],
    *,
    day_offset: int = 0,
    snapshot_hour_utc: int = 17,
    snapshot_minute_utc: int = 0,
) -> List[datetime]:
    out: List[datetime] = []
    for game_date in game_dates:
        snapshot_date = game_date + timedelta(days=int(day_offset))
        out.append(
            datetime.combine(
                snapshot_date,
                time(hour=int(snapshot_hour_utc), minute=int(snapshot_minute_utc)),
                tzinfo=timezone.utc,
            )
        )
    return out


def resolve_densify_books(raw: Optional[str] = None) -> str:
    return densify_bookmakers_csv(raw)
