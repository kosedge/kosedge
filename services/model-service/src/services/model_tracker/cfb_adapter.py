"""CFB adapter — import PLAY/LEAN candidates from packaged KEI board."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.model_tracker.core import log_pick


def _kei_side_and_line(kei: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Derive bet side from KEI vs market edge.

    edge_pts = market − kei (home-relative). Positive ⇒ KEI likes home more
    than books ⇒ bet home; negative ⇒ bet away.
    """
    edge = kei.get("edge_pts")
    tag = str(kei.get("tag") or "").upper()
    if tag not in {"PLAY", "LEAN"}:
        return None
    mkt = kei.get("market_spread_home")
    kei_line = kei.get("kei_spread_home")
    if mkt is None or edge is None:
        return None
    try:
        edge_f = float(edge)
        mkt_f = float(mkt)
    except (TypeError, ValueError):
        return None
    side = "home" if edge_f >= 0 else "away"
    # Bet the market number on the chosen side (home-relative storage)
    return {
        "tag": tag,
        "side": side,
        "line_at_publish": mkt_f,
        "kei_line": float(kei_line) if kei_line is not None else None,
        "fair_line": float(kei.get("model_spread_home"))
        if kei.get("model_spread_home") is not None
        else None,
        "edge_pts": edge_f,
        "market_type": "spread",
    }


def candidates_from_kei_board(
    board: Mapping[str, Any],
    *,
    weeks: Optional[Sequence[int]] = None,
    tags: Sequence[str] = ("PLAY", "LEAN"),
) -> List[Dict[str, Any]]:
    wanted_weeks = {int(w) for w in weeks} if weeks is not None else None
    wanted_tags = {str(t).upper() for t in tags}
    season = int(board.get("season") or 2026)
    engine_version = board.get("engine_version")
    kei_version = board.get("kei_version")
    artifact_as_of = board.get("as_of") or board.get("generated_at")
    out: List[Dict[str, Any]] = []

    for raw in board.get("games") or []:
        if not isinstance(raw, dict):
            continue
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            continue
        if wanted_weeks is not None and week not in wanted_weeks:
            continue
        kei = raw.get("kei") if isinstance(raw.get("kei"), dict) else {}
        derived = _kei_side_and_line(kei)
        if not derived or derived["tag"] not in wanted_tags:
            continue
        home = str(raw.get("home") or raw.get("home_team") or "").upper()
        away = str(raw.get("away") or raw.get("away_team") or "").upper()
        if not home or not away:
            continue
        out.append(
            {
                "sport": "cfb",
                "season": season,
                "week": week,
                "game_id": str(raw.get("game_id")) if raw.get("game_id") else None,
                "home_team": home,
                "away_team": away,
                "market_type": derived["market_type"],
                "side": derived["side"],
                "line_at_publish": derived["line_at_publish"],
                "tag": derived["tag"],
                "edge_pts": derived["edge_pts"],
                "kei_line": derived["kei_line"],
                "fair_line": derived["fair_line"],
                "engine_version": engine_version or kei.get("kei_version"),
                "kei_version": kei_version or kei.get("kei_version"),
                "artifact_as_of": artifact_as_of,
                "confidence": kei.get("confidence"),
                "source": "kei_board",
                "created_by": "system",
                "payload": {
                    "kickoff": raw.get("kickoff"),
                    "neutral_site": raw.get("neutral_site"),
                    "fbs_vs_fbs": raw.get("fbs_vs_fbs"),
                    "investigate": kei.get("investigate"),
                    "play_threshold": kei.get("play_threshold"),
                    "lean_threshold": kei.get("lean_threshold"),
                },
            }
        )
    return out


def load_packaged_kei_board() -> Dict[str, Any]:
    from src.services.cfb_season_engine.product_desk import (
        KEI_BOARD_PATH,
        _load_json,
    )

    pack = _load_json(KEI_BOARD_PATH)
    if pack and "season" not in pack:
        pack = {**pack, "season": 2026}
    return pack


def import_kei_board_picks(
    *,
    weeks: Optional[Sequence[int]] = None,
    tags: Sequence[str] = ("PLAY", "LEAN"),
    dry_run: bool = False,
    lake_dir=None,
) -> Dict[str, Any]:
    board = load_packaged_kei_board()
    cands = candidates_from_kei_board(board, weeks=weeks, tags=tags)
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "n_candidates": len(cands),
            "candidates": cands,
            "board_as_of": board.get("as_of") or board.get("generated_at"),
            "note": (
                "Packaged board often has null market/edge (PASS). "
                "Desk should log manually when books are joined, or refresh KEI vs market first."
            ),
        }
    logged: List[Dict[str, Any]] = []
    for cand in cands:
        logged.append(log_pick(cand, lake_dir=lake_dir))
    return {
        "ok": True,
        "dry_run": False,
        "n_candidates": len(cands),
        "n_logged": len(logged),
        "picks": logged,
        "board_as_of": board.get("as_of") or board.get("generated_at"),
    }
