"""Franchise-key identity. Relocation aliases only. CERT=0."""

from __future__ import annotations

from typing import Any

from src.services.nfl_r7_correctness_v1.pins import FRANCHISE_ALIASES


class FranchiseRefuse(ValueError):
    """Fail-closed franchise identity."""


def franchise_key(code: Any) -> str:
    raw = str(code or "").strip().upper()
    if not raw:
        raise FranchiseRefuse("empty team code")
    if raw in FRANCHISE_ALIASES:
        return FRANCHISE_ALIASES[raw]
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
