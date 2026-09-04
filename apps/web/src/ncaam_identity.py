"""NCAAM team identity — fail-closed alias resolution (Python twin of lib/ncaam/identity.ts).

Canonical sport key: ncaam only (cbb retired as API/DB sport key).
Canonical team_id: clean KenPom-style team_norm (miami fl / miami oh).

P0: bare "miami" is OMIT — Miami FL ≠ Miami OH must never collapse.
Peer homonyms: bare "loyola" / "southern" also OMIT (aliases.json omit_aliases).
No fuzzy auto-publish joins; unknown / ambiguous → None.
Alias SoT: apps/web/lib/ncaam/aliases.json (shared with TS identity).
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_ALIAS_PATH = Path(__file__).resolve().parent.parent / "lib" / "ncaam" / "aliases.json"

RETIRED_NCAAM_SPORT_KEYS = frozenset({"cbb", "ncaab"})


def fold_ncaam_alias(raw: str) -> str:
    s = unicodedata.normalize("NFKD", str(raw or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("'", "").replace("`", "").replace("ʻ", "")
    s = re.sub(r"[^a-z0-9\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@lru_cache(maxsize=1)
def _load_doc() -> Dict[str, Any]:
    with open(_ALIAS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _aliases() -> Dict[str, str]:
    return dict(_load_doc().get("aliases") or {})


def _omit() -> set[str]:
    return {fold_ncaam_alias(a) for a in (_load_doc().get("omit_aliases") or [])}


def _ratings_bridge() -> Dict[str, str]:
    return dict(_load_doc().get("ratings_norm_bridge") or {})


def resolve_team_id(alias: str, source: str = "unknown") -> Optional[str]:
    """Return canonical team_id or None (omit). Fail-closed."""
    del source  # reserved for logging / future source-lock
    folded = fold_ncaam_alias(alias)
    if not folded:
        return None
    if folded in _omit():
        return None
    return _aliases().get(folded)


def to_ratings_norm(team_id: str) -> str:
    """Map clean team_id → ratings parquet team_norm when inherited grain differs."""
    return _ratings_bridge().get(team_id, team_id)


def resolve_ratings_norm(alias: str, source: str = "unknown") -> Optional[str]:
    tid = resolve_team_id(alias, source=source)
    if tid is None:
        return None
    return to_ratings_norm(tid)


def is_retired_ncaam_sport_key(key: Optional[str]) -> bool:
    return str(key or "").strip().lower() in RETIRED_NCAAM_SPORT_KEYS


def odds_name_to_team_norm(full: str) -> Optional[str]:
    """Publish-safe replacement for odds_team_to_short — fail-closed, no first-token shortening."""
    return resolve_ratings_norm(full, source="odds")


def map_odds_names_to_norm(names: list[str]) -> list[Optional[str]]:
    """Vector-friendly map for Polars / batch publish joins."""
    return [odds_name_to_team_norm(n) for n in names]