"""t4688u draft-only W8 forecast builders (CERT=0).

Corrected contracts from Codex 88a08cae / IMV RETURN 75141507.
Not imported by production emit, Celery, or routes. B HOLD — do not merge
as production CLEAR. Wires into run_w8_research_forecast_t4564u.py only
after Ryan CLEAR (that script is on #645, not this tip).

Does not import the paid Odds client or warehouse tables.
Does not open the 2025 prior pack.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Optional, Sequence

WEEK_CAP = 7
OFFICIAL_WEEK = 8
DESIGNATIONS = frozenset({"out", "doubtful", "questionable"})
PRIOR_2025_PACK_NAME = "nfl_team_efficiency_backbone_2026.json"
MISSING_STRENGTH = "MISSING current strength"
SHA_MISMATCH = "input_sha_mismatch"
G3_FLAGS = (
    "w8_official_injury_report",
    "injury_as_of_week8",
    "injury_as_of_week8_away",
)


class MissingCurrentStrength(SystemExit):
    """Builder refuse — no silent 2025 prior."""


class InputShaMismatch(SystemExit):
    """C3 pin refuse — no silent re-download."""


def _norm_status(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_designated(row: Dict[str, Any]) -> bool:
    return _norm_status(row.get("report_status")) in DESIGNATIONS


def require_input_sha(actual_sha256: str, expected_sha256: str, *, label: str) -> None:
    """T-C1-PIN-2 — one-byte drift must refuse."""
    got = str(actual_sha256 or "").strip().lower()
    exp = str(expected_sha256 or "").strip().lower()
    if got != exp or len(exp) != 64:
        raise InputShaMismatch(f"{SHA_MISMATCH}:{label}")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_current_strength(
    rows: Sequence[Dict[str, Any]],
    *,
    week_cap: int = WEEK_CAP,
    refuse_weeks_above_cap: bool = False,
    prior_pack_opened: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Play-weighted EPA by team with a hard week cutoff.

    T-EPA-ASOF-1/2/3. Does not read PRIOR_2025_PACK_NAME.
    `prior_pack_opened` is a probe list tests can pass; this function never appends.
    """
    del prior_pack_opened  # never touched — 2025 pack is not a fallback
    if not rows:
        raise MissingCurrentStrength(MISSING_STRENGTH)

    above = [r for r in rows if int(r["week"]) > int(week_cap)]
    if above and refuse_weeks_above_cap:
        raise MissingCurrentStrength(f"{MISSING_STRENGTH}: week>{week_cap} present")

    capped = [r for r in rows if int(r["week"]) <= int(week_cap)]
    if not capped or max(int(r["week"]) for r in capped) < int(week_cap):
        raise MissingCurrentStrength(MISSING_STRENGTH)

    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for rec in capped:
        team = str(rec["team"])
        by_team.setdefault(team, []).append(dict(rec))

    out: Dict[str, Dict[str, Any]] = {}
    for team, recs in by_team.items():
        recs = sorted(recs, key=lambda r: int(r["week"]))
        off_plays = sum(float(r.get("off_plays") or 0) for r in recs)
        off_epa = sum(float(r.get("off_epa") or 0) for r in recs)
        if off_plays <= 0:
            continue
        weeks = [int(r["week"]) for r in recs]
        out[team] = {
            "off_epa_per_play": round(off_epa / off_plays, 6),
            "games": len(recs),
            "weeks": weeks,
            "off_plays": int(off_plays),
            "source": f"team_week_w1_w{week_cap}_play_weighted",
            "epa_grain": f"season_to_date_w1_w{week_cap}",
            "week_cap": int(week_cap),
            "excluded_weeks_above_cap": sorted({int(r["week"]) for r in above}),
        }
    if not out:
        raise MissingCurrentStrength(MISSING_STRENGTH)
    return out


