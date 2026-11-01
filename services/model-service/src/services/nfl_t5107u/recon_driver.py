"""t5111u 2020–23 reconstruction driver.

Imports hash-verified helpers from vendor/build_recon_t4893u.py @ 7e77c57f.
Adapts season / path / identity plumbing only. Does not rewrite T1/T2/T5/rest
formulas. Never calls helper.main or load_oos_2016_2017. Never opens 1ee90fac.

Labels: RECONSTRUCTED / RETRO_FIT / RESEARCH_CONSUMED_RETRO. CERT=0.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence

from .inputs import (
    GAMES_SHA256,
    OUTCOMES_SHA256,
    PERMITTED_SEASONS,
    SEALED_SEASONS,
)
from .recon_contract import CONTRACT_27, _finite, compare_cell_maps

HELPER_SHA256 = "7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64"
HELPER_TIP = "43b5a62233b3d1d03ad2b25f5ec7dc52be29b31b"
CONTRACT_SHA256 = "b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4"
STAGE_B_FULL_SHA256 = "cd9af2858e21fac5247a489051f0cc61b9490cb97ffdec9ac41a31a2d224d810"
STAGE_B_W7W8_SLICE_SHA256 = (
    "3ab291d66a5b5da88daa073413635196e7361ffc9e1e2eafb35c652bedc7c441"
)
SCORES_2023_SHA256 = "253e178b72094f809264ff7a38b6792fbd99ffac092b26a00a8e8693416a63da"
LABEL_RECONSTRUCTED = "RECONSTRUCTED"
LABEL_RETRO_FIT = "RETRO_FIT"
LABEL_RESEARCH = "RESEARCH_CONSUMED_RETRO"

# 2017-era helper map sends LV→OAK. 2020–23 games.csv / outcomes use LV.
# Overlay is identity plumbing only (LA→LAR, WAS→WSH still required).
HELPER_PBP_TO_CANON_2017 = {"LA": "LAR", "WAS": "WSH", "LV": "OAK"}
ERA_2020_23_PBP_TO_CANON = {"LA": "LAR", "WAS": "WSH"}

FORBIDDEN_PATH_TOKENS = (
    "1ee90fac",
    "historical_oos_games.csv",
    "historical-oos",
)
FORBIDDEN_HELPER_ENTRYPOINTS = ("main", "load_oos_2016_2017")
PBP_COLS = (
    "game_id",
    "season",
    "week",
    "season_type",
    "posteam",
    "defteam",
    "play_type",
    "epa",
    "success",
    "sack",
    "qb_hit",
    "yardline_100",
    "touchdown",
    "down",
    "first_down",
    "home_team",
    "away_team",
)
GAMES_IDENTITY_COLS = ("season", "week", "game_id", "home", "away", "kickoff_utc")
_REPO_ROOT = Path(__file__).resolve().parents[5]
VENDOR_HELPER = (
    Path(__file__).resolve().parent / "vendor" / "build_recon_t4893u.py"
)
DEFAULT_GAMES_CANDIDATES = (
    Path("/tmp/t5111u-recon-43b5a622/pins/games_4fe1cdd7.csv"),
    _REPO_ROOT / "data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv",
)
DEFAULT_OUTCOMES_CANDIDATES = (
    Path("/tmp/t5111u-recon-43b5a622/pins/outcomes_2013_2022_score_only.csv"),
)
DEFAULT_SCORES_2023 = (
    _REPO_ROOT / "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2023.csv"
)
DEFAULT_STAGE_B = (
    _REPO_ROOT / "data/ops/nfl-forecast-builder-t5107u/recon/STAGE_B_W7W8_INPUT_REF.csv"
)
DEFAULT_PBP_ARCHIVE = Path("/Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01")
INCOMPATIBILITIES = (
    {
        "item": "PBP_TO_CANON['LV']='OAK'",
        "helper": "build_recon_t4893u.py:128",
        "status": "OVERLAID_IDENTITY_ONLY",
        "detail": (
            "2017-era helper remaps LV→OAK. 2020–23 games.csv 4fe1cdd7 and "
            "outcomes 50bda875 use LV (OAK count=0). Driver replaces "
            "mod.PBP_TO_CANON with {LA:LAR, WAS:WSH} so Raiders stay LV. "
            "LA→LAR and WAS→WSH transfer unchanged (PBP still emits LA/WAS)."
        ),
    },
    {
        "item": "T4 diffs not a helper export",
        "helper": "build_recon_t4893u.py:938-950 / rebuild_w7w17.py:712-740",
        "status": "APPLIED_UNCHANGED_FROM_HELPER_MAIN",
        "detail": (
            "t4_from_t2_sides applies helper.main T4 contract: "
            "diff_off=h-a, diff_def_allowed=a-h, diff_pg=h-a, diff_pa=a-h, "
            "diff_rz=h-a, diff_sr=mean((h_so-a_so),(a_sd-h_sd)). "
            "Not a new feature. Not loosened."
        ),
    },
    {
        "item": "helper.main / load_oos_2016_2017 / 1ee90fac",
        "helper": "build_recon_t4893u.py:229,522",
        "status": "REFUSED",
        "detail": "Old 2017 OOS reader and quarantined 1ee90fac are not opened.",
    },
    {
        "item": "outcomes 50bda875 season coverage",
        "helper": "stops 2022",
        "status": "PATH_PLUMBING",
        "detail": (
            "2020–22 T5 W-L from 50bda875. 2023 T5 from owned PBP score-only "
            "extract 253e178b (game_id join). Not a formula change."
        ),
    },
    {
        "item": "old b41f4b43 2017 row hashes vs 2020–23 rows",
        "helper": "expected",
        "status": "NEW_HASHES_BOUND",
        "detail": (
            "2017 artifact cannot share row hashes with newly generated "
            "2020–23 rows. Bind new reconstruction hashes + per-field provenance."
        ),
    },
)


class ReconRefuse(ValueError):
    """Fail-closed reconstruction."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fmt(value: float, digits: int = 8) -> str:
    return f"{float(value):.{digits}f}"


