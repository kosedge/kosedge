"""Extended nflverse ingestion for second-order edge (participation / draft).

Graceful: missing nflverse tables or future seasons do not crash callers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import text


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iter_rows(df: Any) -> Iterable[Dict[str, Any]]:
    if df is None:
        return
    if hasattr(df, "iter_rows"):
        for row in df.iter_rows(named=True):
            yield dict(row)


def _safe_load(loader: Any, *, seasons: List[int]) -> Any:
    try:
        return loader(seasons=seasons)
    except Exception as exc:
        message = str(exc)
        if any(token in message for token in ("404", "Not Found", "must be between", "AttributeError")):
            return None
        # Some nflreadpy builds lack participation loader.
        if "has no attribute" in message.lower():
            return None
        raise


def ingest_participation_weekly(
    *,
    seasons: Sequence[int],
    replace_existing: bool = False,
) -> Dict[str, Any]:
    """Ingest nflverse participation into nfl_dp_participation_weekly when available."""
    from .db import SessionLocal

    session = SessionLocal()
    try:
        import nflreadpy as nfl
    except Exception as exc:
        session.close()
        return {"ok": False, "error": f"nflreadpy_unavailable:{exc}", "rows": 0}

    season_list = [int(s) for s in seasons]
    loader = getattr(nfl, "load_participation", None) or getattr(nfl, "load_snap_counts", None)
    if loader is None:
        session.close()
        return {"ok": False, "error": "no_participation_loader", "rows": 0, "source": "nflverse"}

    df = _safe_load(loader, seasons=season_list)
    if df is None:
        session.close()
        return {"ok": False, "error": "participation_load_failed", "rows": 0}

    if replace_existing:
        session.execute(
            text("DELETE FROM nfl_dp_participation_weekly WHERE season = ANY(:seasons)"),
            {"seasons": season_list},
        )
        session.commit()

    written = 0
    for row in _iter_rows(df):
        season = row.get("season")
        week = row.get("week")
        team = row.get("team") or row.get("recent_team") or row.get("club_code")
        player_id = row.get("player_id") or row.get("gsis_id") or row.get("pfr_player_id")
        if season is None or week is None or not team or not player_id:
            continue
        try:
            season_i = int(season)
            week_i = int(week)
        except (TypeError, ValueError):
            continue
        if week_i < 1 or week_i > 22:
            continue

        offense_snaps = int(row.get("offense_snaps") or row.get("offense") or 0 or 0)
        defense_snaps = int(row.get("defense_snaps") or row.get("defense") or 0 or 0)
        st_snaps = int(row.get("st_snaps") or row.get("special_teams") or 0 or 0)
        offense_pct = row.get("offense_pct") or row.get("offense_pct")
        defense_pct = row.get("defense_pct")

        session.execute(
            text(
                """
                INSERT INTO nfl_dp_participation_weekly (
                  season, week, team, player_id, player_name, position,
                  offense_snaps, defense_snaps, st_snaps,
                  offense_pct, defense_pct, as_of_week, source, updated_at
                ) VALUES (
                  :season, :week, :team, :player_id, :player_name, :position,
                  :offense_snaps, :defense_snaps, :st_snaps,
                  :offense_pct, :defense_pct, :as_of_week, :source, :updated_at
                )
                ON CONFLICT (season, week, team, player_id) DO UPDATE SET
                  player_name = EXCLUDED.player_name,
                  position = EXCLUDED.position,
                  offense_snaps = EXCLUDED.offense_snaps,
                  defense_snaps = EXCLUDED.defense_snaps,
                  st_snaps = EXCLUDED.st_snaps,
                  offense_pct = EXCLUDED.offense_pct,
                  defense_pct = EXCLUDED.defense_pct,
                  as_of_week = EXCLUDED.as_of_week,
                  source = EXCLUDED.source,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "season": season_i,
                "week": week_i,
                "team": str(team),
                "player_id": str(player_id),
                "player_name": row.get("player_name") or row.get("player"),
                "position": row.get("position"),
                "offense_snaps": offense_snaps,
                "defense_snaps": defense_snaps,
                "st_snaps": st_snaps,
                "offense_pct": float(offense_pct) if offense_pct is not None else None,
                "defense_pct": float(defense_pct) if defense_pct is not None else None,
                "as_of_week": week_i,
                "source": "nflverse_participation",
                "updated_at": _now(),
            },
        )
        written += 1
        if written % 2000 == 0:
            session.commit()

    session.commit()
    session.close()
    return {
        "ok": True,
        "rows": written,
        "seasons": season_list,
        "source": "nflverse_participation",
        "notes": "Week W row is as-of end of W; join week-1 for pre-game.",
    }


def ingest_draft_picks_raw(
    *,
    seasons: Sequence[int],
) -> Dict[str, Any]:
    """Ensure draft picks land in nfl_dp_raw_objects (idempotent overlay)."""
    from .db import SessionLocal
    from .ingest import _upsert_raw

    session = SessionLocal()
    try:
        import nflreadpy as nfl
    except Exception as exc:
        session.close()
        return {"ok": False, "error": f"nflreadpy_unavailable:{exc}", "rows": 0}

    season_list = [int(s) for s in seasons]
    loader = getattr(nfl, "load_draft_picks", None)
    if loader is None:
        session.close()
        return {"ok": False, "error": "no_draft_loader", "rows": 0}

    df = _safe_load(loader, seasons=season_list)
    if df is None:
        session.close()
        return {"ok": False, "error": "draft_load_failed", "rows": 0}

    written = 0
    for row in _iter_rows(df):
        season = row.get("season")
        pick = row.get("pick") or row.get("overall")
        if season is None or pick is None:
            continue
        object_key = f"draft:{season}:{pick}"
        _upsert_raw(
            session,
            source="nflverse",
            object_type="draft_pick",
            object_key=object_key,
            season=int(season),
            week=None,
            game_id=None,
            payload=row,
        )
        written += 1
        if written % 500 == 0:
            session.commit()
    session.commit()
    session.close()
    return {"ok": True, "rows": written, "seasons": season_list, "source": "nflverse_draft"}