def last_designated_week(rows_for_team: Iterable[Dict[str, Any]]) -> Optional[int]:
    """Corrected rule: last week WITH designations. Not max(week) on empty stubs."""
    designated = [int(r["week"]) for r in rows_for_team if _is_designated(r)]
    if not designated:
        return None
    return max(designated)


def legacy_as_of_week_max_including_empty(rows_for_team: Sequence[Dict[str, Any]]) -> Optional[int]:
    """#645 defect (:325) — protection-removed mutation. Do not call from emit."""
    designated = last_designated_week(rows_for_team)
    if designated is not None:
        return designated
    weeks = [int(r["week"]) for r in rows_for_team]
    return max(weeks) if weeks else None


def legacy_pack_official_from_latest_week(latest_week: int, *, official_week: int = OFFICIAL_WEEK) -> str:
    """#645 defect (:691) — PRESENT if latest_week >= 8. Protection-removed mutation."""
    return "PRESENT" if int(latest_week) >= int(official_week) else "MISSING"


def injury_pack_official_flag(
    *,
    official_sot_pin: Optional[str] = None,
) -> str:
    """PRESENT only from a separately pinned official-W8 SoT (none today)."""
    if official_sot_pin:
        return "PRESENT"
    return "MISSING"


def g3_missing_flags(*, official_sot_pin: Optional[str] = None) -> List[str]:
    """Official book missing → keep all G3 flags (do not drop when as_of==8)."""
    if official_sot_pin:
        return []
    return list(G3_FLAGS)


def injury_impacts(
    rows: Sequence[Dict[str, Any]],
    *,
    official_week: int = OFFICIAL_WEEK,
    official_sot_pin: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Per-team overlay + honest official flag. Calls the writer (not a pre-set dict)."""
    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for rec in rows:
        by_team.setdefault(str(rec["team"]), []).append(dict(rec))

    official = injury_pack_official_flag(official_sot_pin=official_sot_pin)
    flags = g3_missing_flags(official_sot_pin=official_sot_pin)
    out: Dict[str, Dict[str, Any]] = {}
    for team, team_rows in by_team.items():
        as_of = last_designated_week(team_rows)
        designated = [r for r in team_rows if _is_designated(r) and int(r["week"]) == as_of]
        out[team] = {
            "as_of_week": as_of,
            "designated_count": len(designated),
            "w8_official_report": official,
            "missing_flags": list(flags),
            "official_week": int(official_week),
            "source": "nflverse_injuries_designated_only",
        }
    return out


def materialize_injury_pack_meta(
    rows: Sequence[Dict[str, Any]],
    *,
    official_week: int = OFFICIAL_WEEK,
    official_sot_pin: Optional[str] = None,
) -> Dict[str, Any]:
    """Pack writer fragment — never mints PRESENT from latest_week >= 8."""
    designated_weeks = [int(r["week"]) for r in rows if _is_designated(r)]
    latest = max(designated_weeks) if designated_weeks else None
    return {
        "week": latest,
        "w8_official_report": injury_pack_official_flag(official_sot_pin=official_sot_pin),
        "missing_flags": g3_missing_flags(official_sot_pin=official_sot_pin),
        "official_week": int(official_week),
        "designated_count": len(designated_weeks),
    }


def completeness_official_from_pack(pack: Dict[str, Any]) -> str:
    """Completeness must not say PRESENT just because pack week==8."""
    return injury_pack_official_flag(official_sot_pin=pack.get("official_sot_pin"))


def forbidden_odds_tokens() -> tuple[str, ...]:
    return ("odds_api", "the-odds-api", "ODDS_API_KEY", "theoddsapi", "pull_odds_snapshot")


def module_text_forbids_odds(text: str) -> None:
    """Non-vacuous Odds lock — import/call forms, not `\"False\" in text`."""
    import re

    for token in forbidden_odds_tokens():
        pattern = rf"(?:import\s+{re.escape(token)}|from\s+{re.escape(token)}|{re.escape(token)}\s*\()"
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise AssertionError(f"odds import/call present: {token}")
