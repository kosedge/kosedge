"""t5157u R5-HISTORY-ID — 2013–2019 identity projection + Q2 complete (CERT=0).

Identity columns only from archive PBP 2013–2019. Bijective join to approved
score-only / kickoff pins. Original R5 Q2 rule unchanged. Appends completed
candidate freeze against pinned IF496 bytes. Does not regenerate IF, overwrite
HOLD artifacts, score Phase 2, or reopen 2017 Q2 eval.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .builder import challenger_margin
from .cohort_enforcement import (
    DEV_IF437_IDENTITY_SHA256,
    REG496_IDENTITY_SHA256,
    expected_profile_ids,
    PROFILE_DEV_IF437,
    PROFILE_FEATURE_RECON_REG496,
)
from .if_produce import FW_SHA256, IF_TIP, SIM_SHA256, SIMULATIONS
from .last_played_cohort import SCHEDULE_PATH, SCHEDULE_SHA256
from .market_arm_freeze import INTERSECTION_BYTES_SHA256, INTERSECTION_IDENTITY_SHA256
from .q2 import (
    A_Q2,
    B_Q2,
    FIT_POLICY,
    GAMES_SHA256,
    LAMBDA,
    OUTCOMES_SHA256,
    PARAMETER_LABEL,
    PRIOR_ALIAS,
    PRIOR_ALIAS_REVERSE,
    REGRESS_FRAC,
    Game,
    asof_for_targets,
    assert_asof_no_self_target,
    parse_kickoff,
    q2_pm_new,
    verify_q2_transfer_policy,
)
from .r5_496_freeze import (
    CANDIDATE_WEIGHT,
    LABEL_RECONSTRUCTED,
    LABEL_RESEARCH,
    LABEL_RETRO_FIT,
    R3_STOP,
    R3_WEIGHT_STOPPED,
    R5FreezeRefuse,
    TargetScoringRefuse,
    refuse_week_le_18_proxy,
    r5_history_for_target,
    split_scaffolding,
)
from .recon_driver import (
    DEFAULT_GAMES_CANDIDATES,
    DEFAULT_OUTCOMES_CANDIDATES,
    ERA_2020_23_PBP_TO_CANON,
    HELPER_PBP_TO_CANON_2017,
    sha256_file,
)

SCHEMA = "nfl-t5157u-r5-history-id-v1"
PATH_ID = "DEV_R5_HISTORY_ID"
TICKET = "t5157u"
OWNER_CLEAR = "t5157u"
R5_HISTORY_ID = "e6cc6927"
COS_ORDER_A = "1e3c47b8"
PARENT_TIP = "255adf7802830bc25814a739d62f65f095216203"
PARENT_STAMP = "df074369"
CERT_CANDIDATE = 0

IDENTITY_COLS = (
    "game_id",
    "old_game_id",
    "season",
    "season_type",
    "home_team",
    "away_team",
    "week",
    "game_date",
    "start_time",
)
IDENTITY_YEARS = (2013, 2014, 2015, 2016, 2017, 2018, 2019)
PROVEN_Q2_YEARS = tuple(range(2013, 2022))
SEALED_YEARS = (2022, 2023, 2024, 2025, 2026)
PBP_YEARS_FORBIDDEN = (2020, 2021, 2022, 2023, 2024, 2025, 2026)

DEFAULT_ARCHIVE = Path("/Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01")
HOLD_DIR = Path("data/ops/nfl-t5155u-r5-496-freeze")
IF_FORECASTS_NAME = "FORECASTS_DEV_R5_496.json"
IF_FORECASTS_SHA256 = "96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407"
OUT_DIR = Path("data/ops/nfl-t5157u-r5-history-id")

# Existing maps only — composed, never invented.
GAMES_TO_CANON = {"LA": "LAR", "WAS": "WSH", "SD": "SD"}
EXISTING_TEAM_MAPS = (
    dict(HELPER_PBP_TO_CANON_2017),
    dict(ERA_2020_23_PBP_TO_CANON),
    dict(GAMES_TO_CANON),
    dict(PRIOR_ALIAS),
    dict(PRIOR_ALIAS_REVERSE),
)

HOLD_PROTECTED = (
    "FORECASTS_DEV_R5_496.json",
    "Q2_HISTORY_FREEZE.json",
    "FREEZE_MANIFEST.json",
    "IDENTITY_MANIFEST.json",
    "FEATURE_VALIDATION.json",
    "SPLIT_SCAFFOLDING.json",
    "COMPARE_437.json",
    "SPEC.json",
    "SOURCE_PINS.json",
    "SCORING_REFUSE.json",
    "PHASE2_POSITIVE_PATH.json",
    "STOP_AWAITING_ALEX_PREFLIGHT_AND_COS_BIND.json",
)

LIMITATIONS = {
    "publication_timestamp_status": "unverified",
    "observation_timestamp_status": "unverified",
    "fit_label": LABEL_RETRO_FIT,
    "label": LABEL_RECONSTRUCTED,
    "research_label": LABEL_RESEARCH,
    "production_causal_claim": False,
    "nfl_green": False,
    "eval": None,
    "scoring": None,
    "market_edge": None,
    "cert_candidate": CERT_CANDIDATE,
}


class HistoryIdRefuse(R5FreezeRefuse):
    """Fail-closed R5-HISTORY-ID."""


class HistoryIdHold(HistoryIdRefuse):
    """Identity/join failed — HOLD, no invented history."""


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dump_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2) + "\n"


def write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dump_json(payload)
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def existing_alias_closure(team: str) -> frozenset[str]:
    """Franchise aliases reachable from existing maps only."""
    seen = {str(team)}
    changed = True
    while changed:
        changed = False
        for token in list(seen):
            for mapping in EXISTING_TEAM_MAPS:
                mapped = mapping.get(token)
                if mapped and mapped not in seen:
                    seen.add(mapped)
                    changed = True
    return frozenset(seen)


def teams_alias_match(left: str, right: str) -> bool:
    if left == right:
        return True
    return bool(existing_alias_closure(left) & existing_alias_closure(right))


def parse_manifest_sha256(manifest_text: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for line in manifest_text.splitlines():
        match = re.search(r"play_by_play_(\d{4})\.csv.*?`([0-9a-f]{64})`", line)
        if match:
            out[int(match.group(1))] = match.group(2)
    return out


def snapshot_hold_hashes(repo: Path) -> dict[str, str]:
    hold = repo / HOLD_DIR
    out: dict[str, str] = {}
    for name in HOLD_PROTECTED:
        path = hold / name
        if not path.is_file():
            raise HistoryIdRefuse(f"HOLD artifact missing {name}")
        out[name] = sha256_file(path)
    if out[IF_FORECASTS_NAME] != IF_FORECASTS_SHA256:
        raise HistoryIdRefuse(
            f"IF496 bytes drifted {out[IF_FORECASTS_NAME]} != pin 96d3aa6f"
        )
    return out


def assert_hold_unchanged(repo: Path, before: Mapping[str, str]) -> dict[str, str]:
    after = snapshot_hold_hashes(repo)
    drifted = {
        name: {"before": before[name], "after": after[name]}
        for name in before
        if before[name] != after[name]
    }
    if drifted:
        raise HistoryIdRefuse(f"HOLD artifacts overwritten: {sorted(drifted)}")
    return after


def _locate_pin(candidates: Sequence[Path], expected_sha: str, label: str) -> Path:
    for path in candidates:
        if path.is_file():
            digest = sha256_file(path)
            if digest != expected_sha:
                raise HistoryIdRefuse(f"{label} sha {digest} != pin {expected_sha[:8]}")
            return path
    raise HistoryIdRefuse(f"{label} pin not found")


def verify_pbp_file_shas(
    archive: Path,
    *,
    years: Sequence[int] = IDENTITY_YEARS,
) -> dict[str, Any]:
    if any(int(year) in PBP_YEARS_FORBIDDEN for year in years):
        raise HistoryIdRefuse("refusing protected/forbidden 2020–26 PBP files")
    if any(int(year) not in IDENTITY_YEARS for year in years):
        raise HistoryIdRefuse(f"identity years must be 2013–2019, got {list(years)}")
    manifest_path = archive / "MANIFEST.md"
    if not manifest_path.is_file():
        raise HistoryIdRefuse(f"MANIFEST.md missing under {archive}")
    manifest = parse_manifest_sha256(manifest_path.read_text(encoding="utf-8"))
    files: dict[str, Any] = {}
    for year in years:
        name = f"play_by_play_{year}.csv"
        path = archive / name
        if not path.is_file():
            raise HistoryIdRefuse(f"missing {path}")
        expected = manifest.get(int(year))
        if not expected:
            raise HistoryIdRefuse(f"MANIFEST.md has no sha256 for {name}")
        digest = sha256_file(path)
        if digest != expected:
            raise HistoryIdRefuse(f"{name} sha {digest} != MANIFEST {expected}")
        files[str(year)] = {
            "filename": name,
            "path": str(path),
            "sha256": digest,
            "bytes": path.stat().st_size,
            "manifest_sha256": expected,
            "match": True,
        }
    return {
        "schema_version": SCHEMA,
        "archive": str(archive),
        "manifest_path": str(manifest_path),
        "years": [int(y) for y in years],
        "files": files,
        "n_files": len(files),
        "all_match": True,
        "protected_2024_26_opened": False,
        "pbp_2020_2023_opened": False,
    }


def project_identities_from_pbp(
    archive: Path,
    *,
    years: Sequence[int] = IDENTITY_YEARS,
    file_shas: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Dedup identity columns only. Prove explicit season_type. No week≤18 proxy."""
    refuse_week_le_18_proxy(claimed_reg=True, used_week_le_18=False)
    shas = file_shas or verify_pbp_file_shas(archive, years=years)
    games: list[dict[str, str]] = []
    per_year: dict[str, Any] = {}
    for year in years:
        path = archive / f"play_by_play_{year}.csv"
        seen: dict[str, dict[str, str]] = {}
        types: dict[str, set[str]] = defaultdict(set)
        inconsistent: list[dict[str, str]] = []
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = [c for c in IDENTITY_COLS if c not in (reader.fieldnames or [])]
            if missing:
                raise HistoryIdRefuse(f"{path.name} missing identity cols {missing}")
            for raw in reader:
                rec = {col: str(raw.get(col) or "") for col in IDENTITY_COLS}
                gid = rec["game_id"]
                if not gid:
                    raise HistoryIdRefuse(f"{year} row missing game_id")
                season_type = rec["season_type"]
                if season_type not in {"REG", "POST"}:
                    raise HistoryIdRefuse(
                        f"{gid} season_type={season_type!r} is not explicit REG/POST "
                        "(refusing invented season_type)"
                    )
                types[gid].add(season_type)
                if gid not in seen:
                    seen[gid] = rec
                    continue
                for col in IDENTITY_COLS:
                    if seen[gid][col] != rec[col]:
                        inconsistent.append(
                            {
                                "game_id": gid,
                                "column": col,
                                "first": seen[gid][col],
                                "other": rec[col],
                            }
                        )
        mixed = {gid: sorted(vals) for gid, vals in types.items() if len(vals) > 1}
        if inconsistent or mixed:
            raise HistoryIdRefuse(
                f"{year} identity inconsistent: fields={len(inconsistent)} mixed_type={len(mixed)}"
            )
        counts = Counter(row["season_type"] for row in seen.values())
        if counts["REG"] <= 0:
            raise HistoryIdRefuse(f"{year} has no explicit season_type=REG rows")
        per_year[str(year)] = {
            "n_games": len(seen),
            "n_reg": counts["REG"],
            "n_post": counts["POST"],
            "season_type_explicit": True,
            "week_le_18_proxy": False,
            "file_sha256": shas["files"][str(year)]["sha256"],
        }
        games.extend(seen[gid] for gid in sorted(seen))
    reg_ids = [g["game_id"] for g in games if g["season_type"] == "REG"]
    post_ids = [g["game_id"] for g in games if g["season_type"] == "POST"]
    payload = {
        "schema_version": SCHEMA,
        "path_id": PATH_ID,
        "ticket": TICKET,
        "r5_history_id": R5_HISTORY_ID,
        "role": "identity_projection_only",
        "columns": list(IDENTITY_COLS),
        "years": [int(y) for y in years],
        "n_games": len(games),
        "n_reg": len(reg_ids),
        "n_post": len(post_ids),
        "n_other": 0,
        "per_year": per_year,
        "reg_game_ids": reg_ids,
        "post_game_ids": post_ids,
        "games": games,
        "membership_rule": "explicit season_type=REG on PBP identity extract; not week<=18",
        "week_le_18_proxy": False,
        "invented_season_type": False,
        "play_values_used": False,
        "epa_used": False,
        "raw_pbp_feature_reconstruction": False,
        "identity_sha256": sha256_text("\n".join(reg_ids) + "\n"),
        "post_identity_sha256": sha256_text("\n".join(post_ids) + "\n"),
        **LIMITATIONS,
    }
    return payload


