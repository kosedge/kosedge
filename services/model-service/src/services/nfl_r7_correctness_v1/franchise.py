"""Franchise-key identity. Relocation aliases only. CERT=0."""

from __future__ import annotations

from typing import Any, Mapping

from src.services.nfl_r7_correctness_v1.pins import FRANCHISE_ALIASES
from src.services.nfl_t5107u.q2 import PRIOR_ALIAS
from src.services.nfl_t5208u.hashing import canonical_sha256


class FranchiseRefuse(ValueError):
    """Fail-closed franchise identity."""


def franchise_key(code: Any) -> str:
    raw = str(code or "").strip().upper()
    if not raw:
        raise FranchiseRefuse("empty team code")
    if raw in FRANCHISE_ALIASES:
        return FRANCHISE_ALIASES[raw]
    if raw in PRIOR_ALIAS:
        return PRIOR_ALIAS[raw]
    if len(raw) > 4 or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for ch in raw):
        raise FranchiseRefuse(f"team code not a franchise token: {code!r}")
    return raw


def franchise_bind(home_team: Any, away_team: Any) -> dict[str, str]:
    home_raw = str(home_team or "").strip().upper()
    away_raw = str(away_team or "").strip().upper()
    home = franchise_key(home_raw)
    away = franchise_key(away_raw)
    if home == away:
        raise FranchiseRefuse(f"home/away franchise collision {home}")
    return {
        "home_team_raw": home_raw,
        "away_team_raw": away_raw,
        "franchise_key_home": home,
        "franchise_key_away": away,
    }


def q2_consumed_franchise_aliases() -> dict[str, str]:
    """Alias map actually consumed on the Q2 path (PRIOR_ALIAS ∪ product keys)."""
    consumed = dict(PRIOR_ALIAS)
    consumed.update(FRANCHISE_ALIASES)
    return dict(sorted(consumed.items()))


def key_row_teams(row: Mapping[str, Any]) -> dict[str, Any]:
    mapped = dict(row)
    mapped["home_team"] = franchise_key(row.get("home_team"))
    mapped["away_team"] = franchise_key(row.get("away_team"))
    if "source_byte_hash" in mapped:
        mapped["source_byte_hash"] = canonical_sha256(
            {key: value for key, value in mapped.items() if key != "source_byte_hash"}
        )
    return mapped


def key_packet_and_history_for_q2(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Map target + history home/away through franchise_key BEFORE the Q2 ridge.

    SD/STL must not split from LAC/LAR. Product aliases (WSH→WAS, LA→LAR)
    are consumed here so config bind is not decorative.
    """
    keyed = dict(packet)
    original_env = dict(packet.get("envelope") or {})
    env = dict(original_env)
    env["home_team"] = franchise_key(env.get("home_team"))
    env["away_team"] = franchise_key(env.get("away_team"))
    keyed["envelope"] = env
    keyed_history = [key_row_teams(row) for row in history]
    return keyed, keyed_history
