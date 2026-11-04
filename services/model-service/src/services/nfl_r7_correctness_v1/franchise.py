"""Franchise-key identity. Relocation aliases only. CERT=0."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from src.services.nfl_r7_correctness_v1.pins import (
    CANONICAL_FRANCHISES,
    FRANCHISE_ALIASES,
    LA_SOURCE_MAP,
)
from src.services.nfl_t5107u.q2 import PRIOR_ALIAS, REGRESS_FRAC
from src.services.nfl_t5208u.hashing import canonical_sha256


class FranchiseRefuse(ValueError):
    """Fail-closed franchise identity."""


def franchise_key(code: Any, *, source: Any = None) -> str:
    raw = str(code or "").strip().upper()
    if not raw:
        raise FranchiseRefuse("empty team code")
    if raw == "LA":
        src = str(source or "").strip().upper()
        if src not in LA_SOURCE_MAP:
            raise FranchiseRefuse("source-unqualified LA refused")
        return LA_SOURCE_MAP[src]
    if raw in FRANCHISE_ALIASES:
        return FRANCHISE_ALIASES[raw]
    if raw in PRIOR_ALIAS:
        return PRIOR_ALIAS[raw]
    if raw in CANONICAL_FRANCHISES:
        return raw
    raise FranchiseRefuse(f"unknown franchise token: {code!r}")


def franchise_bind(home_team: Any, away_team: Any, *, home_source: Any = None, away_source: Any = None) -> dict[str, str]:
    home_raw = str(home_team or "").strip().upper()
    away_raw = str(away_team or "").strip().upper()
    home = franchise_key(home_raw, source=home_source)
    away = franchise_key(away_raw, source=away_source)
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
    mapped["home_team"] = franchise_key(row.get("home_team"), source=row.get("home_team_source"))
    mapped["away_team"] = franchise_key(row.get("away_team"), source=row.get("away_team_source"))
    if "source_byte_hash" in mapped:
        mapped["source_byte_hash"] = canonical_sha256(
            {key: value for key, value in mapped.items() if key != "source_byte_hash"}
        )
    return mapped


def assert_canonical_state_slots(teams: Iterable[str]) -> None:
    raw = {str(team) for team in teams}
    for team in raw:
        canon = franchise_key(team)
        if team != canon and canon in raw:
            raise FranchiseRefuse(f"duplicate legacy-slot {team} and {canon}")


def collapse_to_canonical_slots(prev: Mapping[str, float]) -> dict[str, float]:
    assert_canonical_state_slots(prev)
    out: dict[str, float] = {}
    for team, val in prev.items():
        key = franchise_key(team)
        number = float(val)
        if key in out and out[key] != number:
            raise FranchiseRefuse(f"duplicate legacy-slot collision {key}")
        out[key] = number
    return out


def canonical_carry_prior(prev: Mapping[str, float], regress_frac: float = REGRESS_FRAC) -> dict[str, float]:
    """One canonical slot throughout carry. Does not inject PRIOR_ALIAS reverse keys."""
    collapsed = collapse_to_canonical_slots(prev)
    rate = float(regress_frac)
    return {key: (1.0 - rate) * value for key, value in collapsed.items()}


def key_packet_and_history_for_q2(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Map target + history home/away through franchise_key BEFORE the Q2 ridge.

    SD/STL must not split from LAC/LAR. Unqualified LA refuses.
    """
    keyed = dict(packet)
    original_env = dict(packet.get("envelope") or {})
    env = dict(original_env)
    env["home_team"] = franchise_key(env.get("home_team"), source=env.get("home_team_source"))
    env["away_team"] = franchise_key(env.get("away_team"), source=env.get("away_team_source"))
    keyed["envelope"] = env
    keyed_history = [key_row_teams(row) for row in history]
    teams = [env["home_team"], env["away_team"]]
    for row in keyed_history:
        teams.append(str(row["home_team"]))
        teams.append(str(row["away_team"]))
    assert_canonical_state_slots(teams)
    return keyed, keyed_history
