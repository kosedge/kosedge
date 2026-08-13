"""Expert QB-situation SoT overlay for 2026 (news → note → override).

The ESPN roster pack remains the identity feed. This module is the *only*
place camp/news conflicts override situation class / named QB1. Callers apply
it at read time (universe load + preseason prior). Do not invent players who
are missing from ESPN.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
OVERRIDE_PATH = DATA_DIR / "cfb_qb_situation_overrides_2026.json"

_CACHE: Optional[Dict[str, Any]] = None


def override_path() -> Path:
    return OVERRIDE_PATH


def load_qb_overrides() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not OVERRIDE_PATH.is_file():
        _CACHE = {"as_of": "", "teams": {}, "present": False}
        return _CACHE
    raw = json.loads(OVERRIDE_PATH.read_text(encoding="utf-8"))
    raw["present"] = True
    _CACHE = raw
    return raw


def override_for(team: str) -> Optional[Dict[str, Any]]:
    teams = load_qb_overrides().get("teams") or {}
    return teams.get(str(team).upper())


def apply_qb_situation_override(
    team: str,
    payload: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Merge expert override onto a packaged QB payload.

    Unknown teams pass through. Listed names are only replaced when the
    override points at an ESPN-present identity (starter_key set).
    """
    out = dict(payload or {})
    row = override_for(team)
    if not row:
        return out

    book = load_qb_overrides()
    as_of = str(book.get("as_of") or "")
    qb_class = str(row.get("qb_class") or "open_competition")
    out["qb_class"] = qb_class
    out["open_competition"] = bool(row.get("open_competition", qb_class == "open_competition"))
    out["is_portal"] = bool(row.get("is_portal", qb_class == "portal"))
    out["is_true_freshman"] = bool(row.get("is_true_freshman", False))
    out["source"] = f"expert_qb_override_{as_of}"
    out["fidelity"] = "approximate"
    out["identity_fidelity"] = "real" if row.get("starter_key") else out.get(
        "identity_fidelity", "approximate"
    )

    if row.get("starter_name") and row.get("starter_key"):
        out["starter_name"] = str(row["starter_name"])
        out["qb_name"] = str(row["starter_name"])
        out["starter_key"] = str(row["starter_key"])
    # else keep pack listed name; do not invent missing ESPN identities

    reason = str(row.get("reason") or "").strip()
    flag = "unconfirmed starter; elevated σ until games" if row.get("unconfirmed_starter") else "open / high uncertainty"
    note = f"QB SoT override {as_of} ({flag}). {reason}".strip()
    existing = str(out.get("notes") or "").strip()
    out["notes"] = f"{note} {existing}".strip()
    return out


def documentation() -> Dict[str, Any]:
    book = load_qb_overrides()
    teams = book.get("teams") or {}
    return {
        "module": "src.services.cfb_season_engine.qb_situation_overrides",
        "as_of": book.get("as_of"),
        "n": len(teams),
        "teams": sorted(teams),
        "path": str(OVERRIDE_PATH),
        "ops": book.get("ops"),
        "doctrine": book.get("doctrine"),
        "applies_to": ["universe load", "preseason prior"],
        "does_not": [
            "rewrite ESPN roster snapshot",
            "invent missing identities (Stockton, Underwood)",
            "set used_in_spread",
        ],
    }