def _load_games_identity(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = []
        for raw in csv.DictReader(handle):
            season = int(float(raw["season"]))
            if season in SEALED_YEARS:
                continue
            if season < 2013 or season > 2021:
                continue
            rows.append(
                {
                    "season": str(season),
                    "week": str(int(float(raw["week"]))),
                    "game_id": str(raw["game_id"]),
                    "home": str(raw["home"]),
                    "away": str(raw["away"]),
                    "kickoff_utc": str(raw["kickoff_utc"]),
                }
            )
    return rows


def _load_outcomes_score_only(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = []
        for raw in csv.DictReader(handle):
            season = int(float(raw["season"]))
            if season in SEALED_YEARS or season < 2013 or season > 2021:
                continue
            rows.append(
                {
                    "season": str(season),
                    "week": str(int(float(raw["week"]))),
                    "home": str(raw["home"]),
                    "away": str(raw["away"]),
                    "home_score": str(raw["home_score"]),
                    "away_score": str(raw["away_score"]),
                }
            )
    return rows


def _load_schedule_reg_2020_2021(path: Path) -> list[dict[str, str]]:
    out = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            season = int(raw["season"])
            if season not in (2020, 2021):
                continue
            if str(raw["season_type"]).upper() != "REG":
                continue
            out.append(
                {
                    "game_id": str(raw["game_id"]),
                    "season": str(season),
                    "week": str(int(raw["week"])),
                    "season_type": "REG",
                    "home_team": str(raw["home"]),
                    "away_team": str(raw["away"]),
                    "old_game_id": "",
                    "game_date": "",
                    "start_time": "",
                    "identity_source": "schedule_results_2020_2023.csv",
                }
            )
    return out


def _index_games(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        gid = row["game_id"]
        if gid in by_id:
            raise HistoryIdRefuse(f"duplicate games.csv game_id {gid}")
        by_id[gid] = dict(row)
    return by_id


def _index_outcomes(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[int, int, str, str], dict[str, str]]:
    by_key: dict[tuple[int, int, str, str], dict[str, str]] = {}
    for row in rows:
        key = (int(row["season"]), int(row["week"]), row["home"], row["away"])
        if key in by_key:
            raise HistoryIdRefuse(f"ambiguous outcomes key {key}")
        by_key[key] = dict(row)
    return by_key


def _fallback_sw_ha(
    rec: Mapping[str, str],
    games_rows: Sequence[Mapping[str, str]],
) -> tuple[dict[str, str] | None, str | None]:
    season = int(rec["season"])
    week = int(rec["week"])
    home_opts = existing_alias_closure(str(rec["home_team"]))
    away_opts = existing_alias_closure(str(rec["away_team"]))
    cands = [
        row
        for row in games_rows
        if int(row["season"]) == season
        and int(row["week"]) == week
        and row["home"] in home_opts
        and row["away"] in away_opts
    ]
    if len(cands) == 1:
        return dict(cands[0]), "season_week_home_away_existing_team_map"
    if len(cands) > 1:
        raise HistoryIdRefuse(
            f"{rec['game_id']} ambiguous season/week/home/away join n={len(cands)}"
        )
    return None, None


def join_identities(
    identities: Sequence[Mapping[str, str]],
    games_rows: Sequence[Mapping[str, str]],
    outcomes_rows: Sequence[Mapping[str, str]],
    *,
    identity_source: str,
    require_complete_season: bool = False,
) -> dict[str, Any]:
    refuse_week_le_18_proxy(claimed_reg=True, used_week_le_18=False)
    games_by_id = _index_games(games_rows)
    outcomes_by_key = _index_outcomes(outcomes_rows)
    joined_reg: list[dict[str, Any]] = []
    joined_post: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for rec in identities:
        gid = rec["game_id"]
        season = int(rec["season"])
        week = int(rec["week"])
        season_type = rec["season_type"]
        game = games_by_id.get(gid)
        join_how = "canonical_game_id" if game is not None else None
        if game is None:
            game, join_how = _fallback_sw_ha(rec, games_rows)
        if game is None:
            unmatched.append(
                {
                    "game_id": gid,
                    "season": season,
                    "week": week,
                    "season_type": season_type,
                    "home": rec.get("home_team"),
                    "away": rec.get("away_team"),
                    "missing": "games.csv",
                    "identity_source": identity_source,
                }
            )
            continue
        if int(game["season"]) != season or int(game["week"]) != week:
            conflicts.append(
                {
                    "game_id": gid,
                    "reason": "season_week_conflict",
                    "identity": {"season": season, "week": week},
                    "games": {"season": int(game["season"]), "week": int(game["week"])},
                }
            )
            continue
        id_home = str(rec.get("home_team") or rec.get("home") or "")
        id_away = str(rec.get("away_team") or rec.get("away") or "")
        if id_home and not teams_alias_match(id_home, game["home"]):
            conflicts.append(
                {
                    "game_id": gid,
                    "reason": "home_team_conflict_after_existing_map",
                    "identity_home": id_home,
                    "games_home": game["home"],
                }
            )
            continue
        if id_away and not teams_alias_match(id_away, game["away"]):
            conflicts.append(
                {
                    "game_id": gid,
                    "reason": "away_team_conflict_after_existing_map",
                    "identity_away": id_away,
                    "games_away": game["away"],
                }
            )
            continue
        key = (int(game["season"]), int(game["week"]), game["home"], game["away"])
        outcome = outcomes_by_key.get(key)
        if outcome is None:
            unmatched.append(
                {
                    "game_id": gid,
                    "season": season,
                    "week": week,
                    "season_type": season_type,
                    "home": game["home"],
                    "away": game["away"],
                    "missing": "outcomes_50bda875",
                    "join": join_how,
                    "identity_source": identity_source,
                }
            )
            continue
        row = {
            "game_id": gid,
            "season": season,
            "week": week,
            "season_type": season_type,
            "home": game["home"],
            "away": game["away"],
            "identity_home": id_home,
            "identity_away": id_away,
            "kickoff_utc": game["kickoff_utc"],
            "home_score": float(outcome["home_score"]),
            "away_score": float(outcome["away_score"]),
            "join": join_how,
            "identity_source": identity_source,
        }
        if season_type == "REG":
            joined_reg.append(row)
        elif season_type == "POST":
            joined_post.append(row)
        else:
            conflicts.append(
                {
                    "game_id": gid,
                    "reason": "invented_or_unknown_season_type",
                    "season_type": season_type,
                }
            )

    if require_complete_season:
        ident_years = {int(r["season"]) for r in identities}
        covered = {r["game_id"] for r in identities}
        leftover = [
            gid
            for gid, row in games_by_id.items()
            if int(row["season"]) in ident_years and gid not in covered
        ]
        if leftover:
            unmatched.extend(
                {
                    "game_id": gid,
                    "season": int(games_by_id[gid]["season"]),
                    "week": int(games_by_id[gid]["week"]),
                    "season_type": None,
                    "home": games_by_id[gid]["home"],
                    "away": games_by_id[gid]["away"],
                    "missing": "identity_extract",
                }
                for gid in leftover
            )

    post_week_le_18 = [
        {"game_id": r["game_id"], "season": r["season"], "week": r["week"]}
        for r in joined_post
        if int(r["week"]) <= 18
    ]
    return {
        "schema_version": SCHEMA,
        "identity_source": identity_source,
        "n_identity": len(list(identities)),
        "n_reg": len(joined_reg),
        "n_post": len(joined_post),
        "n_unmatched": len(unmatched),
        "n_conflict": len(conflicts),
        "join_how": dict(Counter(r["join"] for r in joined_reg + joined_post)),
        "reg_by_season": dict(Counter(r["season"] for r in joined_reg)),
        "post_by_season": dict(Counter(r["season"] for r in joined_post)),
        "unmatched_examples": unmatched[:25],
        "unmatched_all": unmatched,
        "conflict_examples": conflicts[:25],
        "conflicts": conflicts,
        "post_week_le_18_examples": post_week_le_18,
        "n_post_week_le_18": len(post_week_le_18),
        "week_le_18_proxy": False,
        "silent_drop": False,
        "reg_rows": joined_reg,
        "post_rows": joined_post,
        "score_source": "outcomes_2013_2022_score_only.csv 50bda875",
        "kickoff_source": "games.csv 4fe1cdd7",
        "team_map": "existing PBP_TO_CANON / GAMES_TO_CANON / PRIOR_ALIAS composed",
        **LIMITATIONS,
    }


def _hold_payload(join: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "path_id": PATH_ID,
        "ticket": TICKET,
        "r5_history_id": R5_HISTORY_ID,
        "q2_leg": "HOLD",
        "hold_q2": True,
        "hold_reason": reason,
        "invented_history": False,
        "n_reg": join.get("n_reg"),
        "n_post": join.get("n_post"),
        "n_unmatched": join.get("n_unmatched"),
        "n_conflict": join.get("n_conflict"),
        "unmatched_examples": join.get("unmatched_examples") or [],
        "conflict_examples": join.get("conflict_examples") or [],
        "q2_2017_eval": "CLOSED",
        **LIMITATIONS,
    }


def _games_from_reg_rows(rows: Sequence[Mapping[str, Any]]) -> list[Game]:
    out = []
    for row in rows:
        out.append(
            Game(
                season=int(row["season"]),
                week=int(row["week"]),
                game_id=str(row["game_id"]),
                home=str(row["home"]),
                away=str(row["away"]),
                kickoff_utc=parse_kickoff(row["kickoff_utc"]),
                home_score=float(row["home_score"]),
                away_score=float(row["away_score"]),
                season_type="REG",
            )
        )
    return out


def freeze_history_ids(
    targets: Sequence[Mapping[str, Any]],
    history_games: Sequence[Game],
    *,
    proven_reg_ids: Sequence[str],
) -> dict[str, Any]:
    """Freeze choice + every history ID before forecasts."""
    rows = []
    for target in targets:
        game = Game(
            season=int(target["season"]),
            week=int(target["week"]),
            game_id=str(target["game_id"]),
            home=str(target["home"]),
            away=str(target["away"]),
            kickoff_utc=parse_kickoff(target["kickoff_utc"]),
            season_type="REG",
        )
        allowed = r5_history_for_target(
            history_games,
            game,
            proven_reg_ids=proven_reg_ids,
            proven_reg_years=PROVEN_Q2_YEARS,
        )
        ids = [g.game_id for g in allowed]
        rows.append(
            {
                "game_id": game.game_id,
                "season": game.season,
                "week": game.week,
                "n_history": len(ids),
                "history_ids": ids,
                "history_ids_sha256": sha256_text("\n".join(ids) + "\n"),
            }
        )
    all_ids = [row["game_id"] for row in rows]
    return {
        "schema_version": SCHEMA,
        "r5_history_id": R5_HISTORY_ID,
        "choice_frozen": True,
        "history_rule": {
            "name": "R5_REG_SCORE_HISTORY_V1",
            "r5_history_id": R5_HISTORY_ID,
            "disclose_not_old_kickoff_only_asof": True,
            "old_asof": "cf514078 kickoff strictly before target (same-week earlier games allowed)",
            "r5": (
                "approved 2013–2021 REG only; earlier seasons + strictly earlier "
                "NFL weeks; kickoff < KO-60; no same-week / own-target / later; "
                "no week<=18 REG proxy"
            ),
            "ko_minus_minutes": 60,
            "initial_prior_2013": None,
            "end_season_carry": 0.5,
            "carry_through": "complete canon REG",
        },
        "n_targets": len(rows),
        "game_ids": all_ids,
        "targets": rows,
        "choice_sha256": sha256_text(
            json.dumps(
                [(r["game_id"], r["history_ids_sha256"]) for r in rows],
                separators=(",", ":"),
            )
        ),
        **LIMITATIONS,
    }


def complete_q2_and_candidate(
    if_forecasts: Mapping[str, Any],
    history_id_freeze: Mapping[str, Any],
    history_games: Sequence[Game],
    *,
    proven_reg_ids: Sequence[str],
) -> dict[str, Any]:
    transfer = verify_q2_transfer_policy(proposed_refit=False)
    if_by = {str(row["game_id"]): row for row in if_forecasts["forecasts"]}
    hist_by = {str(row["game_id"]): row for row in history_id_freeze["targets"]}
    if set(if_by) != set(hist_by):
        raise HistoryIdRefuse("history-id target set != pinned IF496 identities")
    q2_rows: dict[str, dict[str, Any]] = {}
    forecasts = []
    history_lookup = {g.game_id: g for g in history_games}
    for gid in if_forecasts["game_ids"]:
        if_row = if_by[gid]
        hist_row = hist_by[gid]
        allowed = []
        for hid in hist_row["history_ids"]:
            game = history_lookup.get(hid)
            if game is None:
                raise HistoryIdRefuse(f"{gid} history id {hid} missing from canon REG")
            allowed.append(game)
        target = Game(
            season=int(if_row["season"]),
            week=int(if_row["week"]),
            game_id=gid,
            home=str(if_row["home"]),
            away=str(if_row["away"]),
            kickoff_utc=parse_kickoff(if_row["kickoff_utc"]),
            season_type="REG",
        )
        # Prove the frozen list still equals the live R5 filter.
        live = r5_history_for_target(
            history_games,
            target,
            proven_reg_ids=proven_reg_ids,
            proven_reg_years=PROVEN_Q2_YEARS,
        )
        live_ids = [g.game_id for g in live]
        if live_ids != list(hist_row["history_ids"]):
            raise HistoryIdRefuse(f"{gid} frozen history IDs drifted before forecast")
        feats = asof_for_targets(allowed, [target], initial_prior=None)
        assert_asof_no_self_target(allowed, feats)
        if not feats:
            raise HistoryIdRefuse(f"no Q2 as-of for {gid}")
        feat = feats[0]
        m_q2 = q2_pm_new(feat.rating_diff)
        m_if = float(if_row["m_if"])
        m_c = challenger_margin(m_if, m_q2, w=CANDIDATE_WEIGHT)
        q2_rows[gid] = {
            "game_id": gid,
            "m_q2": m_q2,
            "q2_status": "ok",
            "hold_reason": None,
            "history_ids_sha256": hist_row["history_ids_sha256"],
            "n_history": hist_row["n_history"],
            "rating_diff": feat.rating_diff,
            "n_asof_games": feat.n_asof_games,
        }
        forecasts.append(
            {
                "game_id": gid,
                "season": int(if_row["season"]),
                "week": int(if_row["week"]),
                "season_type": "REG",
                "home": if_row["home"],
                "away": if_row["away"],
                "kickoff_utc": if_row["kickoff_utc"],
                "split": "DEV",
                "m_if": m_if,
                "m_q2": m_q2,
                "m_candidate": m_c,
                "m_challenger": m_c,
                "candidate_formula": "0.5*IF+0.5*Q2",
                "candidate_weight": CANDIDATE_WEIGHT,
                "r3_weight_stopped": R3_WEIGHT_STOPPED,
                "if_status": if_row.get("if_status"),
                "if_label": if_row.get("if_label"),
                "q2_status": "ok",
                "q2_parameter_label": PARAMETER_LABEL,
                "q2_hold_reason": None,
                "history_ids_sha256": hist_row["history_ids_sha256"],
                "n_history": hist_row["n_history"],
                "rating_diff": feat.rating_diff,
                "n_asof_games": feat.n_asof_games,
                "seed": int(if_row["seed"]),
                "simulations": SIMULATIONS,
                "if_tip": IF_TIP,
                "simulator_sha256": SIM_SHA256,
                "framework_sha256": FW_SHA256,
                "blocked_legs": [],
                "label": LABEL_RECONSTRUCTED,
                "fit_label": LABEL_RETRO_FIT,
                "research_label": LABEL_RESEARCH,
                "cert_candidate": CERT_CANDIDATE,
                "eval": None,
                "scoring": None,
                "stage_c": None,
                "if_source": "pinned FORECASTS_DEV_R5_496.json 96d3aa6f — not regenerated",
            }
        )
    payload = {
        "schema_version": SCHEMA,
        "path_id": PATH_ID,
        "ticket": TICKET,
        "r5_history_id": R5_HISTORY_ID,
        "n_forecasts": len(forecasts),
        "n_if_finite": sum(1 for r in forecasts if r["m_if"] is not None),
        "n_q2_finite": sum(1 for r in forecasts if r["m_q2"] is not None),
        "n_q2_hold": 0,
        "n_candidate_finite": sum(1 for r in forecasts if r["m_candidate"] is not None),
        "if_tip": IF_TIP,
        "if_forecasts_sha256": IF_FORECASTS_SHA256,
        "if_regenerated": False,
        "simulator_sha256": SIM_SHA256,
        "framework_sha256": FW_SHA256,
        "simulations": SIMULATIONS,
        "candidate": "0.5*IF+0.5*Q2",
        "r3_stop": R3_STOP,
        "r3_weight_stopped": R3_WEIGHT_STOPPED,
        "a_q2": A_Q2,
        "b_q2": B_Q2,
        "ridge": LAMBDA,
        "prior_reg": REGRESS_FRAC,
        "initial_prior_2013": None,
        "transfer": transfer,
        "fit_policy": FIT_POLICY,
        "parameter_label": PARAMETER_LABEL,
        "history_rule": history_id_freeze["history_rule"],
        "history_choice_sha256": history_id_freeze["choice_sha256"],
        "q2_2017_eval": "CLOSED",
        "forecasts": forecasts,
        "game_ids": [r["game_id"] for r in forecasts],
        **LIMITATIONS,
    }
    if payload["n_forecasts"] != 496:
        raise HistoryIdRefuse(f"n_forecasts={payload['n_forecasts']} != 496")
    if payload["n_if_finite"] != 496 or payload["n_candidate_finite"] != 496:
        raise HistoryIdRefuse("completed freeze is not 496/496 IF+candidate")
    return payload


def refuse_phase2_score() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "refused": True,
        "phase2_score": False,
        "outcome_loader_reads": 0,
        "target_labels_loaded": 0,
        "reason": "t5157u R5-HISTORY-ID must not run Phase2 --score",
        "stop": "STOP_FOR_COS_B",
        **LIMITATIONS,
    }


def stop_for_cos_b(*, status: str, hold: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "stop": "STOP_FOR_COS_B",
        "ticket": TICKET,
        "owner_clear": OWNER_CLEAR,
        "r5_history_id": R5_HISTORY_ID,
        "cos_order_a": COS_ORDER_A,
        "parent_tip": PARENT_TIP,
        "parent_stamp": PARENT_STAMP,
        "status": status,
        "hold_q2": hold,
        "phase2_score": False,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "green": False,
        "hash6": False,
        "q2_2017_eval": "CLOSED",
        "preserve_market_intersection": {
            "n": 96,
            "bytes_sha256": INTERSECTION_BYTES_SHA256,
            "identity_sha256": INTERSECTION_IDENTITY_SHA256,
        },
        "preserve_if496": IF_FORECASTS_SHA256,
        "worker_b_owns": [
            "N1",
            "market intersection",
            "integration-owner combine",
        ],
        **LIMITATIONS,
    }


def run_history_id(
    *,
    root: Path | None = None,
    archive: Path | None = None,
    write: bool = True,
) -> dict[str, Any]:
    repo = _repo_root(root)
    hold_before = snapshot_hold_hashes(repo)
    archive_path = Path(archive) if archive is not None else DEFAULT_ARCHIVE
    if not archive_path.is_dir():
        raise HistoryIdRefuse(f"PBP archive missing {archive_path}")

    file_shas = verify_pbp_file_shas(archive_path)
    identity = project_identities_from_pbp(archive_path, file_shas=file_shas)
    games_path = _locate_pin(DEFAULT_GAMES_CANDIDATES, GAMES_SHA256, "games.csv")
    outcomes_path = _locate_pin(
        DEFAULT_OUTCOMES_CANDIDATES, OUTCOMES_SHA256, "outcomes 50bda875"
    )
    schedule_path = repo / SCHEDULE_PATH
    if sha256_file(schedule_path) != SCHEDULE_SHA256:
        raise HistoryIdRefuse("2020–21 REG schedule pin drifted")
    games_rows = _load_games_identity(games_path)
    outcomes_rows = _load_outcomes_score_only(outcomes_path)

    join_2013_19 = join_identities(
        identity["games"],
        games_rows,
        outcomes_rows,
        identity_source="pbp_identity_2013_2019",
        require_complete_season=True,
    )
    sched_ident = _load_schedule_reg_2020_2021(schedule_path)
    join_2020_21 = join_identities(
        sched_ident,
        games_rows,
        outcomes_rows,
        identity_source="schedule_results_2020_2023 REG 2020-21",
    )

    provenance = {
        "schema_version": SCHEMA,
        "r5_history_id": R5_HISTORY_ID,
        "pbp_2013_2019": {
            "n_reg": join_2013_19["n_reg"],
            "n_post": join_2013_19["n_post"],
            "n_unmatched": join_2013_19["n_unmatched"],
            "n_conflict": join_2013_19["n_conflict"],
            "join_how": join_2013_19["join_how"],
            "reg_by_season": join_2013_19["reg_by_season"],
            "post_by_season": join_2013_19["post_by_season"],
            "n_post_week_le_18": join_2013_19["n_post_week_le_18"],
            "unmatched_examples": join_2013_19["unmatched_examples"],
            "conflict_examples": join_2013_19["conflict_examples"],
            "post_week_le_18_examples": join_2013_19["post_week_le_18_examples"][:8],
        },
        "schedule_2020_2021_reg": {
            "n_reg": join_2020_21["n_reg"],
            "n_post": join_2020_21["n_post"],
            "n_unmatched": join_2020_21["n_unmatched"],
            "n_conflict": join_2020_21["n_conflict"],
            "join_how": join_2020_21["join_how"],
            "reg_by_season": join_2020_21["reg_by_season"],
            "unmatched_examples": join_2020_21["unmatched_examples"],
            "conflict_examples": join_2020_21["conflict_examples"],
        },
        "n_reg": join_2013_19["n_reg"] + join_2020_21["n_reg"],
        "n_post": join_2013_19["n_post"] + join_2020_21["n_post"],
        "n_unmatched": join_2013_19["n_unmatched"] + join_2020_21["n_unmatched"],
        "n_conflict": join_2013_19["n_conflict"] + join_2020_21["n_conflict"],
        "kickoff_source": "games.csv 4fe1cdd7 (not PBP start_time; start_time is naive)",
        "score_source": "outcomes 50bda875 score-only",
        "reg_membership_2013_2019": "PBP explicit season_type=REG",
        "reg_membership_2020_2021": "schedule_results_2020_2023.csv season_type=REG",
        "week_le_18_proxy": False,
        "disclose_not_old_kickoff_only_asof": True,
        **LIMITATIONS,
    }

    failed = (
        provenance["n_unmatched"] > 0
        or provenance["n_conflict"] > 0
        or join_2013_19["n_reg"] != 256 * 7
        or join_2020_21["n_reg"] != 256 + 272
    )
    if_path = repo / HOLD_DIR / IF_FORECASTS_NAME
    if_forecasts = json.loads(if_path.read_text(encoding="utf-8"))
    identities_496 = expected_profile_ids(PROFILE_FEATURE_RECON_REG496, repo)
    if437 = expected_profile_ids(PROFILE_DEV_IF437, repo)
    splits = split_scaffolding(identities_496, if437)
    if len(identities_496) != 496:
        raise HistoryIdRefuse("FEATURE_RECON_REG496 drifted")
    if splits["old437"]["n"] != 437 or splits["new59"]["n"] != 59:
        raise HistoryIdRefuse("old437/new59 split drifted")

    bundle: dict[str, Any] = {
        "SPEC": {
            "schema_version": SCHEMA,
            "path_id": PATH_ID,
            "ticket": TICKET,
            "owner_clear": OWNER_CLEAR,
            "r5_history_id": R5_HISTORY_ID,
            "cos_order_a": COS_ORDER_A,
            "parent_tip": PARENT_TIP,
            "parent_stamp": PARENT_STAMP,
            "if_forecasts_sha256": IF_FORECASTS_SHA256,
            "if_regenerated": False,
            "hold_artifacts_overwritten": False,
            "phase2_score": False,
            "q2_2017_eval": "CLOSED",
            "candidate": "0.5*IF+0.5*Q2",
            "r3_stop": R3_STOP,
            "labels": [LABEL_RECONSTRUCTED, LABEL_RETRO_FIT],
            "preserve_old437_new59_full496": True,
            "preserve_market_intersection": {
                "bytes_sha256": INTERSECTION_BYTES_SHA256,
                "identity_sha256": INTERSECTION_IDENTITY_SHA256,
            },
            **LIMITATIONS,
        },
        "PBP_FILE_SHA256": file_shas,
        "IDENTITY_FREEZE": {
            k: v
            for k, v in identity.items()
            if k != "games"
        }
        | {"n_identity_rows": identity["n_games"]},
        "JOIN_PROVENANCE": provenance,
        "SPLIT_SCAFFOLDING": splits,
        "SOURCE_PINS": {
            "schema_version": SCHEMA,
            "pins": {
                "if_forecasts": IF_FORECASTS_SHA256,
                "reg496_identity": REG496_IDENTITY_SHA256,
                "dev_if437_identity": DEV_IF437_IDENTITY_SHA256,
                "games": GAMES_SHA256,
                "outcomes": OUTCOMES_SHA256,
                "schedule": SCHEDULE_SHA256,
                "market_intersection_bytes": INTERSECTION_BYTES_SHA256,
                "market_intersection_identity": INTERSECTION_IDENTITY_SHA256,
                "r5_history_id": R5_HISTORY_ID,
                "parent_tip": PARENT_TIP,
            },
            "holds": {
                "R3_STOP": R3_STOP,
                "Q2_2017": "CLOSED",
                "HOLD_t5155u_not_overwritten": True,
                "IF496_not_regenerated": True,
                "Phase2_score": False,
            },
        },
        "SCORING_REFUSE": refuse_phase2_score(),
    }

    if failed:
        hold = _hold_payload(
            provenance,
            reason=(
                "Identity/join not bijective — HOLD Q2. No invented history. "
                f"unmatched={provenance['n_unmatched']} conflict={provenance['n_conflict']}"
            ),
        )
        bundle["Q2_COMPLETED_FREEZE"] = hold
        bundle["CANDIDATE_COMPLETED_FREEZE"] = hold
        bundle["HISTORY_IDS_FREEZE"] = {
            "schema_version": SCHEMA,
            "hold_q2": True,
            "invented_history": False,
            "r5_history_id": R5_HISTORY_ID,
        }
        bundle["FORECASTS_DEV_R5_496_Q2_COMPLETED"] = {
            "schema_version": SCHEMA,
            "hold_q2": True,
            "n_candidate_finite": 0,
            "if_forecasts_sha256": IF_FORECASTS_SHA256,
            "if_regenerated": False,
            **LIMITATIONS,
        }
        bundle["STOP_FOR_COS_B"] = stop_for_cos_b(status="HOLD", hold=True)
        bundle["IDENTITY_ROWS"] = identity["games"]
    else:
        history_rows = join_2013_19["reg_rows"] + join_2020_21["reg_rows"]
        history_games = _games_from_reg_rows(history_rows)
        proven_ids = [g.game_id for g in history_games]
        if len(proven_ids) != len(set(proven_ids)):
            raise HistoryIdRefuse("duplicate REG history ids")
        history_ids = freeze_history_ids(
            if_forecasts["forecasts"],
            history_games,
            proven_reg_ids=proven_ids,
        )
        completed = complete_q2_and_candidate(
            if_forecasts,
            history_ids,
            history_games,
            proven_reg_ids=proven_ids,
        )
        bundle["HISTORY_IDS_FREEZE"] = history_ids
        bundle["Q2_COMPLETED_FREEZE"] = {
            "schema_version": SCHEMA,
            "r5_history_id": R5_HISTORY_ID,
            "hold_q2": False,
            "n_q2_finite": completed["n_q2_finite"],
            "n_q2_hold": 0,
            "a_q2": A_Q2,
            "b_q2": B_Q2,
            "ridge": LAMBDA,
            "prior_reg": REGRESS_FRAC,
            "initial_prior_2013": None,
            "end_season_carry": 0.5,
            "history_choice_sha256": history_ids["choice_sha256"],
            "q2_2017_eval": "CLOSED",
            "rows": [
                {
                    "game_id": r["game_id"],
                    "m_q2": r["m_q2"],
                    "rating_diff": r["rating_diff"],
                    "n_history": r["n_history"],
                    "n_asof_games": r["n_asof_games"],
                    "history_ids_sha256": r["history_ids_sha256"],
                }
                for r in completed["forecasts"]
            ],
            **LIMITATIONS,
        }
        bundle["CANDIDATE_COMPLETED_FREEZE"] = {
            "schema_version": SCHEMA,
            "r5_history_id": R5_HISTORY_ID,
            "formula": "0.5*IF+0.5*Q2",
            "n_candidate_finite": completed["n_candidate_finite"],
            "if_forecasts_sha256": IF_FORECASTS_SHA256,
            "if_regenerated": False,
            "rows": [
                {
                    "game_id": r["game_id"],
                    "m_if": r["m_if"],
                    "m_q2": r["m_q2"],
                    "m_candidate": r["m_candidate"],
                }
                for r in completed["forecasts"]
            ],
            **LIMITATIONS,
        }
        bundle["FORECASTS_DEV_R5_496_Q2_COMPLETED"] = completed
        bundle["STOP_FOR_COS_B"] = stop_for_cos_b(status="IDENTITY_Q2_COMPLETE", hold=False)
        bundle["IDENTITY_ROWS"] = identity["games"]

    written: dict[str, str] = {}
    if write:
        dest_dir = repo / OUT_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        skip_inline = {"IDENTITY_ROWS"}
        for name, payload in bundle.items():
            if name in skip_inline:
                dest = dest_dir / "IDENTITY_ROWS.json"
                written["IDENTITY_ROWS"] = write_json(dest, {"rows": payload})
                continue
            dest = dest_dir / f"{name}.json"
            written[name] = write_json(dest, payload)
        manifest = {
            "schema_version": SCHEMA,
            "path_id": PATH_ID,
            "ticket": TICKET,
            "r5_history_id": R5_HISTORY_ID,
            "cos_order_a": COS_ORDER_A,
            "files": written,
            "n_reg_2013_2019": join_2013_19["n_reg"],
            "n_post_2013_2019": join_2013_19["n_post"],
            "n_unmatched": provenance["n_unmatched"],
            "n_conflict": provenance["n_conflict"],
            "n_forecasts": bundle["FORECASTS_DEV_R5_496_Q2_COMPLETED"].get("n_forecasts"),
            "n_q2_finite": bundle["FORECASTS_DEV_R5_496_Q2_COMPLETED"].get("n_q2_finite"),
            "n_candidate_finite": bundle["FORECASTS_DEV_R5_496_Q2_COMPLETED"].get(
                "n_candidate_finite"
            ),
            "if_forecasts_sha256": IF_FORECASTS_SHA256,
            "hold_q2": bool(bundle["STOP_FOR_COS_B"]["hold_q2"]),
            "stop": "STOP_FOR_COS_B",
            **LIMITATIONS,
        }
        written["FREEZE_MANIFEST"] = write_json(dest_dir / "FREEZE_MANIFEST.json", manifest)
        bundle["FREEZE_MANIFEST"] = manifest
    hold_after = assert_hold_unchanged(repo, hold_before)
    if sha256_file(repo / HOLD_DIR / IF_FORECASTS_NAME) != IF_FORECASTS_SHA256:
        raise HistoryIdRefuse("IF496 mutated during history-id run")
    bundle["written"] = written
    bundle["hold_hashes"] = hold_after
    return bundle


def refuse_target_scoring() -> dict[str, Any]:
    raise TargetScoringRefuse("t5157u refuses Phase2 --score / target scoring loader")
