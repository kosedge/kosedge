"""AC-7 two-stream scaffolding. S-IND forbids market inputs.

Does not invent sealed predictions. Separate file names / sha slots only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

STREAM_MKT = "S-MKT"
STREAM_IND = "S-IND"

# Market / blend / price tokens that may not appear as S-IND feature keys.
FORBIDDEN_S_IND_KEYS = frozenset(
    {
        "line",
        "spread",
        "spread_home",
        "total",
        "total_points",
        "price",
        "odds",
        "close",
        "open",
        "clv",
        "blend",
        "blend_weight",
        "market",
        "market_prob",
        "implied_prob",
        "dk_spread",
        "fd_spread",
        "consensus_line",
        "best_line",
    }
)

FORBIDDEN_S_IND_SUBSTR = (
    "market",
    "odds",
    "blend",
    "close_line",
    "open_line",
    "implied",
)


class ForbiddenInputError(ValueError):
    """S-IND fail-closed when a market-derived field is injected."""


@dataclass
class StreamBundle:
    stream: str
    path: str
    sha256: str
    sealed: bool = False
    features: dict[str, Any] = field(default_factory=dict)


def stream_filenames(game_id: str) -> dict[str, str]:
    safe = "".join(ch if ch.isalnum() or ch in "-_@" else "_" for ch in game_id)
    return {
        STREAM_MKT: f"{safe}.s_mkt.json",
        STREAM_IND: f"{safe}.s_ind.json",
    }


def forbidden_s_ind_keys(features: Mapping[str, Any]) -> list[str]:
    hits: list[str] = []
    for key in features:
        compact = str(key).strip().lower()
        if compact in FORBIDDEN_S_IND_KEYS:
            hits.append(str(key))
            continue
        if any(token in compact for token in FORBIDDEN_S_IND_SUBSTR):
            hits.append(str(key))
    return hits


def check_s_ind_forbidden_inputs(features: Mapping[str, Any]) -> None:
    hits = forbidden_s_ind_keys(features)
    if hits:
        raise ForbiddenInputError(
            f"S-IND forbidden-input check failed closed: {', '.join(sorted(hits))}"
        )


def scaffold_streams(
    game_id: str,
    *,
    s_mkt_features: Mapping[str, Any] | None = None,
    s_ind_features: Mapping[str, Any] | None = None,
) -> dict[str, StreamBundle]:
    names = stream_filenames(game_id)
    if s_ind_features is not None:
        check_s_ind_forbidden_inputs(s_ind_features)
    return {
        STREAM_MKT: StreamBundle(
            stream=STREAM_MKT,
            path=names[STREAM_MKT],
            sha256="",  # UNSET until a real artifact is written; do not invent
            sealed=False,
            features=dict(s_mkt_features or {}),
        ),
        STREAM_IND: StreamBundle(
            stream=STREAM_IND,
            path=names[STREAM_IND],
            sha256="",
            sealed=False,
            features=dict(s_ind_features or {}),
        ),
    }


def refuse_seal(streams: Iterable[StreamBundle]) -> None:
    """AC-12: Cursor cannot seal-ack. Always refuse."""
    del streams
    raise PermissionError(
        "AC-12 seal-ack separation: Cursor cannot seal-ack. "
        "Seal-ack = IMV verification + DFG custodian receipt."
    )