def refuse_forbidden_path(path: Path | str) -> None:
    text = str(path)
    lowered = text.lower()
    for token in FORBIDDEN_PATH_TOKENS:
        if token in lowered:
            raise ReconRefuse(
                f"refusing quarantined / old OOS path {path!s} (token={token})"
            )


def _refuse_old_entrypoints(*_args: object, **_kwargs: object) -> None:
    raise ReconRefuse(
        "refusing helper.main / load_oos_2016_2017 / 1ee90fac — "
        "t5111u driver imports T1/T2/T5/rest helpers only"
    )


def verify_helper_pin(path: Path | None = None) -> Path:
    helper = Path(path) if path is not None else VENDOR_HELPER
    refuse_forbidden_path(helper)
    if not helper.is_file():
        raise ReconRefuse(f"helper missing at {helper}")
    digest = sha256_file(helper)
    if digest != HELPER_SHA256:
        raise ReconRefuse(
            f"helper sha256 {digest} != pin {HELPER_SHA256} — STOP"
        )
    return helper


def load_verified_helper(path: Path | None = None) -> ModuleType:
    helper_path = verify_helper_pin(path)
    spec = importlib.util.spec_from_file_location(
        "w2_recon_t4893u_t5111u", helper_path
    )
    if spec is None or spec.loader is None:
        raise ReconRefuse(f"cannot load helper at {helper_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in FORBIDDEN_HELPER_ENTRYPOINTS:
        setattr(mod, name, _refuse_old_entrypoints)
    return mod


def apply_2020_23_identity(mod: ModuleType) -> dict[str, Any]:
    """Identity plumbing only. Do not rewrite T1/T2/T5/rest."""
    prior = dict(getattr(mod, "PBP_TO_CANON", {}))
    if prior == ERA_2020_23_PBP_TO_CANON:
        return {
            "prior": HELPER_PBP_TO_CANON_2017,
            "applied": dict(mod.PBP_TO_CANON),
            "already_applied": True,
            "reason": "2020-23 games.csv uses LV; helper LV→OAK cannot transfer",
        }
    if prior != HELPER_PBP_TO_CANON_2017:
        raise ReconRefuse(
            f"helper PBP_TO_CANON {prior} != 2017-era {HELPER_PBP_TO_CANON_2017} "
            "— do not guess a remap"
        )
    mod.PBP_TO_CANON = dict(ERA_2020_23_PBP_TO_CANON)
    return {
        "prior": prior,
        "applied": dict(mod.PBP_TO_CANON),
        "already_applied": False,
        "reason": "2020-23 games.csv uses LV; helper LV→OAK cannot transfer",
    }


def t4_from_t2_sides(
    home_row: Mapping[str, Any] | None,
    away_row: Mapping[str, Any] | None,
) -> dict[str, float | None]:
    """Apply helper.main T4 contract (build_recon_t4893u.py:921-950)."""

    def _side(row: Mapping[str, Any] | None) -> dict[str, float | None]:
        if row is None:
            return {k: None for k in ("off", "def", "pr", "so", "sd", "pg", "pa", "rz")}
        return {
            "off": float(row["epa_per_play_offense_5g"]),
            "def": float(row["epa_per_play_defense_allowed_5g"]),
            "pr": float(row["pass_rate_5g"]),
            "so": float(row["success_rate_offense_5g"]),
            "sd": float(row["success_rate_defense_allowed_5g"]),
            "pg": float(row["pressure_rate_generated_5g"]),
            "pa": float(row["pressure_rate_allowed_5g"]),
            "rz": float(row["red_zone_td_rate_5g"]),
        }

    hm = _side(home_row)
    am = _side(away_row)

    def _diff(h_v: float | None, a_v: float | None, how: str) -> float | None:
        if h_v is None or a_v is None:
            return None
        return h_v - a_v if how == "h-a" else a_v - h_v

    if None in (hm["so"], am["so"], hm["sd"], am["sd"]):
        diff_sr: float | None = None
    else:
        diff_sr = ((hm["so"] - am["so"]) + (am["sd"] - hm["sd"])) / 2.0
    return {
        "home_off_epa_5g": hm["off"],
        "away_off_epa_5g": am["off"],
        "home_def_epa_allowed_5g": hm["def"],
        "away_def_epa_allowed_5g": am["def"],
        "home_pass_rate_5g": hm["pr"],
        "away_pass_rate_5g": am["pr"],
        "home_success_offense_5g": hm["so"],
        "away_success_offense_5g": am["so"],
        "home_success_defense_allowed_5g": hm["sd"],
        "away_success_defense_allowed_5g": am["sd"],
        "matchup_diff_off_epa_5g": _diff(hm["off"], am["off"], "h-a"),
        "matchup_diff_def_epa_allowed_5g": _diff(hm["def"], am["def"], "a-h"),
        "matchup_diff_success_rate_5g": diff_sr,
        "matchup_diff_pressure_generated_5g": _diff(hm["pg"], am["pg"], "h-a"),
        "matchup_diff_pressure_allowed_5g": _diff(hm["pa"], am["pa"], "a-h"),
        "matchup_diff_red_zone_td_rate_5g": _diff(hm["rz"], am["rz"], "h-a"),
    }


def _resolve_pin(candidates: Sequence[Path], expected: str, label: str) -> Path:
    for path in candidates:
        if not path.is_file():
            continue
        refuse_forbidden_path(path)
        digest = sha256_file(path)
        if digest != expected:
            raise ReconRefuse(f"{label} sha256 {digest} != pin {expected}")
        return path
    raise ReconRefuse(f"{label} pin {expected[:8]} not found in {list(candidates)}")


def load_games_identity(path: Path | None = None) -> list[dict[str, Any]]:
    games_path = (
        Path(path)
        if path is not None
        else _resolve_pin(DEFAULT_GAMES_CANDIDATES, GAMES_SHA256, "games.csv")
    )
    refuse_forbidden_path(games_path)
    if path is not None and sha256_file(games_path) != GAMES_SHA256:
        raise ReconRefuse("games.csv pin drifted")
    rows: list[dict[str, Any]] = []
    with games_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(GAMES_IDENTITY_COLS) - set(reader.fieldnames or [])
        if missing:
            raise ReconRefuse(f"games.csv missing identity cols {sorted(missing)}")
        for raw in reader:
            season = int(raw["season"])
            if season in SEALED_SEASONS:
                raise ReconRefuse(f"sealed season {season} in games.csv")
            if season not in PERMITTED_SEASONS:
                continue
            week = int(raw["week"])
            if week < 1 or week > 18:
                continue
            kick = str(raw.get("kickoff_utc") or "").strip()
            if not kick:
                raise ReconRefuse(f"missing kickoff_utc for {raw.get('game_id')}")
            rows.append(
                {
                    "season": season,
                    "week": week,
                    "game_id": str(raw["game_id"]),
                    "home": str(raw["home"]),
                    "away": str(raw["away"]),
                    "kickoff_utc": kick,
                }
            )
    if not rows:
        raise ReconRefuse("no 2020–23 REG identity rows in games.csv")
    return rows


def load_prior_scores(
    *,
    outcomes_path: Path | None = None,
    scores_2023_path: Path | None = None,
    helper: ModuleType,
) -> list[dict[str, Any]]:
    """Strictly prior score-only. No EPA / trailing / Stage C columns."""
    completed: list[dict[str, Any]] = []
    apply_2020_23_identity(helper)
    outcomes = (
        Path(outcomes_path)
        if outcomes_path is not None
        else _resolve_pin(
            DEFAULT_OUTCOMES_CANDIDATES, OUTCOMES_SHA256, "outcomes 50bda875"
        )
    )
    refuse_forbidden_path(outcomes)
    if sha256_file(outcomes) != OUTCOMES_SHA256:
        raise ReconRefuse("outcomes pin drifted")
    with outcomes.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        banned = {
            col
            for col in (reader.fieldnames or [])
            if col.startswith(("trailing_", "packaged_"))
            or "epa" in col.lower()
            or col.endswith("_err")
        }
        if banned:
            raise ReconRefuse(f"outcomes banned columns {sorted(banned)}")
        allowed = {"season", "week", "home", "away", "home_score", "away_score"}
        extra = set(reader.fieldnames or []) - allowed
        if extra:
            raise ReconRefuse(f"outcomes unexpected columns {sorted(extra)}")
        for raw in reader:
            season = int(raw["season"])
            if season in SEALED_SEASONS:
                raise ReconRefuse(f"sealed season in outcomes {season}")
            if season not in (2020, 2021, 2022):
                continue
            completed.append(
                {
                    "season": season,
                    "week": int(raw["week"]),
                    "home": str(raw["home"]),
                    "away": str(raw["away"]),
                    "home_score": float(raw["home_score"]),
                    "away_score": float(raw["away_score"]),
                    "source": "outcomes_50bda875",
                }
            )

    scores_2023 = Path(scores_2023_path) if scores_2023_path else DEFAULT_SCORES_2023
    if scores_2023.is_file():
        refuse_forbidden_path(scores_2023)
        digest = sha256_file(scores_2023)
        if digest != SCORES_2023_SHA256:
            raise ReconRefuse(f"2023 score extract sha256 {digest} != {SCORES_2023_SHA256}")
        with scores_2023.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                if str(raw.get("season_type") or "REG").upper() != "REG":
                    continue
                season = int(raw["season"])
                if season != 2023:
                    raise ReconRefuse(f"2023 extract contains season {season}")
                home = helper.normalize_pbp_abbr(str(raw["home"]))
                away = helper.normalize_pbp_abbr(str(raw["away"]))
                completed.append(
                    {
                        "season": season,
                        "week": int(raw["week"]),
                        "game_id": str(raw.get("game_id") or ""),
                        "home": home,
                        "away": away,
                        "home_score": float(raw["home_score"]),
                        "away_score": float(raw["away_score"]),
                        "source": "pbp_extract_253e178b",
                    }
                )
    return completed


def attach_kickoffs(
    completed: list[dict[str, Any]], games: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {g["game_id"]: g for g in games}
    by_key = {(g["season"], g["week"], g["home"], g["away"]): g for g in games}
    out: list[dict[str, Any]] = []
    for row in completed:
        hit = None
        gid = str(row.get("game_id") or "")
        if gid and gid in by_id:
            hit = by_id[gid]
        else:
            hit = by_key.get((row["season"], row["week"], row["home"], row["away"]))
        if hit is None:
            continue
        out.append({**row, "kickoff_utc": hit["kickoff_utc"], "game_id": hit["game_id"]})
    return out


def freeze_completeness(
    targets: Sequence[Mapping[str, Any]],
    completed: Sequence[Mapping[str, Any]],
    helper: ModuleType,
) -> dict[str, Any]:
    """Freeze eligible / excluded sets BEFORE error join or PBP open."""
    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for raw in targets:
        season = int(raw["season"])
        week = int(raw["week"])
        gid = str(raw["game_id"])
        home = str(raw["home"])
        away = str(raw["away"])
        kick = str(raw["kickoff_utc"])
        reasons: list[str] = []
        if season in SEALED_SEASONS:
            reasons.append(f"SEALED_SEASON_{season}")
        if season not in PERMITTED_SEASONS:
            reasons.append(f"SEASON_OUT_OF_WINDOW_{season}")
        if week < 1 or week > 18:
            reasons.append(f"NON_REG_WEEK_{week}")
        if week <= 1:
            reasons.append(
                "W1_NO_PRIOR: rating_week=0 / T5 0-0 refused / no last-played fill"
            )
        if not kick:
            reasons.append("MISSING_KICKOFF")
        rating_week = week - 1
        rec = {
            "game_id": gid,
            "season": season,
            "week": week,
            "home": home,
            "away": away,
            "kickoff_utc": kick,
            "rating_week": rating_week,
        }
        if reasons:
            excluded.append({**rec, "reasons": reasons})
            continue
        cutoff = helper.parse_utc(kick)
        w_h, l_h, n_h = helper.record_asof(completed, home, cutoff, season)
        w_a, l_a, n_a = helper.record_asof(completed, away, cutoff, season)
        rec["record_asof_home"] = f"{w_h}-{l_h}"
        rec["record_asof_away"] = f"{w_a}-{l_a}"
        rec["n_home"] = n_h
        rec["n_away"] = n_a
        if n_h < 1 or n_a < 1:
            excluded.append(
                {
                    **rec,
                    "reasons": [
                        "T5_ZERO_COMPLETED_SAME_SEASON: no-fill / no 0-0 baseline"
                    ],
                }
            )
            continue
        eligible.append(rec)
    ids = [r["game_id"] for r in eligible]
    seal = {
        "schema_version": "nfl-t5111u-completeness-seal-v1",
        "frozen_before_errors": True,
        "frozen_before_pbp_open": True,
        "label": LABEL_RESEARCH,
        "cert_candidate": 0,
        "n_targets": len(targets),
        "n_eligible": len(eligible),
        "n_excluded": len(excluded),
        "selection_hash": helper.selection_hash(ids) if ids else sha256_text("\n"),
        "eligible_game_ids": sorted(ids),
        "excluded": excluded,
        "eligible": eligible,
    }
    seal["completeness_sha256"] = sha256_text(
        json.dumps(seal, sort_keys=True, separators=(",", ":"), default=str)
    )
    return seal


def load_pbp_plays(
    *,
    archive: Path,
    seasons: Sequence[int],
    max_week: int,
    helper: ModuleType,
) -> Any:
    refuse_forbidden_path(archive)
    try:
        import pandas as pd
    except ImportError as exc:
        raise ReconRefuse("pandas required to import T1 helper / read PBP") from exc
    frames = []
    for season in seasons:
        if season in SEALED_SEASONS:
            raise ReconRefuse(f"refusing sealed PBP season {season}")
        if season not in PERMITTED_SEASONS:
            raise ReconRefuse(f"PBP season {season} not in 2020–23 window")
        path = Path(archive) / f"play_by_play_{season}.csv"
        refuse_forbidden_path(path)
        if not path.is_file():
            raise ReconRefuse(f"PBP missing: {path}")
        usecols = [c for c in PBP_COLS]
        frame = pd.read_csv(path, usecols=lambda c: c in usecols, low_memory=False)
        seasons_seen = sorted(
            {int(x) for x in frame["season"].dropna().astype(int).unique().tolist()}
        )
        if seasons_seen != [season]:
            raise ReconRefuse(f"{path.name} seasons {seasons_seen} != [{season}]")
        plays = frame[
            (frame["season"] == season)
            & (frame["season_type"].astype(str).str.upper() == "REG")
            & (frame["week"] <= max_week)
            & frame["week"].notna()
            & frame["posteam"].notna()
            & frame["play_type"].isin(["pass", "run"])
        ].copy()
        frames.append(plays)
    if not frames:
        raise ReconRefuse("no PBP frames loaded")
    return pd.concat(frames, ignore_index=True)


def _window_game_ids(t1: Any, team: str, rating_week: int) -> list[str]:
    hit = t1[(t1["team"] == team) & (t1["week"] <= rating_week)]
    ids: list[str] = []
    for raw in hit["source_game_ids"].tolist():
        ids.extend(str(raw).split("|"))
    return sorted({i for i in ids if i and i != "nan"})


def _assert_prior_to_cutoff(
    game_ids: Iterable[str],
    kickoff_by_gid: Mapping[str, str],
    cutoff: datetime,
    helper: ModuleType,
    target_id: str,
) -> None:
    for gid in game_ids:
        kick = kickoff_by_gid.get(gid)
        if kick is None or helper.parse_utc(kick) >= cutoff:
            raise ReconRefuse(
                f"per-target leakage {target_id}: consumed {gid} kickoff={kick}"
            )


def cell_row_hash(row: Mapping[str, Any]) -> str:
    payload = {
        "game_id": row["game_id"],
        "field": row["field"],
        "status": row["status"],
        "reconstructed_value": row["reconstructed_value"],
        "rating_week": row["rating_week"],
        "pregame_cutoff_utc": row["pregame_cutoff_utc"],
        "source_sha256": row.get("source_sha256", ""),
    }
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def reconstruct_slate(
    *,
    targets: Sequence[Mapping[str, Any]],
    games: Sequence[Mapping[str, Any]],
    completed: Sequence[Mapping[str, Any]],
    helper: ModuleType | None = None,
    plays: Any | None = None,
    archive: Path | None = None,
    pbp_sha_by_season: Mapping[int, str] | None = None,
    completeness_seal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build RECONSTRUCTED packets. Completeness must already be frozen."""
    mod = helper if helper is not None else load_verified_helper()
    apply_2020_23_identity(mod)
    if completeness_seal is None:
        raise ReconRefuse("completeness/exclusions must be frozen before errors")
    if not completeness_seal.get("frozen_before_errors"):
        raise ReconRefuse("completeness seal missing frozen_before_errors")
    eligible_ids = set(completeness_seal.get("eligible_game_ids") or [])
    work = [t for t in targets if t["game_id"] in eligible_ids]
    extra = [t["game_id"] for t in work if t["game_id"] not in eligible_ids]
    if extra:
        raise ReconRefuse(f"targets not in completeness seal: {extra[:8]}")

    kickoff_by_gid = {g["game_id"]: g["kickoff_utc"] for g in games}
    if plays is None:
        seasons = sorted({int(t["season"]) for t in work})
        max_week = max((int(t["week"]) - 1) for t in work) if work else 0
        plays = load_pbp_plays(
            archive=Path(archive) if archive else DEFAULT_PBP_ARCHIVE,
            seasons=seasons,
            max_week=max_week,
            helper=mod,
        )

    matrix: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    complete: list[str] = []
    partial: list[dict[str, Any]] = []

    t1 = None
    t2 = None
    if work:
        if getattr(plays, "empty", True):
            raise ReconRefuse("no prior-week REG pass/run plays")
        t1 = mod.t1_from_plays(plays)
        t2 = mod.rolling_5g(t1)

    t1_lineage = (
        "T1=nfl_dp_team_situational_weekly port from helper 7e77c57f "
        "(pressure=sack|qb_hit on pass; RZ=yardline_100<=20). "
        "T2=rolling_5g ROWS 4 PRECEDING AND CURRENT. "
        "T3=exact rating_week=week-1; no last-played fill. "
        "T4 helper.main contract diffs. "
        "T5 team_strength_from_record same-season as-of. "
        "RETRO_FIT / RESEARCH_CONSUMED_RETRO / RECONSTRUCTED."
    )

    eligible_by_id = {r["game_id"]: r for r in completeness_seal.get("eligible") or []}
    for rec in work:
        gid = rec["game_id"]
        sealed = eligible_by_id[gid]
        home = sealed["home"]
        away = sealed["away"]
        week = int(sealed["week"])
        season = int(sealed["season"])
        kick = sealed["kickoff_utc"]
        rating_week = int(sealed["rating_week"])
        cutoff = mod.parse_utc(kick)
        rest_et = mod.rest_days_et(kick)
        rec_h = sealed["record_asof_home"]
        rec_a = sealed["record_asof_away"]
        n_h = sealed["n_home"]
        n_a = sealed["n_away"]

        h = mod.lookup_t2(t2, home, rating_week)
        a = mod.lookup_t2(t2, away, rating_week)
        for team in (home, away):
            _assert_prior_to_cutoff(
                _window_game_ids(t1, team, rating_week),
                kickoff_by_gid,
                cutoff,
                mod,
                gid,
            )
        for side_row in (h, a):
            if side_row is None:
                continue
            consumed = [
                cgid
                for cgid in str(side_row.get("source_game_ids", "")).split("|")
                if cgid and cgid != "nan"
            ]
            _assert_prior_to_cutoff(consumed, kickoff_by_gid, cutoff, mod, gid)

        def add(
            field: str,
            status: str,
            *,
            value: object = "",
            source_path: str = "",
            source_sha256: str = "",
            lineage: str = "",
            evidence: str = "",
            exclusion_reason: str = "",
            notes: str = "",
        ) -> None:
            row = {
                "game_id": gid,
                "season": season,
                "week": week,
                "home_team": home,
                "away_team": away,
                "field": field,
                "status": status,
                "reconstructed_value": value,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "source_sha8": source_sha256[:8] if source_sha256 else "",
                "pregame_cutoff_utc": kick,
                "rating_week": str(rating_week),
                "derivation_lineage": lineage,
                "availability_evidence": evidence,
                "exclusion_reason": exclusion_reason,
                "notes": notes,
                "label": LABEL_RECONSTRUCTED,
                "fit_label": LABEL_RETRO_FIT,
                "research_label": LABEL_RESEARCH,
            }
            row["row_sha256"] = cell_row_hash(row)
            matrix.append(row)
            status_counts[status] += 1

        for field, value in {
            "game_id": gid,
            "home_team": home,
            "away_team": away,
            "matchup_season": str(season),
            "matchup_week": str(week),
        }.items():
            add(
                field,
                "DERIVED_PREGAME",
                value=value,
                source_path="games.csv 4fe1cdd7",
                source_sha256=GAMES_SHA256,
                lineage="2020-23 identity from games.csv pin; kickoff UTC Z",
                evidence=f"game_id={gid}",
                notes="identity plumbing; not a new feature",
            )
        for side in ("home", "away"):
            add(
                f"rest_days_{side}",
                "DERIVED_PREGAME",
                value=str(rest_et),
                source_path="helper.rest_days_et",
                source_sha256=HELPER_SHA256,
                lineage="ET DOW heuristic (Thu=4, Mon=6, else=7). Same both sides.",
                evidence=f"kickoff_utc={kick} rest_et={rest_et}",
                notes="games.csv rest_days_* hardcoded 7.0 NOT used",
            )
        for side, rec_wl, n_played in (
            ("home", rec_h, n_h),
            ("away", rec_a, n_a),
        ):
            off_i, def_i = mod.team_strength_from_record(rec_wl)
            t5_src = (
                OUTCOMES_SHA256 if season <= 2022 else SCORES_2023_SHA256
            )
            add(
                f"offense_index_{side}",
                "DERIVED_PREGAME",
                value=_fmt(off_i, 6),
                source_path="helper.team_strength_from_record",
                source_sha256=t5_src,
                lineage="T5: off=clamp(0.90+0.22*wp, 0.82, 1.18) same-season as-of",
                evidence=f"record_asof={rec_wl} n={n_played} cutoff={kick}",
                notes="not 1ee90fac; not a 2026 panel index",
            )
            add(
                f"defense_index_{side}",
                "DERIVED_PREGAME",
                value=_fmt(def_i, 6),
                source_path="helper.team_strength_from_record",
                source_sha256=t5_src,
                lineage="T5: def=clamp(0.92+0.20*wp, 0.82, 1.20) same-season as-of",
                evidence=f"record_asof={rec_wl} n={n_played} cutoff={kick}",
                notes="not 1ee90fac; not a 2026 panel index",
            )

        values = t4_from_t2_sides(h, a)
        pbp_sha = ""
        if pbp_sha_by_season:
            pbp_sha = pbp_sha_by_season.get(season, "")
        for field in (
            "home_off_epa_5g",
            "away_off_epa_5g",
            "home_def_epa_allowed_5g",
            "away_def_epa_allowed_5g",
            "home_pass_rate_5g",
            "away_pass_rate_5g",
            "home_success_offense_5g",
            "away_success_offense_5g",
            "home_success_defense_allowed_5g",
            "away_success_defense_allowed_5g",
            "matchup_diff_off_epa_5g",
            "matchup_diff_def_epa_allowed_5g",
            "matchup_diff_success_rate_5g",
            "matchup_diff_pressure_generated_5g",
            "matchup_diff_pressure_allowed_5g",
            "matchup_diff_red_zone_td_rate_5g",
        ):
            val = values[field]
            if not _finite(val):
                add(
                    field,
                    "MISSING_RECORD",
                    source_path="helper.lookup_t2",
                    source_sha256=pbp_sha or HELPER_SHA256,
                    lineage=t1_lineage,
                    evidence=f"T2 rating_week={rating_week}; fail-closed",
                    notes="no default; no last-played-week T2 fill",
                    exclusion_reason="T2 row absent at exact rating_week or non-finite metric",
                )
                continue
            add(
                field,
                "DERIVED_PREGAME",
                value=_fmt(float(val), 8),
                source_path="helper.t1_from_plays + rolling_5g + T4",
                source_sha256=pbp_sha or HELPER_SHA256,
                lineage=t1_lineage,
                evidence=f"T2 rating_week={rating_week} cutoff={kick}",
                notes="Same T1–T4 as 7e77c57f. RETRO_FIT / RESEARCH_CONSUMED_RETRO.",
            )

        derived_here = sum(
            1
            for row in matrix
            if row["game_id"] == gid and row["status"] == "DERIVED_PREGAME"
        )
        missing_here = sum(
            1
            for row in matrix
            if row["game_id"] == gid and row["status"] == "MISSING_RECORD"
        )
        fields_here = [row["field"] for row in matrix if row["game_id"] == gid]
        if set(fields_here) != set(CONTRACT_27) or len(fields_here) != 27:
            raise ReconRefuse(
                f"{gid} field set {fields_here} != CONTRACT_27"
            )
        if derived_here == 27 and missing_here == 0:
            complete.append(gid)
        else:
            partial.append(
                {
                    "game_id": gid,
                    "derived": derived_here,
                    "missing": missing_here,
                    "reason": "T2 exact rating_week miss or non-finite",
                }
            )

    matrix_sha = sha256_text(
        json.dumps(matrix, sort_keys=True, separators=(",", ":"), default=str)
    )
    provenance = provenance_table()
    return {
        "schema_version": "nfl-t5111u-recon-driver-v1",
        "label": LABEL_RECONSTRUCTED,
        "fit_label": LABEL_RETRO_FIT,
        "research_label": LABEL_RESEARCH,
        "cert_candidate": 0,
        "helper_sha256": HELPER_SHA256,
        "helper_tip": HELPER_TIP,
        "contract_sha256": CONTRACT_SHA256,
        "stage_c": False,
        "scored_look": False,
        "archived_if_mus_required": False,
        "old_main_oos_invoked": False,
        "opened_1ee90fac": False,
        "completeness_seal": dict(completeness_seal),
        "n_complete_27": len(complete),
        "n_partial": len(partial),
        "complete_game_ids": complete,
        "partial": partial,
        "status_counts": dict(status_counts),
        "matrix": matrix,
        "matrix_sha256": matrix_sha,
        "n_cells": len(matrix),
        "provenance": provenance,
        "incompatibilities": list(INCOMPATIBILITIES),
    }


def provenance_table() -> list[dict[str, str]]:
    return [
        {
            "field": ",".join(
                (
                    "game_id",
                    "home_team",
                    "away_team",
                    "matchup_season",
                    "matchup_week",
                )
            ),
            "source": "games.csv 4fe1cdd7 identity + kickoff_utc UTC Z",
            "sha256": GAMES_SHA256,
            "status": "hashed",
            "notes": "do not use games.csv rest_days_* or epa_* columns",
        },
        {
            "field": "rest_days_home,rest_days_away",
            "source": "helper.rest_days_et (ET DOW Thu=4 Mon=6 else=7)",
            "sha256": HELPER_SHA256,
            "status": "imported",
            "notes": "existing rest contract; both sides same value",
        },
        {
            "field": "offense_index_*,defense_index_*",
            "source": "helper.team_strength_from_record + record_asof",
            "sha256": f"{OUTCOMES_SHA256} / {SCORES_2023_SHA256}",
            "status": "imported",
            "notes": "2020-22 50bda875; 2023 PBP extract; same-season; W1 no-fill",
        },
        {
            "field": "T1/T2 5g EPA/success/pass/pressure/RZ",
            "source": "helper.t1_from_plays + rolling_5g + lookup_t2",
            "sha256": HELPER_SHA256,
            "status": "imported",
            "notes": "owned PBP 2020-23; exact rating_week=week-1; no last-played fill",
        },
        {
            "field": "T4 matchup_diff_*",
            "source": "helper.main T4 contract applied to imported T2 rows",
            "sha256": HELPER_SHA256,
            "status": "applied_unchanged",
            "notes": "not a helper export; not a new feature",
        },
        {
            "field": "Stage C / 1ee90fac / old OOS",
            "source": "forbidden",
            "sha256": "1ee90fac",
            "status": "FORBIDDEN",
            "notes": "not opened; not a missing-to-invent source",
        },
    ]


def load_stage_b_input_ref(path: Path | None = None) -> dict[str, Any]:
    """Approved-input schema/contract check. Does not rescore 2017 outcomes."""
    stage = Path(path) if path is not None else DEFAULT_STAGE_B
    refuse_forbidden_path(stage)
    digest = sha256_file(stage)
    if digest != STAGE_B_W7W8_SLICE_SHA256:
        raise ReconRefuse(
            f"Stage B W7–W8 slice sha256 {digest} != {STAGE_B_W7W8_SLICE_SHA256}"
        )
    rows: list[dict[str, str]] = []
    with stage.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    fields = sorted({row["field"] for row in rows})
    if set(fields) != set(CONTRACT_27):
        raise ReconRefuse(
            f"Stage B field set {fields} != CONTRACT_27 — do not loosen"
        )
    prior = {(row["game_id"], row["field"]): row for row in rows}
    identity = compare_cell_maps(prior, prior)
    if not identity["pass"]:
        raise ReconRefuse("Stage B self-compare failed")
    return {
        "path": str(stage),
        "slice_sha256": digest,
        "full_matrix_pin": STAGE_B_FULL_SHA256,
        "n_rows": len(rows),
        "n_games": len({row["game_id"] for row in rows}),
        "fields": list(CONTRACT_27),
        "self_compare": identity,
        "rescored_2017_outcomes": False,
    }


def write_recon_bindings(result: Mapping[str, Any], dest: Path) -> str:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "nfl-t5111u-recon-bindings-v1",
        "label": LABEL_RESEARCH,
        "cert_candidate": 0,
        "helper_sha256": HELPER_SHA256,
        "helper_tip": HELPER_TIP,
        "contract_sha256": CONTRACT_SHA256,
        "matrix_sha256": result.get("matrix_sha256"),
        "n_cells": result.get("n_cells"),
        "n_complete_27": result.get("n_complete_27"),
        "n_partial": result.get("n_partial"),
        "completeness_sha256": (result.get("completeness_seal") or {}).get(
            "completeness_sha256"
        ),
        "archived_if_mus_required": False,
        "old_b41f4b43_row_hash_match_expected": False,
        "incompatibilities": result.get("incompatibilities"),
        "provenance": result.get("provenance"),
        "written_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    dest.write_text(text, encoding="utf-8")
    return sha256_text(text)
