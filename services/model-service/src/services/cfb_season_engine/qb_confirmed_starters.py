"""Week-scoped confirmed QB1 join into the existing 1C–1E path.

Doctrine (Chapter 3 confirmation — not a second QB model):
  packaged ESPN qb → expert override → **confirmed starter** → build_qb_situation

Identity only. Does not invent ESPN-missing names, does not fork
``qb_situation``, does not touch ``EFF_CARRY_SHRINK`` / travel / rebuild.
``rest_travel`` remains a later class (see Ch3 situation audit).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
CONFIRM_PATH = DATA_DIR / "cfb_qb_confirmed_starters_w1_2026.json"

_CACHE: Optional[Dict[str, Any]] = None


def confirm_path() -> Path:
    return CONFIRM_PATH


def load_confirmed_starters() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not CONFIRM_PATH.is_file():
        _CACHE = {"as_of": "", "week": 1, "teams": {}, "present": False}
        return _CACHE
    raw = json.loads(CONFIRM_PATH.read_text(encoding="utf-8"))
    raw["present"] = True
    _CACHE = raw
    return raw


def clear_confirmed_starters_cache() -> None:
    global _CACHE
    _CACHE = None


def confirmation_for(team: str, *, week: Optional[int] = None) -> Optional[Dict[str, Any]]:
    book = load_confirmed_starters()
    book_week = int(book.get("week") or 1)
    if week is not None and int(week) != book_week:
        return None
    teams = book.get("teams") or {}
    row = teams.get(str(team).upper())
    if not row:
        return None
    if str(row.get("status") or "").lower() != "confirmed":
        return None
    return row


def apply_confirmed_starter(
    team: str,
    payload: Optional[Mapping[str, Any]],
    *,
    week: Optional[int] = None,
) -> Dict[str, Any]:
    """Merge a W1-confirmed starter identity onto the QB payload.

    No-op when the book has no row, status is not confirmed, starter_key is
    missing, or the key already matches the payload (zero-move path).
    Never invents a starter_key that is absent from the override/pack payload
    pair without an explicit key in the confirmation book (book is SoT for
    identity; callers must only list ESPN-present keys).
    """
    out = dict(payload or {})
    row = confirmation_for(team, week=week)
    if not row:
        return out

    name = str(row.get("starter_name") or "").strip()
    key = str(row.get("starter_key") or "").strip()
    if not name or not key:
        return out

    prior_key = str(out.get("starter_key") or "").strip()
    prior_name = str(out.get("starter_name") or out.get("qb_name") or "").strip()
    unchanged = prior_key == key and (not prior_name or prior_name == name)

    book = load_confirmed_starters()
    as_of = str(book.get("as_of") or "")
    out["starter_name"] = name
    out["qb_name"] = name
    out["starter_key"] = key
    # Identity stamp only — class / talent stay on the existing 1C–1E inputs.
    out["confirmation_week"] = int(book.get("week") or 1)
    out["confirmation_as_of"] = as_of
    out["confirmation_matched"] = bool(unchanged or row.get("matched_1c1e_input"))

    note = f"W{book.get('week', 1)} confirmed starter {as_of} ({name})."
    if unchanged or row.get("matched_1c1e_input"):
        note += " Matched prior 1C–1E input — no identity move."
    existing = str(out.get("notes") or "").strip()
    # Avoid duplicating the stamp on repeated applies.
    if "confirmed starter" not in existing.lower():
        out["notes"] = f"{note} {existing}".strip()
    return out


def documentation() -> Dict[str, Any]:
    book = load_confirmed_starters()
    teams = book.get("teams") or {}
    return {
        "module": "src.services.cfb_season_engine.qb_confirmed_starters",
        "as_of": book.get("as_of"),
        "week": book.get("week"),
        "n": len(teams),
        "path": str(CONFIRM_PATH),
        "open_camps_no_lock": book.get("open_camps_no_lock") or [],
        "doctrine": book.get("doctrine"),
        "applies_to": ["universe load", "preseason prior"],
        "pipeline": "pack qb → expert override → confirmed starter → build_qb_situation",
        "does_not": [
            "fork qb_situation / 1C–1E",
            "invent ESPN-missing identities",
            "set rest_travel",
            "edit EFF_CARRY_SHRINK",
            "team-name compose ifs",
        ],
    }
