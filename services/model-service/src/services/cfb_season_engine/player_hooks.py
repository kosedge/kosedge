"""Thin player-level hooks (QB + skill) where identity is available.

Foundation pass: attach named hooks from packaged priors; do not invent
full player projection engines. Structure is ready for depth-chart feeds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.cfb_season_engine.types import PlayerHook, QbSituation


def build_player_hooks(
    team: str,
    payload_rows: Optional[Sequence[Mapping[str, Any]]] = None,
    *,
    qb: Optional[QbSituation] = None,
    default_source: str = "packaged_prior",
) -> List[PlayerHook]:
    """Build player hooks for a team; synthesize QB hook from Layer 2 if needed."""
    out: List[PlayerHook] = []
    for row in payload_rows or []:
        name = str(row.get("player_name", "") or "")
        key = str(row.get("player_key", "") or "")
        if not key and name:
            key = name.lower().replace(" ", "_").replace(".", "")
        fidelity = str(row.get("fidelity", "approximate"))
        if fidelity not in ("real", "approximate", "placeholder"):
            fidelity = "approximate"
        out.append(
            PlayerHook(
                player_key=key or f"{team.lower()}_unk",
                player_name=name or key,
                team=str(team),
                position=str(row.get("position", "WR")).upper(),
                depth_order=int(row.get("depth_order", 1) or 1),
                usage_share=float(row.get("usage_share", 0.0) or 0.0),
                talent=float(row.get("talent", 50.0) or 50.0),
                source=str(row.get("source", default_source)),
                fidelity=fidelity,  # type: ignore[arg-type]
            )
        )

    has_qb = any(h.position == "QB" for h in out)
    if qb and qb.starter_name and not has_qb:
        out.insert(
            0,
            PlayerHook(
                player_key=qb.starter_key or f"{team.lower()}_qb1",
                player_name=qb.starter_name,
                team=str(team),
                position="QB",
                depth_order=1,
                usage_share=0.92,
                talent=qb.qb_talent,
                source=qb.source,
                fidelity=qb.fidelity,
            ),
        )
    return out


def hooks_to_summaries(hooks: Sequence[PlayerHook]) -> List[Dict[str, Any]]:
    return [
        {
            "player_key": h.player_key,
            "player_name": h.player_name,
            "team": h.team,
            "position": h.position,
            "depth_order": h.depth_order,
            "usage_share": round(h.usage_share, 3),
            "talent": round(h.talent, 2),
            "source": h.source,
            "fidelity": h.fidelity,
        }
        for h in hooks
    ]


def documentation() -> Dict[str, Any]:
    return {
        "layer": "player_hooks",
        "name": "player_hooks",
        "module": "src.services.cfb_season_engine.player_hooks",
        "status": "thin",
        "real_vs_approximate": (
            "Hook wiring is REAL. Named skill/QB identities in packaged data "
            "are APPROXIMATE; full usage/production paths deferred."
        ),
        "focus": ["QB", "RB", "WR", "TE"],
    }
