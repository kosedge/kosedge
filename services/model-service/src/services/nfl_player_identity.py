from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from sqlalchemy import text

DEFAULT_RESOLVER_VERSION = os.getenv("NFL_PLAYER_IDENTITY_RESOLVER_VERSION", "nfl-player-identity-v1")
MIN_AUTO_MAP_CONFIDENCE = float(os.getenv("NFL_PLAYER_IDENTITY_AUTO_MAP_THRESHOLD", "0.82"))
FUZZY_MIN_SCORE = float(os.getenv("NFL_PLAYER_IDENTITY_FUZZY_MIN_SCORE", "0.90"))
FUZZY_CANDIDATE_WINDOW = int(os.getenv("NFL_PLAYER_IDENTITY_FUZZY_CANDIDATE_WINDOW", "8"))
TRUSTED_LINK_MIN_CONFIDENCE = float(os.getenv("NFL_PLAYER_IDENTITY_TRUSTED_LINK_MIN_CONFIDENCE", "0.95"))
NO_PUBLISH_MAX_UNRESOLVED_RATE = float(os.getenv("NFL_PLAYER_IDENTITY_MAX_UNRESOLVED_RATE", "0.06"))
NO_PUBLISH_MAX_CONFLICT_RATE = float(os.getenv("NFL_PLAYER_IDENTITY_MAX_CONFLICT_RATE", "0.02"))


