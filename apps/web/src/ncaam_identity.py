"""NCAAM team identity — fail-closed alias resolution (Python twin of lib/ncaam/identity.ts).

Canonical sport key: ncaam only (cbb retired as API/DB sport key).
Canonical team_id: clean KenPom-style team_norm (miami fl / miami oh).

P0: bare "miami" is OMIT — Miami FL ≠ Miami OH must never collapse.
Peer homonyms: bare "loyola" / "southern" also OMIT (aliases.json omit_aliases).
No fuzzy auto-publish joins; unknown / ambiguous → None.
Alias SoT: apps/web/lib/ncaam/aliases.json (shared with TS identity).

Phase 2.6B: odds_name_to_team_norm may apply deterministic expansions only
(hyphen→space, St→State, trailing-mascot strip, univ→university). Never fuzzy.
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

# Campus location tokens that may appear after a school stem in odds strings.
_CAMPUS_LOC_TOKENS = frozenset(
    {
        "mn",
        "pa",
        "ny",
        "oh",
        "fl",
        "ca",
        "tx",
        "il",
        "in",
        "mi",
        "nc",
        "sc",
        "va",
        "md",
        "ga",
        "al",
        "ms",
        "la",
        "ar",
        "mo",
        "ks",
        "ok",
        "co",
        "az",
        "wa",
        "or",
        "ky",
        "tn",
        "wi",
        "ia",
        "ne",
        "sd",
        "nd",
        "mt",
        "id",
        "ut",
        "nm",
        "nv",
        "wy",
        "hi",
        "ak",
        "ct",
        "ma",
        "ri",
        "nh",
        "vt",
        "me",
        "nj",
        "de",
        "wv",
        "dc",
    }
)


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


def _expand_st_abbreviation(folded: str) -> str:
    """Deterministic St → State token expansion (not fuzzy).

    Examples: 'washington st cougars' → 'washington state cougars';
              'san diego st' → 'san diego state'.
    Does not touch leading saint prefixes (st thomas, st johns, etc.).
    """
    parts = folded.split()
    out: list[str] = []
    for i, p in enumerate(parts):
        if p == "st" and i > 0 and parts[i - 1] not in {"st", "saint"}:
            out.append("state")
        else:
            out.append(p)
    return " ".join(out)


def _normalize_odds_fold(folded: str) -> str:
    """Deterministic odds-string normalizations before alias lookup."""
    s = folded.replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split()
    out: list[str] = []
    for p in parts:
        if p in {"univ", "u"} and out:
            # 'boston univ' → 'boston university'; lone 'u' after school stem only when prior is alpha school token
            if p == "univ":
                out.append("university")
            else:
                out.append(p)
        else:
            out.append(p)
    return " ".join(out)


def _lookup_folded(folded: str) -> Optional[str]:
    if not folded or folded in _omit():
        return None
    tid = _aliases().get(folded)
    if tid is None:
        return None
    return to_ratings_norm(tid)


def odds_name_to_team_norm(full: str) -> Optional[str]:
    """Publish-safe odds-name resolver — fail-closed, deterministic expansions only.

    Resolution order:
      1) exact folded alias
      2) hyphen→space + univ→university normalization
      3) St→State abbreviation expansion
      4) strip final mascot token, then retry 1–3
      5) if stem ends with a 2-letter campus locator, strip it and retry

    Never uses fuzzy/edit-distance matching. Bare homonyms stay omit-listed.
    Never collapses Texas A&M-Commerce → Texas A&M (requires explicit commerce alias).
    """
    folded0 = fold_ncaam_alias(full)
    if not folded0:
        return None

    bases = []
    for b in (folded0, _normalize_odds_fold(folded0)):
        if b and b not in bases:
            bases.append(b)

    candidates: list[str] = []
    for base in bases:
        for cand in (base, _expand_st_abbreviation(base)):
            if cand and cand not in candidates:
                candidates.append(cand)
        parts = base.split()
        if len(parts) >= 2:
            stem = " ".join(parts[:-1])
            for cand in (stem, _expand_st_abbreviation(stem)):
                if cand and cand not in candidates:
                    candidates.append(cand)
            # campus locator: 'st thomas mn' / 'st francis pa'
            stem_parts = stem.split()
            if len(stem_parts) >= 2 and stem_parts[-1] in _CAMPUS_LOC_TOKENS:
                stem2 = " ".join(stem_parts[:-1])
                for cand in (stem2, _expand_st_abbreviation(stem2)):
                    if cand and cand not in candidates:
                        candidates.append(cand)

    for cand in candidates:
        hit = _lookup_folded(cand)
        if hit:
            return hit
    return None


def map_odds_names_to_norm(names: list[str]) -> list[Optional[str]]:
    """Vector-friendly map for Polars / batch publish joins."""
    return [odds_name_to_team_norm(n) for n in names]
