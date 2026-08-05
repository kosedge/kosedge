"""Variable home-field advantage (CFB) — bucketed, inspectable, not flat 3 pts.

Design (bettor-facing, honest fidelity):
- Baseline ~1.7 points (FBS-ish; trimmed in v0.8.1 hist-cal; not NFL's ~1 pt).
- Team buckets from recent home performance proxy / packaged venue prior:
  elite / strong / average / weak / poor.
- Night games and major environments are noted; night gets a small optional
  bump when flagged. Major-environment identity is mostly captured by bucket.
- Neutral sites get 0 HFA.

This layer feeds ``expected_team_points`` (project-game + season sim).
Packaged numerics are APPROXIMATE until live home-split feeds exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import DataFidelity, HomeFieldProfile

# Bucket → points. Baseline sits at "average".
# v0.8.1 hist-cal: trimmed ~0.3 pts after home-dog overrate vs 2023–24 closes.
BUCKET_POINTS: Dict[str, float] = {
    "elite": 3.10,
    "strong": 2.45,
    "average": 1.70,
    "weak": 1.05,
    "poor": 0.55,
}

BUCKET_ORDER = ("poor", "weak", "average", "strong", "elite")

# Score thresholds for env_score (0–100) → bucket.
SCORE_BUCKETS = (
    (80.0, "elite"),
    (65.0, "strong"),
    (45.0, "average"),
    (30.0, "weak"),
    (0.0, "poor"),
)

NIGHT_GAME_BUMP = 0.30  # modest; not a full venue model
MAJOR_ENV_NOTE_BUMP = 0.0  # identity already in elite/strong; note-only for now

# Curated venue / recent-home proxies (approximate). Used when payload omits
# home_field — keeps famous environments distinct without inventing precision.
CURATED_HOME_ENV: Dict[str, Dict[str, Any]] = {
    "LSU": {"env_score": 92, "bucket": "elite", "major_environment": True, "venue": "Tiger Stadium"},
    "ORE": {"env_score": 90, "bucket": "elite", "major_environment": True, "venue": "Autzen Stadium"},
    "PSU": {"env_score": 88, "bucket": "elite", "major_environment": True, "venue": "Beaver Stadium"},
    "CLEM": {"env_score": 87, "bucket": "elite", "major_environment": True, "venue": "Memorial Stadium"},
    "UF": {"env_score": 86, "bucket": "elite", "major_environment": True, "venue": "Ben Hill Griffin"},
    "TENN": {"env_score": 85, "bucket": "elite", "major_environment": True, "venue": "Neyland Stadium"},
    "WIS": {"env_score": 84, "bucket": "elite", "major_environment": True, "venue": "Camp Randall"},
    "OU": {"env_score": 83, "bucket": "elite", "major_environment": True, "venue": "Gaylord Family"},
    "AUB": {"env_score": 82, "bucket": "elite", "major_environment": True, "venue": "Jordan-Hare"},
    "UGA": {"env_score": 81, "bucket": "elite", "major_environment": True, "venue": "Sanford Stadium"},
    "OSU": {"env_score": 80, "bucket": "elite", "major_environment": True, "venue": "Ohio Stadium"},
    "ND": {"env_score": 78, "bucket": "strong", "major_environment": True, "venue": "Notre Dame Stadium"},
    "ALA": {"env_score": 77, "bucket": "strong", "major_environment": True, "venue": "Bryant-Denny"},
    "TEX": {"env_score": 74, "bucket": "strong", "major_environment": False, "venue": "DKR"},
    "MICH": {"env_score": 76, "bucket": "strong", "major_environment": True, "venue": "Michigan Stadium"},
    "USC": {"env_score": 62, "bucket": "average", "major_environment": False, "venue": "LA Coliseum"},
    "COLO": {"env_score": 68, "bucket": "strong", "major_environment": False, "venue": "Folsom Field"},
    "FSU": {"env_score": 70, "bucket": "strong", "major_environment": False, "venue": "Doak Campbell"},
    "MIA": {"env_score": 58, "bucket": "average", "major_environment": False, "venue": "Hard Rock"},
    "BALL": {"env_score": 28, "bucket": "poor", "major_environment": False, "venue": ""},
    "EMU": {"env_score": 26, "bucket": "poor", "major_environment": False, "venue": ""},
    "NMSU": {"env_score": 32, "bucket": "weak", "major_environment": False, "venue": ""},
    "WAKE": {"env_score": 40, "bucket": "weak", "major_environment": False, "venue": ""},
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def bucket_from_score(env_score: float) -> str:
    score = _clamp(env_score, 0.0, 100.0)
    for threshold, bucket in SCORE_BUCKETS:
        if score >= threshold:
            return bucket
    return "poor"


def points_for_bucket(bucket: str) -> float:
    return float(BUCKET_POINTS.get(str(bucket).lower(), BUCKET_POINTS["average"]))


def proxy_env_score_from_roster(payload: Optional[Mapping[str, Any]]) -> float:
    """Soft proxy when no home_field prior: recruiting + experience → venue draw.

    Labeled approximate — not a measured home ATS / scoring-margin split.
    """
    if not payload:
        return 50.0
    roster = payload.get("roster") or {}
    recruiting = float(
        roster.get("recruiting_class_score", roster.get("recruiting_capital", 50.0))
    )
    experience = float(roster.get("experience_index", 50.0))
    # Mild pull toward average so placeholders do not all become "strong".
    return _clamp(0.55 * recruiting + 0.25 * experience + 0.20 * 50.0, 20.0, 78.0)


def build_home_field_profile(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    team_payload: Optional[Mapping[str, Any]] = None,
) -> HomeFieldProfile:
    """Build inspectable HFA profile for ``team``.

    Precedence: explicit ``home_field`` payload → curated venue map → roster proxy.
    """
    team = str(team).upper()
    raw = dict(payload or {})
    fidelity: DataFidelity = "approximate"
    source = "packaged_prior"
    notes_parts: list[str] = []

    if raw:
        env_score = float(raw.get("env_score", raw.get("home_env_score", 50.0)))
        bucket = str(raw.get("bucket") or bucket_from_score(env_score)).lower()
        if bucket not in BUCKET_POINTS:
            bucket = bucket_from_score(env_score)
        major = bool(raw.get("major_environment", False))
        venue = str(raw.get("venue") or "")
        night_default = bool(raw.get("night_game_default", False))
        source = str(raw.get("source") or "packaged_prior")
        fidelity = str(raw.get("fidelity") or "approximate")  # type: ignore[assignment]
        if fidelity not in ("real", "approximate", "placeholder"):
            fidelity = "approximate"
        if raw.get("notes"):
            notes_parts.append(str(raw["notes"]))
    elif team in CURATED_HOME_ENV:
        cur = CURATED_HOME_ENV[team]
        env_score = float(cur["env_score"])
        bucket = str(cur["bucket"])
        major = bool(cur.get("major_environment", False))
        venue = str(cur.get("venue") or "")
        night_default = False
        source = "curated_venue_proxy"
        fidelity = "approximate"
        notes_parts.append("curated venue / recent-home proxy")
    else:
        env_score = proxy_env_score_from_roster(team_payload)
        bucket = bucket_from_score(env_score)
        major = False
        venue = ""
        night_default = False
        source = "roster_proxy"
        fidelity = "placeholder" if env_score == 50.0 else "approximate"
        notes_parts.append("derived from recruiting/experience proxy")

    # Keep bucket/score coherent if caller set one but not the other.
    if "bucket" in raw and "env_score" not in raw and "home_env_score" not in raw:
        # Snap score to bucket midpoints for inspectability.
        mid = {"elite": 88, "strong": 72, "average": 52, "weak": 36, "poor": 22}
        env_score = float(mid.get(bucket, 50))

    baseline = float(P.HFA_BASELINE_POINTS)
    bucket_points = points_for_bucket(bucket)
    bucket_delta = round(bucket_points - baseline, 3)
    notes_parts.append(f"bucket={bucket} pts={bucket_points:.2f} (baseline={baseline:.2f})")
    if major:
        notes_parts.append("major_environment")

    return HomeFieldProfile(
        team=team,
        env_score=round(env_score, 2),
        bucket=bucket,  # type: ignore[arg-type]
        hfa_points=round(bucket_points, 3),
        baseline_points=baseline,
        bucket_delta=bucket_delta,
        major_environment=major,
        venue=venue,
        night_game_default=night_default,
        source=source,
        fidelity=fidelity,  # type: ignore[arg-type]
        notes="; ".join(notes_parts),
    )


def resolve_hfa_points(
    profile: Optional[HomeFieldProfile],
    *,
    home: bool,
    neutral_site: bool = False,
    night_game: bool = False,
) -> Dict[str, Any]:
    """Game-level HFA resolution with inspectable components."""
    if neutral_site or not home:
        return {
            "hfa_points": 0.0,
            "baseline": float(P.HFA_BASELINE_POINTS),
            "bucket": None if profile is None else profile.bucket,
            "bucket_points": None if profile is None else profile.hfa_points,
            "bucket_delta": None if profile is None else profile.bucket_delta,
            "night_bump": 0.0,
            "major_environment": bool(profile.major_environment) if profile else False,
            "applied": False,
            "reason": "neutral_site" if neutral_site else "away_side",
            "fidelity": profile.fidelity if profile else "approximate",
        }

    if profile is None:
        pts = float(P.HFA_BASELINE_POINTS)
        return {
            "hfa_points": pts,
            "baseline": pts,
            "bucket": "average",
            "bucket_points": pts,
            "bucket_delta": 0.0,
            "night_bump": 0.0,
            "major_environment": False,
            "applied": True,
            "reason": "missing_profile_baseline",
            "fidelity": "placeholder",
        }

    night_bump = float(NIGHT_GAME_BUMP) if night_game else 0.0
    # Major env currently note-only (bucket already elevated); keep bump at 0.
    major_bump = float(MAJOR_ENV_NOTE_BUMP) if profile.major_environment else 0.0
    total = _clamp(profile.hfa_points + night_bump + major_bump, 0.0, 4.5)
    return {
        "hfa_points": round(total, 3),
        "baseline": profile.baseline_points,
        "bucket": profile.bucket,
        "bucket_points": profile.hfa_points,
        "bucket_delta": profile.bucket_delta,
        "night_bump": round(night_bump, 3),
        "major_environment": profile.major_environment,
        "venue": profile.venue,
        "env_score": profile.env_score,
        "applied": True,
        "reason": "variable_hfa",
        "fidelity": profile.fidelity,
        "source": profile.source,
    }


def profile_to_dict(profile: Optional[HomeFieldProfile]) -> Optional[Dict[str, Any]]:
    if profile is None:
        return None
    return {
        "team": profile.team,
        "env_score": profile.env_score,
        "bucket": profile.bucket,
        "hfa_points": profile.hfa_points,
        "baseline_points": profile.baseline_points,
        "bucket_delta": profile.bucket_delta,
        "major_environment": profile.major_environment,
        "venue": profile.venue,
        "night_game_default": profile.night_game_default,
        "source": profile.source,
        "fidelity": profile.fidelity,
        "notes": profile.notes,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": "home_field",
        "name": "home_field",
        "module": "src.services.cfb_season_engine.home_field",
        "real_vs_approximate": (
            "Bucket structure + baseline/ deltas are REAL (inspectable). "
            "Team env_scores / venue labels are APPROXIMATE packaged proxies — "
            "not live home ATS or scoring-margin splits. Night bump is a thin "
            "optional note, not a full night-game model."
        ),
        "formula": (
            "hfa = bucket_points(+ night_bump) when home & not neutral; "
            f"baseline={P.HFA_BASELINE_POINTS}; buckets={BUCKET_POINTS}"
        ),
        "buckets": dict(BUCKET_POINTS),
        "baseline_points": P.HFA_BASELINE_POINTS,
        "night_game_bump": NIGHT_GAME_BUMP,
        "feeds": ["team_projection.expected_team_points", "season_sim.realize_game_scores"],
    }