def normalize_name_key(value: str) -> str:
    raw = str(value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    compact = " ".join(raw.split())
    compact = compact.replace(" jr", "").replace(" sr", "")
    compact = compact.replace(" iii", "").replace(" ii", "").replace(" iv", "")
    return compact


def initial_last_name_key(value: str) -> Optional[str]:
    """Bridge nflverse-style 'D.Maye' and Odds-API 'Drake Maye' to a shared key."""
    parts = normalize_name_key(value).split()
    if len(parts) < 2:
        return None
    first = parts[0]
    last = parts[-1]
    if not first or not last:
        return None
    return f"{first[0]} {last}"


def prop_player_match_keys(*, player_uid: Optional[str], player_name: Optional[str]) -> List[str]:
    """Stable lookup keys for joining baselines to prop market snapshots.

    Historical Odds-API snapshots often have null player_uid and full names, while
    projection baselines use nflverse abbreviations with resolved UIDs. Index and
    lookup with uid, normalized full name, and initial+last so either side can join.
    """
    keys: List[str] = []
    seen: set[str] = set()

    def _add(key: str) -> None:
        if key and key not in seen:
            seen.add(key)
            keys.append(key)

    if player_uid is not None and str(player_uid).strip():
        _add(f"uid:{str(player_uid).strip()}")
    name = str(player_name or "").strip()
    if name:
        normalized = normalize_name_key(name)
        if normalized:
            _add(f"name:{normalized}")
        initial_last = initial_last_name_key(name)
        if initial_last:
            _add(f"il:{initial_last}")
    return keys


# Position allow-lists for ambiguous initial+last joins (e.g. J.Williams DET WR
# must not steal Javonte Williams DAL rush lines via shared `il:j williams`).
_PROP_MARKET_POSITIONS: Dict[str, Optional[List[str]]] = {
    "pass_yds": ["QB"],
    "rush_yds": ["RB", "FB", "QB", "WR"],
    "rec_yds": ["WR", "TE", "RB", "FB"],
    "receptions": ["WR", "TE", "RB", "FB"],
    "anytime_td": None,
}


def prop_market_position_compatible(market_key: str, position: Optional[str]) -> bool:
    allowed = _PROP_MARKET_POSITIONS.get(str(market_key or ""))
    if allowed is None:
        return True
    pos = str(position or "").strip().upper()
    return bool(pos) and pos in allowed


def prop_market_position_rank(market_key: str, position: Optional[str]) -> int:
    """Lower is better. Used to break ties when multiple players share il: keys."""
    allowed = _PROP_MARKET_POSITIONS.get(str(market_key or "")) or []
    pos = str(position or "").strip().upper()
    try:
        return allowed.index(pos)
    except ValueError:
        return 99


def select_prop_market_for_player(
    market_lookup: Dict[tuple[str, str], Any],
    *,
    player_match_keys: List[str],
    market_key: str,
    team: Optional[str] = None,
    position: Optional[str] = None,
    ambiguous_il_keys: Optional[set[str]] = None,
) -> Any:
    """Pick the best market snapshot for a baseline player.

    Prefer uid / exact normalized name, then team-scoped initial+last, then
    unambiguous global initial+last. Never attach an `il:` collision across
    teams/positions (Javonte Williams rush ≠ Jameson Williams DET WR).
    """
    mk = str(market_key or "")
    team_u = str(team or "").strip().upper()
    ambiguous = ambiguous_il_keys or set()

    # 1) UID
    for key in player_match_keys:
        if key.startswith("uid:"):
            hit = market_lookup.get((key, mk))
            if hit is not None:
                return hit

    # 2) Exact normalized full/abbrev name
    for key in player_match_keys:
        if key.startswith("name:"):
            hit = market_lookup.get((key, mk))
            if hit is not None:
                m_team = str(getattr(hit, "team", None) or "").strip().upper()
                if m_team and team_u and m_team != team_u:
                    continue
                return hit

    # 3) Team-scoped initial+last
    if team_u:
        for key in player_match_keys:
            if key.startswith("il:"):
                hit = market_lookup.get((f"{key}|{team_u}", mk))
                if hit is not None and prop_market_position_compatible(mk, position):
                    return hit

    # 4) Global il: only when unique among baselines this week
    for key in player_match_keys:
        if not key.startswith("il:") or key in ambiguous:
            continue
        hit = market_lookup.get((key, mk))
        if hit is None:
            continue
        m_team = str(getattr(hit, "team", None) or "").strip().upper()
        if m_team and team_u and m_team != team_u:
            continue
        if not prop_market_position_compatible(mk, position):
            continue
        return hit

    return None


_PROP_SPORTSBOOK_RANK = {"draftkings": 0, "fanduel": 1}


def prop_market_snapshot_rank(market: Any) -> tuple:
    """Lower rank is preferred when multiple books quote the same player/market."""
    book = str(getattr(market, "sportsbook", None) or "").strip().lower()
    book_rank = _PROP_SPORTSBOOK_RANK.get(book, 50)
    has_both = 0 if (getattr(market, "over_price", None) is not None and getattr(market, "under_price", None) is not None) else 1
    captured = getattr(market, "captured_at", None)
    try:
        captured_ts = float(captured.timestamp()) if captured is not None else 0.0
    except Exception:
        captured_ts = 0.0
    return (has_both, book_rank, -captured_ts)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fuzzy_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return round(float(SequenceMatcher(None, left, right).ratio()), 6)


@dataclass(frozen=True)
class IdentityInput:
    source_system: str
    external_id: Optional[str]
    player_name: str
    team: Optional[str] = None
    position: Optional[str] = None
    season: Optional[int] = None
    week: Optional[int] = None
    source_payload: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class IdentityResolution:
    status: str
    player_uid: Optional[str]
    confidence: float
    rule_used: str
    resolver_version: str
    normalized_name: str
    candidate_player_uids: List[str]
    explanation: Dict[str, Any]
    queue_reason: Optional[str] = None


def _select_external_id_match(session: Any, source_system: str, external_id: str) -> Optional[Dict[str, Any]]:
    row = session.execute(
        text(
            """
            SELECT
              sim.player_uid::text AS player_uid,
              sim.confidence,
              sim.trusted_link
            FROM nfl_player_source_id_map sim
            WHERE sim.source_system = :source_system
              AND sim.external_id = :external_id
            LIMIT 1
            """
        ),
        {"source_system": source_system, "external_id": external_id},
    ).fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def _select_exact_alias_candidates(
    session: Any,
    *,
    normalized_name: str,
    team: Optional[str],
    position: Optional[str],
    season: Optional[int],
    week: Optional[int],
) -> List[Dict[str, Any]]:
    team_key = str(team or "").strip().upper()
    position_key = str(position or "").strip().upper()
    season_key = int(season) if season is not None else -1
    week_key = int(week) if week is not None else -1
    rows = session.execute(
        text(
            """
            SELECT
              a.player_uid::text AS player_uid,
              a.team,
              a.position,
              a.season,
              a.week
            FROM nfl_player_aliases a
            WHERE a.normalized_alias = :normalized_alias
              AND (a.team = :team OR a.team = '')
              AND (a.position = :position OR a.position = '')
              AND (a.season = :season OR a.season = -1)
              AND (a.week = :week OR a.week = -1)
            ORDER BY
              CASE WHEN a.team = :team THEN 0 ELSE 1 END,
              CASE WHEN a.position = :position THEN 0 ELSE 1 END,
              CASE WHEN a.season = :season THEN 0 ELSE 1 END,
              CASE WHEN a.week = :week THEN 0 ELSE 1 END,
              a.last_seen_at DESC
            LIMIT 12
            """
        ),
        {
            "normalized_alias": normalized_name,
            "team": team_key,
            "position": position_key,
            "season": season_key,
            "week": week_key,
        },
    ).fetchall()
    return [dict(row._mapping) for row in rows]


def _select_fuzzy_candidates(
    session: Any,
    *,
    team: Optional[str],
    position: Optional[str],
    season: Optional[int],
    week: Optional[int],
) -> List[Dict[str, Any]]:
    team_key = str(team or "").strip().upper()
    position_key = str(position or "").strip().upper()
    season_key = int(season) if season is not None else -1
    week_key = int(week) if week is not None else -1
    rows = session.execute(
        text(
            """
            SELECT
              a.player_uid::text AS player_uid,
              a.normalized_alias,
              a.team,
              a.position,
              a.season,
              a.week
            FROM nfl_player_aliases a
            WHERE (a.team = :team OR a.team = '')
              AND (a.position = :position OR a.position = '')
              AND (a.season = :season OR a.season = -1)
              AND (a.week = :week OR a.week = -1)
            ORDER BY a.last_seen_at DESC
            LIMIT :limit_rows
            """
        ),
        {
            "team": team_key,
            "position": position_key,
            "season": season_key,
            "week": week_key,
            "limit_rows": int(max(1, FUZZY_CANDIDATE_WINDOW)),
        },
    ).fetchall()
    return [dict(row._mapping) for row in rows]


def _upsert_identity_and_alias(
    session: Any,
    *,
    player_uid: str,
    canonical_name: str,
    normalized_name: str,
    team: Optional[str],
    position: Optional[str],
    season: Optional[int],
    week: Optional[int],
    source_system: str,
) -> None:
    alias_team = str(team or "").strip().upper()
    alias_position = str(position or "").strip().upper()
    alias_season = int(season) if season is not None else -1
    alias_week = int(week) if week is not None else -1
    session.execute(
        text(
            """
            UPDATE nfl_player_identities
            SET
              canonical_name = :canonical_name,
              normalized_name = :normalized_name,
              primary_team = COALESCE(:primary_team, primary_team),
              primary_position = COALESCE(:primary_position, primary_position),
              active_from_season = COALESCE(active_from_season, :season),
              active_to_season = GREATEST(COALESCE(active_to_season, :season), COALESCE(:season, active_to_season)),
              updated_at = NOW()
            WHERE player_uid = CAST(:player_uid AS uuid)
            """
        ),
        {
            "player_uid": player_uid,
            "canonical_name": canonical_name,
            "normalized_name": normalized_name,
            "primary_team": team,
            "primary_position": position,
            "season": season,
        },
    )
    session.execute(
        text(
            """
            INSERT INTO nfl_player_aliases (
              player_uid, source_system, alias, normalized_alias, team, position, season, week,
              context, first_seen_at, last_seen_at, created_at, updated_at
            ) VALUES (
              CAST(:player_uid AS uuid), :source_system, :alias, :normalized_alias, :team, :position, :season, :week,
              CAST(:context AS jsonb), NOW(), NOW(), NOW(), NOW()
            )
            ON CONFLICT (player_uid, normalized_alias, team, position, season, week) DO UPDATE SET
              source_system = EXCLUDED.source_system,
              alias = EXCLUDED.alias,
              context = EXCLUDED.context,
              last_seen_at = NOW(),
              updated_at = NOW()
            """
        ),
        {
            "player_uid": player_uid,
            "source_system": source_system,
            "alias": canonical_name,
            "normalized_alias": normalized_name,
            "team": alias_team,
            "position": alias_position,
            "season": alias_season,
            "week": alias_week,
            "context": json.dumps({"resolver": DEFAULT_RESOLVER_VERSION}),
        },
    )


def _create_identity(session: Any, payload: IdentityInput, normalized_name: str) -> str:
    row = session.execute(
        text(
            """
            INSERT INTO nfl_player_identities (
              canonical_name, normalized_name, primary_team, primary_position,
              active_from_season, active_to_season, metadata, created_at, updated_at
            ) VALUES (
              :canonical_name, :normalized_name, :primary_team, :primary_position,
              :season, :season, CAST(:metadata AS jsonb), NOW(), NOW()
            )
            RETURNING player_uid::text
            """
        ),
        {
            "canonical_name": payload.player_name,
            "normalized_name": normalized_name,
            "primary_team": payload.team,
            "primary_position": payload.position,
            "season": payload.season,
            "metadata": json.dumps(
                {
                    "created_by": "identity_resolver",
                    "resolver_version": DEFAULT_RESOLVER_VERSION,
                    "source_system": payload.source_system,
                }
            ),
        },
    ).fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("Failed to create nfl player identity")
    return str(row[0])


def _upsert_source_map(
    session: Any,
    *,
    source_system: str,
    external_id: str,
    player_uid: str,
    confidence: float,
    trusted_link: bool,
    metadata: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO nfl_player_source_id_map (
              source_system, external_id, player_uid, confidence, trusted_link,
              first_seen_at, last_seen_at, metadata, created_at, updated_at
            ) VALUES (
              :source_system, :external_id, CAST(:player_uid AS uuid), :confidence, :trusted_link,
              NOW(), NOW(), CAST(:metadata AS jsonb), NOW(), NOW()
            )
            ON CONFLICT (source_system, external_id) DO UPDATE SET
              player_uid = EXCLUDED.player_uid,
              confidence = EXCLUDED.confidence,
              trusted_link = EXCLUDED.trusted_link,
              last_seen_at = NOW(),
              metadata = EXCLUDED.metadata,
              updated_at = NOW()
            """
        ),
        {
            "source_system": source_system,
            "external_id": external_id,
            "player_uid": player_uid,
            "confidence": confidence,
            "trusted_link": trusted_link,
            "metadata": json.dumps(metadata),
        },
    )


def persist_mapping_event(session: Any, payload: IdentityInput, decision: IdentityResolution) -> str:
    row = session.execute(
        text(
            """
            INSERT INTO nfl_player_mapping_events (
              observed_source, observed_external_id, observed_player_name, normalized_name,
              observed_team, observed_position, observed_season, observed_week,
              resolver_version, rule_used, confidence, status, player_uid, candidate_player_uids,
              explanation, created_at
            ) VALUES (
              :observed_source, :observed_external_id, :observed_player_name, :normalized_name,
              :observed_team, :observed_position, :observed_season, :observed_week,
              :resolver_version, :rule_used, :confidence, :status, CAST(:player_uid AS uuid), CAST(:candidate_player_uids AS jsonb),
              CAST(:explanation AS jsonb), NOW()
            )
            RETURNING id::text
            """
        ),
        {
            "observed_source": payload.source_system,
            "observed_external_id": payload.external_id,
            "observed_player_name": payload.player_name,
            "normalized_name": decision.normalized_name,
            "observed_team": payload.team,
            "observed_position": payload.position,
            "observed_season": payload.season,
            "observed_week": payload.week,
            "resolver_version": decision.resolver_version,
            "rule_used": decision.rule_used,
            "confidence": decision.confidence,
            "status": decision.status,
            "player_uid": decision.player_uid,
            "candidate_player_uids": json.dumps(decision.candidate_player_uids),
            "explanation": json.dumps(decision.explanation),
        },
    ).fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("Failed to persist nfl mapping event")
    return str(row[0])


def queue_mapping_review(session: Any, *, event_id: str, payload: IdentityInput, decision: IdentityResolution) -> None:
    reason = decision.queue_reason or ("conflict" if decision.status == "conflict" else "unresolved")
    priority = "high" if reason in {"conflict", "guardrail_high_confidence_remap"} else "medium"
    session.execute(
        text(
            """
            INSERT INTO nfl_player_mapping_review_queue (
              mapping_event_id, queue_status, priority, reason,
              observed_source, observed_external_id, observed_player_name, normalized_name,
              observed_team, observed_position, observed_season, observed_week,
              candidate_player_uids, proposed_player_uid, created_at, updated_at
            ) VALUES (
              CAST(:mapping_event_id AS uuid), 'pending', :priority, :reason,
              :observed_source, :observed_external_id, :observed_player_name, :normalized_name,
              :observed_team, :observed_position, :observed_season, :observed_week,
              CAST(:candidate_player_uids AS jsonb), CAST(:proposed_player_uid AS uuid), NOW(), NOW()
            )
            """
        ),
        {
            "mapping_event_id": event_id,
            "priority": priority,
            "reason": reason,
            "observed_source": payload.source_system,
            "observed_external_id": payload.external_id,
            "observed_player_name": payload.player_name,
            "normalized_name": decision.normalized_name,
            "observed_team": payload.team,
            "observed_position": payload.position,
            "observed_season": payload.season,
            "observed_week": payload.week,
            "candidate_player_uids": json.dumps(decision.candidate_player_uids),
            "proposed_player_uid": decision.player_uid,
        },
    )


def resolve_player_identity(session: Any, payload: IdentityInput) -> IdentityResolution:
    normalized_name = normalize_name_key(payload.player_name)
    if not normalized_name:
        return IdentityResolution(
            status="unresolved",
            player_uid=None,
            confidence=0.0,
            rule_used="invalid_input",
            resolver_version=DEFAULT_RESOLVER_VERSION,
            normalized_name="",
            candidate_player_uids=[],
            explanation={"reason": "empty_player_name"},
            queue_reason="unresolved",
        )

    if payload.external_id:
        external_match = _select_external_id_match(session, payload.source_system, payload.external_id)
        if external_match:
            return IdentityResolution(
                status="mapped",
                player_uid=str(external_match["player_uid"]),
                confidence=round(_safe_float(external_match.get("confidence"), default=1.0), 4),
                rule_used="exact_external_id",
                resolver_version=DEFAULT_RESOLVER_VERSION,
                normalized_name=normalized_name,
                candidate_player_uids=[str(external_match["player_uid"])],
                explanation={"trusted_link": bool(external_match.get("trusted_link", False))},
            )

    exact_candidates = _select_exact_alias_candidates(
        session,
        normalized_name=normalized_name,
        team=payload.team,
        position=payload.position,
        season=payload.season,
        week=payload.week,
    )
    distinct_exact = sorted({str(row["player_uid"]) for row in exact_candidates if row.get("player_uid")})
    if len(distinct_exact) == 1:
        return IdentityResolution(
            status="mapped",
            player_uid=distinct_exact[0],
            confidence=0.93,
            rule_used="exact_normalized_name_context",
            resolver_version=DEFAULT_RESOLVER_VERSION,
            normalized_name=normalized_name,
            candidate_player_uids=distinct_exact,
            explanation={"candidates_seen": len(exact_candidates)},
        )
    if len(distinct_exact) > 1:
        return IdentityResolution(
            status="conflict",
            player_uid=None,
            confidence=0.0,
            rule_used="exact_normalized_name_context_conflict",
            resolver_version=DEFAULT_RESOLVER_VERSION,
            normalized_name=normalized_name,
            candidate_player_uids=distinct_exact,
            explanation={"reason": "multiple_exact_candidates"},
            queue_reason="conflict",
        )

    fuzzy_rows = _select_fuzzy_candidates(
        session,
        team=payload.team,
        position=payload.position,
        season=payload.season,
        week=payload.week,
    )
    scored: List[Dict[str, Any]] = []
    for row in fuzzy_rows:
        alias = str(row.get("normalized_alias") or "")
        score = _fuzzy_score(normalized_name, alias)
        scored.append({"player_uid": str(row.get("player_uid")), "score": score})
    scored.sort(key=lambda item: float(item["score"]), reverse=True)

    if scored:
        top = scored[0]
        top_score = float(top["score"])
        second_score = float(scored[1]["score"]) if len(scored) > 1 else 0.0
        if top_score >= FUZZY_MIN_SCORE and (top_score - second_score) >= 0.03:
            confidence = max(MIN_AUTO_MAP_CONFIDENCE, min(0.91, top_score))
            return IdentityResolution(
                status="mapped",
                player_uid=str(top["player_uid"]),
                confidence=round(confidence, 4),
                rule_used="fuzzy_name_bounded_context",
                resolver_version=DEFAULT_RESOLVER_VERSION,
                normalized_name=normalized_name,
                candidate_player_uids=[str(top["player_uid"])],
                explanation={
                    "top_score": round(top_score, 5),
                    "second_score": round(second_score, 5),
                    "candidate_count": len(scored),
                },
            )
        top_candidates = [str(item["player_uid"]) for item in scored[:3] if float(item["score"]) >= max(0.8, FUZZY_MIN_SCORE - 0.08)]
        return IdentityResolution(
            status="conflict" if len(top_candidates) > 1 else "unresolved",
            player_uid=None,
            confidence=0.0,
            rule_used="fuzzy_name_ambiguous" if len(top_candidates) > 1 else "fuzzy_name_below_threshold",
            resolver_version=DEFAULT_RESOLVER_VERSION,
            normalized_name=normalized_name,
            candidate_player_uids=top_candidates,
            explanation={
                "top_score": round(top_score, 5),
                "second_score": round(second_score, 5),
                "required_score": float(FUZZY_MIN_SCORE),
            },
            queue_reason="conflict" if len(top_candidates) > 1 else "unresolved",
        )

    return IdentityResolution(
        status="unresolved",
        player_uid=None,
        confidence=0.0,
        rule_used="no_candidate",
        resolver_version=DEFAULT_RESOLVER_VERSION,
        normalized_name=normalized_name,
        candidate_player_uids=[],
        explanation={"reason": "no_alias_candidates"},
        queue_reason="unresolved",
    )


def resolve_and_persist_player_identity(session: Any, payload: IdentityInput) -> IdentityResolution:
    decision = resolve_player_identity(session, payload)
    if decision.status == "mapped" and decision.player_uid is not None:
        trusted_existing = None
        if payload.external_id:
            trusted_existing = _select_external_id_match(session, payload.source_system, payload.external_id)
        if trusted_existing and bool(trusted_existing.get("trusted_link")):
            existing_uid = str(trusted_existing.get("player_uid") or "")
            existing_conf = _safe_float(trusted_existing.get("confidence"), default=0.0)
            if (
                existing_uid
                and existing_uid != str(decision.player_uid)
                and existing_conf >= TRUSTED_LINK_MIN_CONFIDENCE
            ):
                decision = IdentityResolution(
                    status="conflict",
                    player_uid=existing_uid,
                    confidence=0.0,
                    rule_used="guardrail_trusted_link_no_silent_remap",
                    resolver_version=decision.resolver_version,
                    normalized_name=decision.normalized_name,
                    candidate_player_uids=[existing_uid, str(decision.player_uid)],
                    explanation={
                        "existing_player_uid": existing_uid,
                        "attempted_player_uid": str(decision.player_uid),
                        "existing_confidence": existing_conf,
                    },
                    queue_reason="guardrail_high_confidence_remap",
                )
        if decision.status == "mapped" and decision.player_uid:
            _upsert_identity_and_alias(
                session,
                player_uid=str(decision.player_uid),
                canonical_name=payload.player_name,
                normalized_name=decision.normalized_name,
                team=payload.team,
                position=payload.position,
                season=payload.season,
                week=payload.week,
                source_system=payload.source_system,
            )
            if payload.external_id:
                _upsert_source_map(
                    session,
                    source_system=payload.source_system,
                    external_id=payload.external_id,
                    player_uid=str(decision.player_uid),
                    confidence=decision.confidence,
                    trusted_link=decision.confidence >= TRUSTED_LINK_MIN_CONFIDENCE,
                    metadata={
                        "rule_used": decision.rule_used,
                        "resolver_version": decision.resolver_version,
                    },
                )

    if decision.status == "unresolved" and payload.external_id:
        player_uid = _create_identity(session, payload, decision.normalized_name)
        _upsert_identity_and_alias(
            session,
            player_uid=player_uid,
            canonical_name=payload.player_name,
            normalized_name=decision.normalized_name,
            team=payload.team,
            position=payload.position,
            season=payload.season,
            week=payload.week,
            source_system=payload.source_system,
        )
        _upsert_source_map(
            session,
            source_system=payload.source_system,
            external_id=payload.external_id,
            player_uid=player_uid,
            confidence=0.98,
            trusted_link=True,
            metadata={
                "rule_used": "bootstrap_external_id",
                "resolver_version": DEFAULT_RESOLVER_VERSION,
            },
        )
        decision = IdentityResolution(
            status="mapped",
            player_uid=player_uid,
            confidence=0.98,
            rule_used="bootstrap_external_id",
            resolver_version=decision.resolver_version,
            normalized_name=decision.normalized_name,
            candidate_player_uids=[player_uid],
            explanation={"created_new_identity": True},
        )

    event_id = persist_mapping_event(session, payload, decision)
    if decision.status in {"unresolved", "conflict"}:
        queue_mapping_review(session, event_id=event_id, payload=payload, decision=decision)
    return decision


def apply_manual_mapping_resolution(
    session: Any,
    *,
    queue_id: str,
    action: str,
    reviewer: str,
    player_uid: Optional[str],
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    queue_row = session.execute(
        text(
            """
            SELECT
              q.id::text AS id,
              q.mapping_event_id::text AS mapping_event_id,
              q.observed_source,
              q.observed_external_id,
              q.observed_player_name,
              q.normalized_name,
              q.observed_team,
              q.observed_position,
              q.observed_season,
              q.observed_week
            FROM nfl_player_mapping_review_queue q
            WHERE q.id = CAST(:queue_id AS uuid)
            LIMIT 1
            """
        ),
        {"queue_id": queue_id},
    ).fetchone()
    if queue_row is None:
        return {"updated": False, "reason": "queue_item_not_found"}
    row = dict(queue_row._mapping)

    normalized_action = str(action or "").strip().lower()
    if normalized_action not in {"approve", "reject"}:
        return {"updated": False, "reason": "invalid_action"}
    if normalized_action == "approve" and not player_uid:
        return {"updated": False, "reason": "player_uid_required_for_approve"}

    new_status = "approved" if normalized_action == "approve" else "rejected"
    session.execute(
        text(
            """
            UPDATE nfl_player_mapping_review_queue
            SET
              queue_status = :queue_status,
              reviewer = :reviewer,
              reviewer_notes = :reviewer_notes,
              approved_player_uid = CAST(:approved_player_uid AS uuid),
              reviewed_at = NOW(),
              updated_at = NOW()
            WHERE id = CAST(:queue_id AS uuid)
            """
        ),
        {
            "queue_status": new_status,
            "reviewer": reviewer,
            "reviewer_notes": notes,
            "approved_player_uid": player_uid,
            "queue_id": queue_id,
        },
    )
    if normalized_action == "approve" and player_uid:
        session.execute(
            text(
                """
                UPDATE nfl_player_mapping_events
                SET
                  status = 'manual_approved',
                  player_uid = CAST(:player_uid AS uuid),
                  explanation = explanation || CAST(:patch AS jsonb)
                WHERE id = CAST(:mapping_event_id AS uuid)
                """
            ),
            {
                "player_uid": player_uid,
                "mapping_event_id": row["mapping_event_id"],
                "patch": json.dumps({"manual_reviewer": reviewer, "manual_notes": notes or ""}),
            },
        )
        if row.get("observed_external_id"):
            _upsert_source_map(
                session,
                source_system=str(row["observed_source"]),
                external_id=str(row["observed_external_id"]),
                player_uid=player_uid,
                confidence=1.0,
                trusted_link=True,
                metadata={
                    "rule_used": "manual_approval",
                    "reviewer": reviewer,
                    "reviewed_at": _utc_now().isoformat(),
                },
            )
    return {"updated": True, "queue_id": queue_id, "status": new_status}


def compute_identity_quality_snapshot(
    session: Any,
    *,
    season: Optional[int],
    week: Optional[int],
    source_system: Optional[str],
    resolver_version: str = DEFAULT_RESOLVER_VERSION,
) -> Dict[str, Any]:
    filter_sql = """
      WHERE (:season IS NULL OR observed_season = :season)
        AND (:week IS NULL OR observed_week = :week)
        AND (:source_system IS NULL OR observed_source = :source_system)
    """
    base_row = session.execute(
        text(
            f"""
            SELECT
              COUNT(*)::int AS total_events,
              SUM(CASE WHEN status IN ('mapped', 'manual_approved') THEN 1 ELSE 0 END)::int AS mapped_events,
              SUM(CASE WHEN status = 'mapped' AND confidence >= :trusted_threshold THEN 1 ELSE 0 END)::int AS high_conf_mapped,
              SUM(CASE WHEN status = 'unresolved' THEN 1 ELSE 0 END)::int AS unresolved_events,
              SUM(CASE WHEN status = 'conflict' THEN 1 ELSE 0 END)::int AS conflict_events
            FROM nfl_player_mapping_events
            {filter_sql}
            """
        ),
        {
            "season": season,
            "week": week,
            "source_system": source_system,
            "trusted_threshold": TRUSTED_LINK_MIN_CONFIDENCE,
        },
    ).fetchone()
    remap_row = session.execute(
        text(
            f"""
            SELECT
              SUM(CASE WHEN rule_used = 'guardrail_trusted_link_no_silent_remap' THEN 1 ELSE 0 END)::int AS remap_count,
              SUM(CASE WHEN status = 'manual_approved' AND rule_used = 'manual_reversal' THEN 1 ELSE 0 END)::int AS reversal_count
            FROM nfl_player_mapping_events
            {filter_sql}
            """
        ),
        {"season": season, "week": week, "source_system": source_system},
    ).fetchone()
    freshness_row = session.execute(
        text(
            """
            SELECT
              EXTRACT(EPOCH FROM (NOW() - MAX(last_seen_at))) / 3600.0 AS source_freshness_hours
            FROM nfl_player_source_id_map
            WHERE (:source_system IS NULL OR source_system = :source_system)
            """
        ),
        {"source_system": source_system},
    ).fetchone()

    total = int((base_row.total_events if base_row else 0) or 0)
    mapped = int((base_row.mapped_events if base_row else 0) or 0)
    high_conf = int((base_row.high_conf_mapped if base_row else 0) or 0)
    unresolved = int((base_row.unresolved_events if base_row else 0) or 0)
    conflicts = int((base_row.conflict_events if base_row else 0) or 0)
    remap_count = int((remap_row.remap_count if remap_row else 0) or 0)
    reversal_count = int((remap_row.reversal_count if remap_row else 0) or 0)
    freshness_hours = _safe_float((freshness_row.source_freshness_hours if freshness_row else None), default=9999.0)

    denominator = float(total or 1)
    coverage_rate = round(mapped / denominator, 6)
    high_conf_rate = round(high_conf / denominator, 6)
    unresolved_rate = round(unresolved / denominator, 6)
    conflict_rate = round(conflicts / denominator, 6)

    if unresolved_rate > NO_PUBLISH_MAX_UNRESOLVED_RATE or conflict_rate > NO_PUBLISH_MAX_CONFLICT_RATE:
        readiness = "no-go"
    elif unresolved_rate > (NO_PUBLISH_MAX_UNRESOLVED_RATE * 0.65) or conflict_rate > (NO_PUBLISH_MAX_CONFLICT_RATE * 0.65):
        readiness = "warning"
    else:
        readiness = "go"

    return {
        "resolver_version": resolver_version,
        "season": season,
        "week": week,
        "source_system": source_system,
        "total_events": total,
        "coverage_rate": coverage_rate,
        "high_confidence_auto_map_rate": high_conf_rate,
        "unresolved_rate": unresolved_rate,
        "conflict_rate": conflict_rate,
        "remap_count": remap_count,
        "reversal_count": reversal_count,
        "source_freshness_hours": round(freshness_hours, 3) if freshness_hours is not None else None,
        "readiness_status": readiness,
        "metrics": {
            "mapped_events": mapped,
            "high_confidence_mapped_events": high_conf,
            "unresolved_events": unresolved,
            "conflict_events": conflicts,
        },
    }


def persist_identity_quality_snapshot(session: Any, payload: Dict[str, Any]) -> None:
    session.execute(
        text(
            """
            INSERT INTO nfl_player_mapping_quality_snapshots (
              snapshot_date, season, week, resolver_version, source_system,
              coverage_rate, high_confidence_auto_map_rate, unresolved_rate, conflict_rate,
              remap_count, reversal_count, source_freshness_hours, readiness_status, metrics, created_at
            ) VALUES (
              CURRENT_DATE, :season, :week, :resolver_version, :source_system,
              :coverage_rate, :high_confidence_auto_map_rate, :unresolved_rate, :conflict_rate,
              :remap_count, :reversal_count, :source_freshness_hours, :readiness_status, CAST(:metrics AS jsonb), NOW()
            )
            ON CONFLICT (snapshot_date, resolver_version, source_system, season, week) DO UPDATE SET
              coverage_rate = EXCLUDED.coverage_rate,
              high_confidence_auto_map_rate = EXCLUDED.high_confidence_auto_map_rate,
              unresolved_rate = EXCLUDED.unresolved_rate,
              conflict_rate = EXCLUDED.conflict_rate,
              remap_count = EXCLUDED.remap_count,
              reversal_count = EXCLUDED.reversal_count,
              source_freshness_hours = EXCLUDED.source_freshness_hours,
              readiness_status = EXCLUDED.readiness_status,
              metrics = EXCLUDED.metrics,
              created_at = NOW()
            """
        ),
        {
            "season": int(payload.get("season")) if payload.get("season") is not None else -1,
            "week": int(payload.get("week")) if payload.get("week") is not None else -1,
            "resolver_version": payload.get("resolver_version") or DEFAULT_RESOLVER_VERSION,
            "source_system": str(payload.get("source_system") or ""),
            "coverage_rate": payload.get("coverage_rate"),
            "high_confidence_auto_map_rate": payload.get("high_confidence_auto_map_rate"),
            "unresolved_rate": payload.get("unresolved_rate"),
            "conflict_rate": payload.get("conflict_rate"),
            "remap_count": payload.get("remap_count"),
            "reversal_count": payload.get("reversal_count"),
            "source_freshness_hours": payload.get("source_freshness_hours"),
            "readiness_status": payload.get("readiness_status"),
            "metrics": json.dumps(payload.get("metrics") or {}),
        },
    )
