"""Offline 2020–23 REG forecast builder (CERT=0). No EVAL scoring.

Challenger: mC = 0.5*mIF + 0.5*mQ2 (home−away points).
No extra HFA, no market blend, no weight search. No Stage C columns.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .if_control import (
    IF_TIP,
    LABEL_ARCHIVED,
    LABEL_RECONSTRUCTED,
    IFResolution,
    resolve_if_margin,
    retained_if_arm,
)
from .q2 import (
    A_Q2,
    B_Q2,
    FIT_POLICY,
    PARAMETER_LABEL,
    Q2S_WEIGHT,
    SEALED_SEASONS,
    T5107U_DEV_SEASONS,
    T5107U_EVAL_SEASONS,
    Game,
    asof_for_targets,
    assert_asof_no_self_target,
    parse_kickoff,
    q2_pm_new,
    verify_q2_transfer_policy,
)

CHALLENGER_WEIGHT = Q2S_WEIGHT
LABEL = "RESEARCH_CONSUMED_RETRO"
CERT_CANDIDATE = 0
SCHEMA = "nfl-t5107u-forecast-v1"
FORBIDDEN_COLUMNS = (
    "stage_c",
    "scored_index",
    "1ee90fac",
    "packaged_margin",
    "trailing_epa",
)

STAGE_C_KEYS = frozenset(
    {
        "stage_c",
        "scored_index",
        "scored_columns",
        "packaged_margin",
        "trailing_epa",
        "kei_score",
    }
)


class BuilderRefuse(ValueError):
    """Fail-closed builder."""


@dataclass
class ForecastRow:
    game_id: str
    season: int
    week: int
    season_type: str
    home: str
    away: str
    kickoff_utc: str
    split: str  # DEV | EVAL | CONTEXT
    m_if: float | None
    m_q2: float | None
    m_challenger: float | None
    if_status: str
    if_label: str
    q2_status: str
    q2_parameter_label: str
    blocked_legs: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    rating_diff: float | None = None
    n_asof_games: int | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "season": self.season,
            "week": self.week,
            "season_type": self.season_type,
            "home": self.home,
            "away": self.away,
            "kickoff_utc": self.kickoff_utc,
            "split": self.split,
            "m_if": self.m_if,
            "m_q2": self.m_q2,
            "m_challenger": self.m_challenger,
            "if_status": self.if_status,
            "if_label": self.if_label,
            "q2_status": self.q2_status,
            "q2_parameter_label": self.q2_parameter_label,
            "fit_policy": FIT_POLICY,
            "blocked_legs": list(self.blocked_legs),
            "missing_fields": list(self.missing_fields),
            "missing_artifacts": list(self.missing_artifacts),
            "rating_diff": self.rating_diff,
            "n_asof_games": self.n_asof_games,
            "label": LABEL,
            "cert_candidate": CERT_CANDIDATE,
            "notes": list(self.notes),
            "eval": None,
            "scoring": None,
            "stage_c": None,
        }


def challenger_margin(
    m_if: Any,
    m_q2: Any,
    *,
    w: float = CHALLENGER_WEIGHT,
    extra_hfa: float = 0.0,
    market_blend: float = 0.0,
) -> float:
    if extra_hfa != 0.0:
        raise BuilderRefuse("Add NO extra HFA; blend two complete margins")
    if market_blend != 0.0:
        raise BuilderRefuse("market blending is forbidden")
    if w != CHALLENGER_WEIGHT:
        raise BuilderRefuse("w is frozen at the predeclared 0.5; no weight search")
    try:
        if_m = float(m_if)
        q2_m = float(m_q2)
    except (TypeError, ValueError) as exc:
        raise BuilderRefuse("non-finite complete margin") from exc
    if not math.isfinite(if_m) or not math.isfinite(q2_m):
        raise BuilderRefuse("non-finite complete margin")
    return CHALLENGER_WEIGHT * if_m + CHALLENGER_WEIGHT * q2_m


def _split_for(season: int) -> str:
    if season in T5107U_DEV_SEASONS:
        return "DEV"
    if season in T5107U_EVAL_SEASONS:
        return "EVAL"
    if season in SEALED_SEASONS:
        raise BuilderRefuse(f"refusing sealed season {season}")
    return "CONTEXT"


def _scan_forbidden(payload: Mapping[str, Any], *, where: str) -> None:
    blob = json.dumps(payload, default=str).casefold()
    for token in FORBIDDEN_COLUMNS:
        if token in blob:
            raise BuilderRefuse(f"{where} cites forbidden column {token}")
    extra = STAGE_C_KEYS.intersection(payload)
    if extra:
        raise BuilderRefuse(f"{where} contains Stage C / scored keys {sorted(extra)}")


def _q2_for_targets(
    history: Sequence[Game],
    targets: Sequence[Game],
) -> dict[str, tuple[float, float, int]]:
    """Return game_id -> (m_q2, rating_diff, n_asof)."""
    if any(g.season in SEALED_SEASONS for g in list(history) + list(targets)):
        raise BuilderRefuse("refusing 2024–26 rows")
    feats = asof_for_targets(history, targets)
    assert_asof_no_self_target(history, feats)
    out: dict[str, tuple[float, float, int]] = {}
    for feat in feats:
        out[feat.game.game_id] = (
            q2_pm_new(feat.rating_diff),
            feat.rating_diff,
            feat.n_asof_games,
        )
    return out


def build_forecasts(
    targets: Sequence[Mapping[str, Any] | Game],
    *,
    history: Sequence[Mapping[str, Any] | Game] | None = None,
    archived_if: Mapping[str, Mapping[str, Any]] | None = None,
    recon_packets: Mapping[str, Mapping[str, Any]] | None = None,
    reconstructed_if_mus: Mapping[str, float] | None = None,
    if_tree_present: bool | None = None,
    allow_eval_generation: bool = False,
    frozen_manifest_sealed: bool = False,
) -> dict[str, Any]:
    """Build per-game forecasts. Does not join target outcomes for scoring."""
    transfer = verify_q2_transfer_policy(proposed_refit=False)
    games = [_coerce_game(row, where="target") for row in targets]
    hist = [_coerce_game(row, where="history") for row in (history or [])]
    # Prior-game history may include earlier targets' scores; never the target itself
    # unless that row is a *different* already-played game.
    hist_ids_at_or_after = {
        (g.game_id, g.kickoff_utc)
        for g in hist
        if any(t.game_id == g.game_id and t.kickoff_utc <= g.kickoff_utc for t in games)
        and g.game_id in {t.game_id for t in games}
    }
    if hist_ids_at_or_after:
        # Same game_id in history at/after its own target kickoff is a leak.
        leaks = [gid for gid, _ in hist_ids_at_or_after if any(t.game_id == gid for t in games)]
        if leaks:
            raise BuilderRefuse(f"history includes target game rows {sorted(set(leaks))}")

    eval_targets = [g for g in games if g.season in T5107U_EVAL_SEASONS]
    if eval_targets and not (allow_eval_generation and frozen_manifest_sealed):
        raise BuilderRefuse(
            "EVAL sequential forecast generation is gated on a sealed "
            "FROZEN_MANIFEST (design/input-source/fit-policy). "
            "Pass frozen_manifest_sealed=True and allow_eval_generation=True "
            "only after seal. Scoring remains refused."
        )

    if reconstructed_if_mus:
        raise BuilderRefuse("produce-μ required; supplied reconstructed_if_mus is not authorized")
    archived_if = archived_if or {}
    recon_packets = recon_packets or {}

    q2_by_id: dict[str, tuple[float, float, int]] = {}
    q2_block_reason: str | None = None
    try:
        q2_by_id = _q2_for_targets(hist, games)
    except Exception as exc:  # noqa: BLE001 — surface as blocked Q2 leg
        q2_block_reason = str(exc)

    rows: list[ForecastRow] = []
    if_resolutions: list[IFResolution] = []
    for game in games:
        _scan_forbidden(
            game.__dict__ if not isinstance(game, Mapping) else game,  # type: ignore[arg-type]
            where=game.game_id,
        )
        if_res = resolve_if_margin(
            game.game_id,
            archived=archived_if.get(game.game_id),
            recon_packet=recon_packets.get(game.game_id),
        )
        if_resolutions.append(if_res)

        blocked: list[str] = []
        m_q2 = rating_diff = n_asof = None
        q2_status = "ok"
        if q2_block_reason:
            blocked.append("q2")
            q2_status = "blocked"
        elif game.game_id not in q2_by_id:
            blocked.append("q2")
            q2_status = "blocked"
        else:
            m_q2, rating_diff, n_asof = q2_by_id[game.game_id]

        m_if = if_res.margin_mu
        if if_res.status == "blocked":
            blocked.append("if")
        m_c = None
        if m_if is not None and m_q2 is not None:
            m_c = challenger_margin(m_if, m_q2)
        else:
            blocked.append("challenger")

        notes = list(if_res.notes)
        if q2_block_reason:
            notes.append(f"q2 blocked: {q2_block_reason}")
        notes.append("IF control retained; archived vs reconstructed labeled.")
        if if_res.label == LABEL_ARCHIVED:
            notes.append("using archived IF mus")
        elif if_res.label == LABEL_RECONSTRUCTED:
            notes.append("using newly reconstructed IF mus")

        rows.append(
            ForecastRow(
                game_id=game.game_id,
                season=game.season,
                week=game.week,
                season_type=game.season_type,
                home=game.home,
                away=game.away,
                kickoff_utc=game.kickoff_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                split=_split_for(game.season),
                m_if=m_if,
                m_q2=m_q2,
                m_challenger=m_c,
                if_status=if_res.status,
                if_label=if_res.label,
                q2_status=q2_status,
                q2_parameter_label=PARAMETER_LABEL,
                blocked_legs=sorted(set(blocked)),
                missing_fields=list(if_res.missing_fields),
                missing_artifacts=list(if_res.missing_artifacts),
                rating_diff=rating_diff,
                n_asof_games=n_asof,
                notes=notes,
            )
        )

    if_counts = retained_if_arm(if_resolutions)
    payload = {
        "schema_version": SCHEMA,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "purpose": "offline_forecast_builder_only",
        "if_tip": IF_TIP,
        "fit_policy": transfer,
        "if_arm": if_counts,
        "forecasts": [row.as_dict() for row in rows],
        "eval": None,
        "scoring": None,
        "stage_c": None,
        "notes": [
            "CERT=0. RESEARCH_CONSUMED_RETRO. DRAFT≠merge.",
            "No EXEC scoring. No 2024–25. No Stage C / scored columns.",
            "mC = 0.5*mIF + 0.5*mQ2; extra HFA / market blend / weight search refused.",
        ],
    }
    return payload


def hash_forecasts(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _coerce_game(row: Mapping[str, Any] | Game, *, where: str) -> Game:
    if isinstance(row, Game):
        if row.season in SEALED_SEASONS:
            raise BuilderRefuse(f"{where} sealed season {row.season}")
        if str(row.season_type or "REG").upper() != "REG":
            raise BuilderRefuse(f"{where} {row.game_id} is not REG")
        return row
    _scan_forbidden(row, where=where)
    season = int(row["season"])
    if season in SEALED_SEASONS:
        raise BuilderRefuse(f"{where} sealed season {season}")
    season_type = str(row.get("season_type") or row.get("game_type") or "REG").upper()
    if season_type != "REG":
        raise BuilderRefuse(f"{where} {row.get('game_id')} is not REG")
    home = str(row.get("home") or row.get("home_team") or "").strip()
    away = str(row.get("away") or row.get("away_team") or "").strip()
    if not home or not away:
        raise BuilderRefuse(f"{where} missing home/away")
    kickoff = parse_kickoff(row.get("kickoff_utc") or row.get("kickoff"))
    hs = row.get("home_score")
    aws = row.get("away_score")
    return Game(
        season=season,
        week=int(row.get("week") or 0),
        game_id=str(row.get("game_id") or f"{season}_{row.get('week')}_{away}_{home}"),
        home=home,
        away=away,
        kickoff_utc=kickoff,
        home_score=None if hs in (None, "") else float(hs),
        away_score=None if aws in (None, "") else float(aws),
        season_type=season_type,
    )


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
