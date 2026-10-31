"""Canonical CFB QB feature contract (train/serve identity).

This module is the locked specification for the QB talent / class / supporting-
cast inputs production already serves. It does **not** change compose weights,
MATCHUP_RESPONSE, or any projection arithmetic.

#539 established that hist-cal fitted downstream knobs on
``unknown @ talent 50`` (placeholder missing-fill) while 2026 serve uses
prior-year counting-stat talent centered near 67. Recalibration is illegal
until train rows are stamped with the same contract version as serve.

Versions
--------
- ``cfb-qb-feature-v1`` — live packager heuristic
  (``scripts/cfb/package_real_roster_2026.py``). Legal for coefficient fit
  only after a historical dataset is built under this exact definition.
- ``cfb-qb-feature-placeholder-unknown-50`` — hist-cal proxy. Must not be
  used to re-estimate MATCHUP_RESPONSE / QB weights.

See ``data/ops/cfb-qb-calibration-protocol-20260911.md``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

QB_FEATURE_CONTRACT_VERSION = "cfb-qb-feature-v1"
QB_FEATURE_CONTRACT_PLACEHOLDER = "cfb-qb-feature-placeholder-unknown-50"

# Frozen serve formula (packager SoT as of 2026-09-11). Do not "fix" location.
TALENT_BASE = 42.0
TALENT_ATTEMPT_CAP = 22.0
TALENT_ATTEMPT_DIV = 22.0
TALENT_YPA_CAP = 12.0
TALENT_YPA_SCALE = 1.1
TALENT_TD_CAP = 10.0
TALENT_TD_SCALE = 0.35
TALENT_PORTAL_BUMP = 2.0
TALENT_FLOOR = 35.0
TALENT_CAP = 96.0
ZERO_ATT_DEFAULT = 48.0
ZERO_ATT_PORTAL_DEFAULT = 52.0
LOWSAMPLE_ATTEMPTS = 80
MISSING_QB_TALENT = 50.0
MISSING_QB_CLASS = "unknown"
# 2026 packaged recruiting floor when a class score is absent at *package* time.
# Historical rows must not silently inherit this as year-Y recruiting.
RECRUITING_PACKAGED_FLOOR_2026 = 55.0

LEGAL_FOR_COEFFICIENT_FIT = frozenset({QB_FEATURE_CONTRACT_VERSION})

REQUIRED_QB_FIELDS = (
    "qb_class",
    "qb_talent",
    "ol_support",
    "weapons_support",
    "starter_name",
    "starter_key",
    "is_portal",
    "prior_season",
    "pass_attempts_prior",
    "pass_yards_prior",
    "pass_td_prior",
    "qb_feature_contract_version",
    "availability",
)

# ESPN site roster without a season lock returns the current club (2026).
FORBIDDEN_ROSTER_SOURCES = frozenset(
    {
        "espn_site_v2_roster_unscoped",
        "espn_site_roster_current",
        "espn_web_roster_query_season_ignored",
    }
)
LEGAL_ROSTER_SOURCES = frozenset(
    {
        "espn_core_seasons_Y_team_athletes",
        "packaged_espn_roster_2026",
    }
)

AVAILABILITY_CLASSES = frozenset(
    {"EXACT", "RECONSTRUCTABLE", "PROXY", "MISSING"}
)


class FeatureContractError(ValueError):
    """Train/serve contract violation — fail closed, do not proxy."""


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def talent_from_qb_stats(
    attempts: int, yards: int, tds: int, *, is_portal: bool
) -> float:
    """v1 counting-stat talent. No completion-rate term."""
    if int(attempts) <= 0:
        return ZERO_ATT_PORTAL_DEFAULT if is_portal else ZERO_ATT_DEFAULT
    ypa = float(yards) / max(int(attempts), 1)
    base = (
        TALENT_BASE
        + min(TALENT_ATTEMPT_CAP, float(attempts) / TALENT_ATTEMPT_DIV)
        + min(TALENT_YPA_CAP, ypa * TALENT_YPA_SCALE)
        + min(TALENT_TD_CAP, float(tds) * TALENT_TD_SCALE)
    )
    if is_portal:
        base += TALENT_PORTAL_BUMP
    return _clamp(base, TALENT_FLOOR, TALENT_CAP)


def resolve_qb_talent(
    attempts: int,
    yards: int,
    tds: int,
    *,
    is_portal: bool,
    recruiting_class_score: Optional[float],
    recruiting_availability: str = "EXACT",
) -> Tuple[float, str]:
    """Stats talent, blended to *year-legal* recruiting when attempts are thin.

    Returns ``(talent, availability)``. If attempts < N and recruiting is not
    EXACT/RECONSTRUCTABLE, talent is not silently filled with the 2026 floor.
    """
    stats = talent_from_qb_stats(
        int(attempts), int(yards), int(tds), is_portal=bool(is_portal)
    )
    att = int(attempts or 0)
    if att >= LOWSAMPLE_ATTEMPTS:
        return stats, "EXACT"
    avail = str(recruiting_availability or "MISSING").upper()
    if avail not in AVAILABILITY_CLASSES:
        raise FeatureContractError(f"bad recruiting availability: {avail}")
    if recruiting_class_score is None or avail in {"MISSING", "PROXY"}:
        if att <= 0:
            return (
                ZERO_ATT_PORTAL_DEFAULT if is_portal else ZERO_ATT_DEFAULT
            ), "MISSING"
        return stats, "MISSING"
    fallback = _clamp(float(recruiting_class_score))
    w = math.sqrt(att / float(LOWSAMPLE_ATTEMPTS)) if att > 0 else 0.0
    return _clamp((1.0 - w) * fallback + w * stats), avail


def classify_qb(
    *,
    experience_abbr: str,
    experience_years: int,
    pass_attempts_prior: int,
    is_portal: bool,
    qb_room_size: int,
    competing_with_attempts: int,
) -> Tuple[str, int, str]:
    """Return (qb_class, experience_starts_proxy, notes). Same rules as serve."""
    starts_proxy = max(0, int(round(int(pass_attempts_prior) / 30.0)))
    if experience_abbr == "FR" and experience_years <= 1 and pass_attempts_prior < 15:
        return "true_freshman", 0, "true freshman / no meaningful prior-season attempts"
    if is_portal and pass_attempts_prior >= 50:
        return "portal", starts_proxy, "portal addition with prior production"
    if is_portal and pass_attempts_prior < 50 and experience_years >= 2:
        if competing_with_attempts >= 80 or qb_room_size >= 4:
            return "open_competition", starts_proxy, "portal body in unsettled room"
        return "portal", starts_proxy, "portal addition"
    if pass_attempts_prior >= 120:
        return "incumbent", max(starts_proxy, 4), "returning production starter"
    if competing_with_attempts >= 40 and pass_attempts_prior < 120:
        return "open_competition", starts_proxy, "split / unsettled QB room"
    if experience_years >= 2 and pass_attempts_prior >= 20:
        return "incumbent", starts_proxy, "returning depth with some prior-season work"
    if experience_abbr == "FR":
        return "true_freshman", 0, "freshman listed without prior attempts"
    return "open_competition", starts_proxy, "insufficient starter signal"


def depth_sort_key(row: Mapping[str, Any]) -> Tuple[float, float, str]:
    """QB1 = max prior-season attempts, then experience years, then name."""
    att = float(row.get("pass_attempts_prior") or row.get("pass_attempts_2025") or 0)
    years = float(row.get("experience_years") or 0)
    return (-att, -years, str(row.get("player_name") or ""))


def prior_season_for_prediction(prediction_season: int) -> int:
    """Week-0 / early-season freeze: full prior-season counting stats only."""
    return int(prediction_season) - 1


def assert_roster_source_legal(source: str) -> None:
    src = str(source or "")
    if src in FORBIDDEN_ROSTER_SOURCES:
        raise FeatureContractError(
            f"roster source {src!r} leaks current-club membership"
        )


def assert_counting_stats_season_legal(
    *,
    stats_season: int,
    prediction_season: int,
    week: int,
    allow_in_season_update: bool = False,
) -> None:
    """Reject same-season (or future) counting stats as Week-N talent inputs.

    Production 2026 W1/W2 still freeze prior-year totals. Until an explicit
    in-season talent updater is approved, ``stats_season`` must equal
    ``prediction_season - 1`` for every week.
    """
    pred = int(prediction_season)
    stats = int(stats_season)
    wk = int(week)
    if stats > pred:
        raise FeatureContractError(
            f"counting stats season {stats} is after prediction season {pred}"
        )
    if stats == pred and not allow_in_season_update:
        raise FeatureContractError(
            f"same-season {stats} counting stats are leakage for week {wk} "
            "under the frozen v1 contract"
        )
    if stats != pred - 1 and not allow_in_season_update:
        raise FeatureContractError(
            f"v1 freeze requires stats_season={pred - 1}, got {stats}"
        )


def assert_experience_not_current_leaked(
    *,
    experience_source: str,
) -> None:
    """ESPN core season-Y athlete.experience is the *current* class year."""
    src = str(experience_source or "")
    if src in {
        "espn_core_athlete_experience_unadjusted",
        "espn_athlete_experience_current",
    }:
        raise FeatureContractError(
            "ESPN athlete.experience is current-class, not year-locked; "
            "reconstruct via first-appearance / roster-year join"
        )


def assert_legal_for_coefficient_fit(version: str) -> None:
    v = str(version or "")
    if v not in LEGAL_FOR_COEFFICIENT_FIT:
        raise FeatureContractError(
            f"refusing coefficient fit on qb feature contract {v!r}; "
            f"legal versions: {sorted(LEGAL_FOR_COEFFICIENT_FIT)}"
        )


def assert_v1_schema(row: Mapping[str, Any]) -> None:
    missing = [k for k in REQUIRED_QB_FIELDS if k not in row]
    if missing:
        raise FeatureContractError(f"v1 schema missing fields: {missing}")
    avail = row.get("availability") or {}
    if isinstance(avail, str):
        if avail not in AVAILABILITY_CLASSES:
            raise FeatureContractError(f"bad availability class {avail!r}")
        return
    if not isinstance(avail, Mapping):
        raise FeatureContractError("availability must be a class or per-field map")
    for key, val in avail.items():
        if str(val).upper() not in AVAILABILITY_CLASSES:
            raise FeatureContractError(f"bad availability for {key}: {val!r}")
        if str(val).upper() == "PROXY":
            raise FeatureContractError(
                f"silent proxy forbidden for {key}; label MISSING or rebuild"
            )


def talent_location_summary(talents: Sequence[float]) -> Dict[str, float]:
    xs = [float(x) for x in talents]
    if not xs:
        raise FeatureContractError("empty talent vector")
    xs_sorted = sorted(xs)
    n = len(xs_sorted)
    mean = sum(xs_sorted) / n
    var = sum((x - mean) ** 2 for x in xs_sorted) / n
    sd = math.sqrt(var)
    p50 = xs_sorted[n // 2]
    return {
        "n": float(n),
        "mean": round(mean, 4),
        "sd": round(sd, 4),
        "p50": round(p50, 4),
        "min": round(xs_sorted[0], 4),
        "max": round(xs_sorted[-1], 4),
    }


def assert_v1_talent_location(
    talents: Sequence[float],
    *,
    established: bool = False,
) -> Dict[str, float]:
    """Reject the hist-cal missing-fill distribution labeled as v1."""
    summary = talent_location_summary(talents)
    mean = summary["mean"]
    sd = summary["sd"]
    n = summary["n"]
    if n >= 20 and sd < 1.5 and 48.0 <= mean <= 52.0:
        raise FeatureContractError(
            f"v1 talent location looks like missing-fill (mean={mean}, sd={sd})"
        )
    if established and n >= 20:
        if not (60.0 <= mean <= 78.0):
            raise FeatureContractError(
                f"established v1 talent mean {mean} outside [60, 78]"
            )
        if not (4.0 <= sd <= 16.0):
            raise FeatureContractError(
                f"established v1 talent sd {sd} outside [4, 16]"
            )
    return summary


def assert_placeholder_location(talents: Sequence[float]) -> Dict[str, float]:
    """Hist-cal fill must stay labeled placeholder — all ~50."""
    summary = talent_location_summary(talents)
    if summary["n"] >= 10 and not (
        49.0 <= summary["mean"] <= 51.0 and summary["sd"] < 0.5
    ):
        raise FeatureContractError(
            "placeholder contract expected unknown@50; got "
            f"mean={summary['mean']} sd={summary['sd']}"
        )
    return summary


def contract_version_for_notes(notes: Optional[Mapping[str, Any]]) -> str:
    if not notes:
        return ""
    return str(notes.get("qb_feature_contract_version") or "")


def documentation() -> Dict[str, Any]:
    return {
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "placeholder_version": QB_FEATURE_CONTRACT_PLACEHOLDER,
        "legal_for_coefficient_fit": sorted(LEGAL_FOR_COEFFICIENT_FIT),
        "ops": "data/ops/cfb-qb-calibration-protocol-20260911.md",
        "formula": {
            "zero_attempts": (
                f"{ZERO_ATT_DEFAULT} (or {ZERO_ATT_PORTAL_DEFAULT} if portal)"
            ),
            "stats": (
                f"clamp({TALENT_BASE} + min({TALENT_ATTEMPT_CAP}, att/"
                f"{TALENT_ATTEMPT_DIV}) + min({TALENT_YPA_CAP}, ypa*"
                f"{TALENT_YPA_SCALE}) + min({TALENT_TD_CAP}, td*"
                f"{TALENT_TD_SCALE}) + {TALENT_PORTAL_BUMP}*portal, "
                f"{TALENT_FLOOR}, {TALENT_CAP})"
            ),
            "lowsample": (
                f"if att<{LOWSAMPLE_ATTEMPTS}: sqrt(att/{LOWSAMPLE_ATTEMPTS})"
                "*stats + (1-w)*year_legal_recruiting"
            ),
            "completion_rate_term": False,
            "starter_rule": "max prior-season attempts, then experience years, then name",
            "temporal": "prior_season = prediction_season - 1; no same-season stats",
        },
        "missing_semantics": {
            "no_qb_on_roster": {
                "qb_talent": MISSING_QB_TALENT,
                "qb_class": MISSING_QB_CLASS,
            },
            "zero_attempts": {
                "non_portal": ZERO_ATT_DEFAULT,
                "portal": ZERO_ATT_PORTAL_DEFAULT,
            },
            "lowsample_without_legal_recruiting": "MISSING — do not inherit 2026 floor 55",
            "espn_experience_current": "not year-locked; reconstruct first-appearance",
        },
        "does_not": [
            "change MATCHUP_RESPONSE / QB compose weights",
            "ship median-to-50 location transforms",
            "unseal 2025 residuals",
            "fit 2026 W1/W2",
            "enable PLAY or public CFB",
        ],
    }


def attach_contract_version(
    notes: Mapping[str, Any],
    version: str,
) -> Dict[str, Any]:
    out = dict(notes)
    out["qb_feature_contract_version"] = str(version)
    return out


def iter_universe_qb_talent(universe: Any) -> Iterable[float]:
    teams = getattr(universe, "teams", {}) or {}
    for state in teams.values():
        qb = getattr(state, "qb", None)
        if qb is None:
            continue
        yield float(getattr(qb, "qb_talent", MISSING_QB_TALENT))
