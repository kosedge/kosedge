"""Persist and load NFL DFS slates. Schema-missing paths fail closed."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from src.services.nfl_dfs_board import (
    DfsBoard,
    DfsProjectionInput,
    assemble_dfs_board,
    projection_input_from_baseline,
)
from src.services.nfl_dfs_identity import (
    DfsSalaryObservation,
    DfsSlateIdentity,
    canonical_dfs_site,
)
from src.services.nfl_dfs_salary_ingest import (
    INGEST_VERSION,
    NormalizedSlate,
    payload_sha256,
)
from src.services.nfl_player_identity import IdentityInput, resolve_and_persist_player_identity
from src.services.nfl_player_production import PRODUCTION_VERSION

log = logging.getLogger(__name__)


def persist_normalized_slate(session: Any, slate: NormalizedSlate) -> Dict[str, Any]:
    raw_sha = payload_sha256(slate.raw_payload)
    raw_row = session.execute(
        text(
            """
            INSERT INTO nfl_dfs_slate_raw (
              site, season, week, source, source_version, captured_at, payload, payload_sha256
            ) VALUES (
              :site, :season, :week, :source, :source_version, CAST(:captured_at AS timestamptz),
              CAST(:payload AS jsonb), :payload_sha256
            )
            ON CONFLICT (site, season, week, payload_sha256) DO UPDATE SET
              source_version = EXCLUDED.source_version
            RETURNING id
            """
        ),
        {
            "site": slate.site,
            "season": slate.season,
            "week": slate.week,
            "source": slate.source,
            "source_version": slate.source_version,
            "captured_at": slate.captured_at,
            "payload": json.dumps(slate.raw_payload, default=str),
            "payload_sha256": raw_sha,
        },
    ).fetchone()
    raw_id = str(raw_row.id) if raw_row is not None else None

    session.execute(
        text(
            """
            UPDATE nfl_dfs_slates
            SET is_current = FALSE, updated_at = NOW()
            WHERE site = :site AND season = :season AND week = :week AND slate_id = :slate_id
              AND source_version <> :source_version
            """
        ),
        {
            "site": slate.site,
            "season": slate.season,
            "week": slate.week,
            "slate_id": slate.slate_id,
            "source_version": slate.source_version,
        },
    )
    session.execute(
        text(
            """
            INSERT INTO nfl_dfs_slates (
              site, season, week, slate_id, slate_name, contest_style, game_count,
              source, source_version, captured_at, is_current, raw_id
            ) VALUES (
              :site, :season, :week, :slate_id, :slate_name, :contest_style, :game_count,
              :source, :source_version, CAST(:captured_at AS timestamptz), TRUE, CAST(:raw_id AS uuid)
            )
            ON CONFLICT (site, season, week, slate_id, source_version) DO UPDATE SET
              slate_name = EXCLUDED.slate_name,
              game_count = EXCLUDED.game_count,
              is_current = TRUE,
              captured_at = EXCLUDED.captured_at,
              raw_id = EXCLUDED.raw_id,
              updated_at = NOW()
            """
        ),
        {
            "site": slate.site,
            "season": slate.season,
            "week": slate.week,
            "slate_id": slate.slate_id,
            "slate_name": slate.slate_name,
            "contest_style": slate.contest_style,
            "game_count": len({row.game_label for row in slate.rows if row.game_label}),
            "source": slate.source,
            "source_version": slate.source_version,
            "captured_at": slate.captured_at,
            "raw_id": raw_id,
        },
    )

    session.execute(
        text(
            """
            UPDATE nfl_dfs_salary_observations
            SET is_current = FALSE, updated_at = NOW()
            WHERE site = :site AND slate_id = :slate_id AND source_version <> :source_version
            """
        ),
        {"site": slate.site, "slate_id": slate.slate_id, "source_version": slate.source_version},
    )

    upserted = 0
    unresolved = 0
    for row in slate.rows:
        identity_status = "unresolved"
        identity_reason = "unresolved"
        player_uid = None
        try:
            resolved = resolve_and_persist_player_identity(
                session,
                IdentityInput(
                    source_system="draftkings" if slate.site == "DK" else "fanduel",
                    external_id=row.source_player_id,
                    player_name=row.player_name,
                    team=row.team,
                    position=row.position,
                    season=slate.season,
                    week=slate.week,
                    source_payload={"ingest_version": INGEST_VERSION, "slate_id": slate.slate_id},
                ),
            )
            if resolved.status == "mapped" and resolved.player_uid:
                identity_status = "resolved"
                identity_reason = resolved.rule_used
                player_uid = resolved.player_uid
            elif resolved.status == "conflict":
                identity_status = "conflict"
                identity_reason = resolved.rule_used
                unresolved += 1
            else:
                unresolved += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("DFS identity resolve failed for %s: %s", row.player_name, exc)
            unresolved += 1

        session.execute(
            text(
                """
                INSERT INTO nfl_dfs_salary_observations (
                  site, season, week, slate_id, source_player_id, player_uid, player_name,
                  team, opponent, position, salary, game_id, game_label, game_time, source,
                  source_version, captured_at, is_current, identity_status, identity_reason, raw_id
                ) VALUES (
                  :site, :season, :week, :slate_id, :source_player_id, CAST(:player_uid AS uuid),
                  :player_name, :team, :opponent, :position, :salary, :game_id, :game_label,
                  CAST(:game_time AS timestamptz), :source, :source_version,
                  CAST(:captured_at AS timestamptz), TRUE, :identity_status, :identity_reason,
                  CAST(:raw_id AS uuid)
                )
                ON CONFLICT (site, slate_id, source_player_id, source_version) DO UPDATE SET
                  player_uid = EXCLUDED.player_uid,
                  player_name = EXCLUDED.player_name,
                  team = EXCLUDED.team,
                  opponent = EXCLUDED.opponent,
                  position = EXCLUDED.position,
                  salary = EXCLUDED.salary,
                  game_label = EXCLUDED.game_label,
                  game_time = EXCLUDED.game_time,
                  is_current = TRUE,
                  identity_status = EXCLUDED.identity_status,
                  identity_reason = EXCLUDED.identity_reason,
                  captured_at = EXCLUDED.captured_at,
                  updated_at = NOW()
                """
            ),
            {
                "site": slate.site,
                "season": slate.season,
                "week": slate.week,
                "slate_id": slate.slate_id,
                "source_player_id": row.source_player_id,
                "player_uid": player_uid,
                "player_name": row.player_name,
                "team": row.team,
                "opponent": row.opponent,
                "position": row.position,
                "salary": row.salary,
                "game_id": None,
                "game_label": row.game_label,
                "game_time": row.game_time,
                "source": row.source,
                "source_version": slate.source_version,
                "captured_at": slate.captured_at,
                "identity_status": identity_status,
                "identity_reason": identity_reason,
                "raw_id": raw_id,
            },
        )
        upserted += 1

    session.commit()
    return {
        "site": slate.site,
        "season": slate.season,
        "week": slate.week,
        "slate_id": slate.slate_id,
        "source_version": slate.source_version,
        "raw_id": raw_id,
        "salary_upserted": upserted,
        "unresolved_identity": unresolved,
        "rejected_cross_site": len(slate.rejected),
    }


def load_current_slates(session: Any, *, site: str, season: int, week: int) -> List[DfsSlateIdentity]:
    rows = session.execute(
        text(
            """
            SELECT site, season, week, slate_id, contest_style
            FROM nfl_dfs_slates
            WHERE site = :site AND season = :season AND week = :week AND is_current = TRUE
            ORDER BY captured_at DESC
            """
        ),
        {"site": site, "season": season, "week": week},
    ).fetchall()
    return [
        DfsSlateIdentity(
            season=int(r.season),
            week=int(r.week),
            site=str(r.site),
            slate_id=str(r.slate_id),
            contest_style=str(r.contest_style or "classic"),
        )
        for r in rows
    ]


def load_current_salaries(
    session: Any, *, site: str, season: int, week: int, slate_id: str
) -> List[DfsSalaryObservation]:
    rows = session.execute(
        text(
            """
            SELECT
              site, season, week, slate_id, source_player_id, player_uid::text AS player_uid,
              player_name, team, opponent, position, salary, game_id, game_label,
              game_time, source, source_version, captured_at, is_current, identity_status
            FROM nfl_dfs_salary_observations
            WHERE site = :site AND season = :season AND week = :week
              AND slate_id = :slate_id AND is_current = TRUE
            """
        ),
        {"site": site, "season": season, "week": week, "slate_id": slate_id},
    ).fetchall()
    out: List[DfsSalaryObservation] = []
    for r in rows:
        mapping = dict(r._mapping)
        out.append(
            DfsSalaryObservation(
                site=str(mapping["site"]),
                season=int(mapping["season"]),
                week=int(mapping["week"]),
                slate_id=str(mapping["slate_id"]),
                source_player_id=str(mapping["source_player_id"]),
                player_uid=mapping.get("player_uid"),
                player_name=str(mapping["player_name"]),
                team=str(mapping["team"]),
                opponent=str(mapping["opponent"]),
                position=str(mapping["position"]),
                salary=int(mapping["salary"]),
                game_id=str(mapping["game_id"]) if mapping.get("game_id") is not None else None,
                game_label=mapping.get("game_label"),
                game_time=mapping["game_time"].isoformat() if mapping.get("game_time") is not None else None,
                source=str(mapping["source"]),
                source_version=str(mapping["source_version"]),
                captured_at=mapping["captured_at"].isoformat()
                if hasattr(mapping.get("captured_at"), "isoformat")
                else str(mapping.get("captured_at") or ""),
                is_current=bool(mapping["is_current"]),
                identity_status=str(mapping.get("identity_status") or "unresolved"),
            )
        )
    return out


def load_week_projections(
    session: Any, *, season: int, week: int, model_version: str = "nfl-player-v1"
) -> List[DfsProjectionInput]:
    rows = session.execute(
        text(
            """
            SELECT
              b.*,
              f.opponent AS feature_opponent
            FROM nfl_player_projection_baselines b
            LEFT JOIN nfl_player_projection_features_weekly f
              ON f.season = b.season AND f.week = b.week
             AND f.team = b.team AND f.player_id = b.player_id
            WHERE b.season = :season
              AND b.week = :week
              AND b.model_version = :model_version
            """
        ),
        {"season": season, "week": week, "model_version": model_version},
    ).fetchall()
    out: List[DfsProjectionInput] = []
    for row in rows:
        mapping = dict(row._mapping)
        if mapping.get("opponent") is None and mapping.get("feature_opponent"):
            mapping["opponent"] = mapping["feature_opponent"]
        item = projection_input_from_baseline(mapping)
        if item:
            out.append(item)
    return out


def build_board_from_db(
    session: Any,
    *,
    site: str,
    season: int,
    week: int,
    slate_id: Optional[str] = None,
    position: Optional[str] = None,
    model_version: str = "nfl-player-v1",
) -> DfsBoard:
    site_c = canonical_dfs_site(site)
    if site_c is None:
        return assemble_dfs_board(
            requested=DfsSlateIdentity(season=season, week=week, site=str(site), slate_id=""),
            salaries=[],
            projections=[],
        )
    slates = load_current_slates(session, site=site_c, season=season, week=week)
    requested = DfsSlateIdentity(
        season=season,
        week=week,
        site=site_c,
        slate_id=str(slate_id or (slates[0].slate_id if len(slates) == 1 else "")),
    )
    salaries: List[DfsSalaryObservation] = []
    if requested.slate_id:
        salaries = load_current_salaries(
            session, site=site_c, season=season, week=week, slate_id=requested.slate_id
        )
    projections = load_week_projections(session, season=season, week=week, model_version=model_version)
    board = assemble_dfs_board(
        requested=requested,
        salaries=salaries,
        projections=projections,
        available_slates=slates,
        position=position,
    )
    board.diagnostics["production_version"] = PRODUCTION_VERSION
    board.diagnostics["model_version"] = model_version
    return board
