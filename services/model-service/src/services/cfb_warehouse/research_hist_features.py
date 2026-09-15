"""Versioned historical raw features (2014–2025) — research restore only.

Applies #555 / #559 raw-metric definitions to SportsDataverse ``espn_cfb_pbp``
season parquets. Writes under ``data/cfb/research/pbp_hist/as_of_YYYYMMDD/``.

Never overwrites the Aug 13 canonical lake
``/Volumes/KosEdgeData/raw/cfb/pbp/`` (or the repo warehouse fallback).
Reconciles game counts to that inventory; play-count delta is reported when
the public restore copy differs from the HD snapshot.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.current_season_2026 import assert_not_historical_write
from src.services.cfb_warehouse.owned_metrics import (
    DEFINITIONS,
    METRIC_VERSION,
    audit_epa_success,
    league_rollups,
    team_game_raw_metrics,
)
from src.services.cfb_warehouse.owned_pbp import INVENTORY_EXPECTED as OWNED_INV
from src.services.cfb_warehouse.pbp import PBP_CORE_COLUMNS, PBP_TAG
from src.services.cfb_warehouse.paths import (
    HD_RAW_PBP,
    REPO_RAW_PBP,
    hd_mounted,
    hd_pbp_hist_research_target,
    pbp_hist_research_dir,
)
from src.services.cfb_warehouse.sdv import SDV_BASE, fetch_sdv_file
from src.services.cfb_warehouse.research_opp_adj import TeamGameEpa, aggregate_team_game_epa
from src.services.cfb_warehouse.team_game_w1_2026 import compose_team_game_table, core31_and_epa_null_rates

HIST_SEASONS = tuple(range(2014, 2026))
FEATURE_VERSION = "cfb-research-hist-raw-features-v1"


def asdict_game(game: TeamGameEpa) -> Dict[str, Any]:
    return {
        "season": game.season,
        "week": game.week,
        "game_id": game.game_id,
        "offense": game.offense,
        "defense": game.defense,
        "y": game.y,
        "n_plays": game.n_plays,
        "n_weighted": game.n_weighted,
        "home": game.home,
        "fcs_offense": game.fcs_offense,
        "fcs_defense": game.fcs_defense,
        "available_week": game.available_week,
        "success_rate": game.success_rate,
        "explosive_rate": game.explosive_rate,
        "pace_plays": game.pace_plays,
    }
SUCCESS_RATE_LABEL = "EPA_success = EPA>0"

# Aug 13 HD inventory (data/ops/cfb-historical-warehouse-v1-20260812-pbp-inventory.json).
INVENTORY_AS_OF = "2026-08-13"
INVENTORY_EXPECTED: Dict[int, Dict[str, int]] = {
    2014: {"plays": 155521, "games": 854},
    2015: {"plays": 158501, "games": 866},
    2016: {"plays": 155622, "games": 858},
    2017: {"plays": 155505, "games": 872},
    2018: {"plays": 158249, "games": 884},
    2019: {"plays": 156888, "games": 890},
    2020: {"plays": 100420, "games": 565},
    2021: {"plays": 146367, "games": 842},
    2022: {"plays": 149654, "games": 861},
    2023: {"plays": 153626, "games": 903},
    2024: {"plays": 162950, "games": 946},
    2025: {"plays": 165850, "games": 956},
}
INVENTORY_TOTAL_PLAYS = 1_819_153
INVENTORY_TOTAL_GAMES = 10_297
INVENTORY_2021_2024_PLAYS = 612_597
INVENTORY_2021_2024_GAMES = 3_552

# Extra columns needed for garbage / OT / home — read if present, never invented.
EXTRA_READ_COLS = (
    "period",
    "qtr",
    "quarter",
    "half",
    "neutral",
    "neutral_site",
    "home",
    "away",
    "pos_team_timeouts_remaining_before",
    "def_pos_team_timeouts_rem_before",
)

READ_COLS = tuple(dict.fromkeys(list(PBP_CORE_COLUMNS) + list(EXTRA_READ_COLS)))


def _sha256(path: Path, *, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def historical_path_convention(as_of: str) -> Dict[str, Any]:
    dest = pbp_hist_research_dir(as_of, prefer_hd=False)
    return {
        "as_of": as_of,
        "canonical_hd_lake": str(HD_RAW_PBP),
        "canonical_note": (
            "2014–2025 Aug 13 lake is CANONICAL SoT. Research restore is a "
            "versioned copy and must not overwrite those files."
        ),
        "hd_research_mirror": str(hd_pbp_hist_research_target(as_of)),
        "vm_research_path": str(dest),
        "repo_warehouse_fallback": str(REPO_RAW_PBP),
        "hd_mounted": hd_mounted(),
        "historical_lake_write": False,
        "versioning": "research/pbp_hist/as_of_YYYYMMDD/",
        "release_url_pattern": f"{SDV_BASE}/{PBP_TAG}/play_by_play_{{year}}.parquet",
    }


def restore_season_raw(season: int, dest_dir: Path, *, timeout: int = 300, force: bool = False) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    assert_not_historical_write(dest_dir)
    dest = dest_dir / f"play_by_play_{int(season)}.parquet"
    assert_not_historical_write(dest)
    if force and dest.exists():
        dest.unlink()
    return fetch_sdv_file(PBP_TAG, dest.name, cache_dir=dest_dir, timeout=timeout)


def load_season_frame(path: Path, *, columns: Sequence[str] = READ_COLS):
    import pandas as pd
    import pyarrow.parquet as pq

    available = set(pq.ParquetFile(path).schema.names)
    keep = [c for c in columns if c in available]
    return pd.read_parquet(path, columns=keep)


def inspect_and_reconcile(season: int, path: Path, df) -> Dict[str, Any]:
    gid = "game_id" if "game_id" in df.columns else None
    n_plays = int(len(df))
    n_games = int(df[gid].nunique(dropna=True)) if gid else None
    expected = INVENTORY_EXPECTED.get(int(season), {})
    play_delta = (n_plays - expected["plays"]) if expected and n_plays is not None else None
    game_delta = (n_games - expected["games"]) if expected and n_games is not None else None
    owned = OWNED_INV.get(int(season))
    return {
        "season": int(season),
        "plays": n_plays,
        "games": n_games,
        "columns": int(len(df.columns)),
        "column_names": [str(c) for c in df.columns],
        "bytes": int(path.stat().st_size),
        "sha256": _sha256(path),
        "inventory_as_of": INVENTORY_AS_OF,
        "inventory_plays": expected.get("plays"),
        "inventory_games": expected.get("games"),
        "play_delta_vs_aug13": play_delta,
        "game_delta_vs_aug13": game_delta,
        "games_match_aug13": game_delta == 0,
        "owned_metrics_inv_bytes": None if not owned else owned.get("bytes"),
        "duplicate_game_id": (
            int(df.duplicated(subset=[gid, "id"]).sum())
            if gid and "id" in df.columns
            else None
        ),
    }


def missing_data_report(df) -> Dict[str, Any]:
    out: Dict[str, Any] = {"n_rows": int(len(df)), "core31": {}, "extra": {}}
    for col in PBP_CORE_COLUMNS:
        if col not in df.columns:
            out["core31"][col] = {"present": False, "null_rate": None}
            continue
        out["core31"][col] = {
            "present": True,
            "null_rate": round(float(df[col].isna().mean()), 6),
        }
    for col in EXTRA_READ_COLS:
        if col not in df.columns:
            out["extra"][col] = {"present": False, "null_rate": None}
        else:
            out["extra"][col] = {
                "present": True,
                "null_rate": round(float(df[col].isna().mean()), 6),
            }
    present = [c for c, v in out["core31"].items() if v["present"]]
    out["core31_present_count"] = len(present)
    out["core31_absent"] = [c for c, v in out["core31"].items() if not v["present"]]
    return out


def build_season_features(
    season: int,
    df,
    *,
    inspect: Mapping[str, Any],
) -> Dict[str, Any]:
    records = df.to_dict(orient="records")
    for rec in records:
        gid = rec.get("game_id")
        if gid is not None:
            rec["game_id"] = str(gid).split(".")[0] if str(gid).endswith(".0") else str(gid)
    epa_audit = audit_epa_success(records)
    table = compose_team_game_table(records)
    epa_games = [asdict_game(g) for g in aggregate_team_game_epa(records)]
    field = core31_and_epa_null_rates(records)
    missing = missing_data_report(df)
    rollups = league_rollups(
        [
            {
                "success_rate": r.get("off_success_rate"),
                "standard_success_rate": r.get("off_standard_success_rate"),
                "epa_per_play": r.get("off_epa_per_play"),
                "explosive_rate": r.get("off_explosive_rate"),
                "pass_explosive_rate": r.get("off_pass_explosive_rate"),
                "rush_explosive_rate": r.get("off_rush_explosive_rate"),
                "early_success_rate": r.get("off_early_success_rate"),
                "standard_down_success_rate": r.get("off_standard_down_success_rate"),
                "passing_down_success_rate": r.get("off_passing_down_success_rate"),
            }
            for r in table
        ]
    )
    return {
        "season": int(season),
        "inspect": dict(inspect),
        "epa_audit": epa_audit,
        "field_stats": field,
        "missing_data": missing,
        "team_games": table,
        "epa_team_games": epa_games,
        "n_team_games": len(table),
        "n_epa_team_games": len(epa_games),
        "n_games": len({r["game_id"] for r in table}),
        "league_rollups": rollups,
        "success_rate_label": SUCCESS_RATE_LABEL,
        "metric_version": METRIC_VERSION,
        "feature_version": FEATURE_VERSION,
        "opponent_adjusted": False,
        "definitions": {
            "success_rate": DEFINITIONS["success_rate"],
            "standard_success_rate": DEFINITIONS["standard_success_rate"],
            "epa_per_play": DEFINITIONS["epa_per_play"],
            "explosive_rate": DEFINITIONS["explosive_rate"],
        },
    }


def restore_and_build(
    *,
    as_of: str,
    seasons: Sequence[int] = HIST_SEASONS,
    dest_dir: Optional[Path] = None,
    allow_fetch: bool = True,
    write_artifacts: bool = True,
) -> Dict[str, Any]:
    dest = Path(dest_dir) if dest_dir is not None else pbp_hist_research_dir(as_of)
    dest.mkdir(parents=True, exist_ok=True)
    assert_not_historical_write(dest)

    by_season: Dict[str, Any] = {}
    checksums: Dict[str, Any] = {}
    all_team_games: List[Dict[str, Any]] = []
    all_epa_games: List[Dict[str, Any]] = []
    epa_audits: Dict[str, Any] = {}
    missing_reports: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    for season in seasons:
        try:
            raw_path = dest / f"play_by_play_{int(season)}.parquet"
            if not raw_path.exists():
                if not allow_fetch:
                    raise FileNotFoundError(str(raw_path))
                raw_path = restore_season_raw(int(season), dest)
            assert_not_historical_write(raw_path)
            df = load_season_frame(raw_path)
            inspect = inspect_and_reconcile(int(season), raw_path, df)
            built = build_season_features(int(season), df, inspect=inspect)
            by_season[str(season)] = {
                "status": "ok",
                **{k: v for k, v in built.items() if k != "team_games"},
            }
            all_team_games.extend(built["team_games"])
            all_epa_games.extend(built.get("epa_team_games") or [])
            epa_audits[str(season)] = built["epa_audit"]
            missing_reports[str(season)] = built["missing_data"]
            checksums[str(season)] = {
                "path": str(raw_path),
                "sha256": inspect["sha256"],
                "bytes": inspect["bytes"],
                "plays": inspect["plays"],
                "games": inspect["games"],
                "play_delta_vs_aug13": inspect["play_delta_vs_aug13"],
                "game_delta_vs_aug13": inspect["game_delta_vs_aug13"],
            }
            if write_artifacts:
                _write_season_outputs(dest, int(season), built)
        except Exception as exc:  # noqa: BLE001
            errors[str(season)] = str(exc)[:400]
            by_season[str(season)] = {"status": "failed", "error": str(exc)[:400]}

    hist_21_24 = [s for s in seasons if 2021 <= int(s) <= 2024]
    obs_plays = sum(int((checksums.get(str(s)) or {}).get("plays") or 0) for s in seasons)
    obs_games = sum(int((checksums.get(str(s)) or {}).get("games") or 0) for s in seasons)
    obs_21_24_plays = sum(int((checksums.get(str(s)) or {}).get("plays") or 0) for s in hist_21_24)
    obs_21_24_games = sum(int((checksums.get(str(s)) or {}).get("games") or 0) for s in hist_21_24)

    inventory = {
        "feature_version": FEATURE_VERSION,
        "metric_version": METRIC_VERSION,
        "success_rate_label": SUCCESS_RATE_LABEL,
        "research_only": True,
        "opponent_adjusted": False,
        "not_ke_ratings": True,
        "as_of": as_of,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "path_convention": historical_path_convention(as_of),
        "seasons": list(seasons),
        "checksums": checksums,
        "errors": errors,
        "totals": {
            "plays": obs_plays,
            "games": obs_games,
            "team_games": len(all_team_games),
            "inventory_plays": INVENTORY_TOTAL_PLAYS,
            "inventory_games": INVENTORY_TOTAL_GAMES,
            "play_delta_vs_aug13": obs_plays - INVENTORY_TOTAL_PLAYS if checksums else None,
            "game_delta_vs_aug13": obs_games - INVENTORY_TOTAL_GAMES if checksums else None,
        },
        "reconcile_2021_2024": {
            "inventory_plays": INVENTORY_2021_2024_PLAYS,
            "inventory_games": INVENTORY_2021_2024_GAMES,
            "observed_plays": obs_21_24_plays,
            "observed_games": obs_21_24_games,
            "play_delta": obs_21_24_plays - INVENTORY_2021_2024_PLAYS,
            "game_delta": obs_21_24_games - INVENTORY_2021_2024_GAMES,
            "games_match": obs_21_24_games == INVENTORY_2021_2024_GAMES,
            "note": (
                "HD SoT is 612,597 plays / 3,552 games. A later SDV copy may "
                "add plays; game-count match is the reconcile gate."
            ),
        },
        "epa_audits": epa_audits,
        "missing_data": missing_reports,
        "by_season": {
            k: {sk: sv for sk, sv in v.items() if sk not in {"inspect"}}
            for k, v in by_season.items()
        },
        "cfbd_used": False,
        "historical_lake_write": False,
    }

    if write_artifacts:
        (dest / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
        (dest / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n")
        (dest / "missing_data.json").write_text(json.dumps(missing_reports, indent=2) + "\n")
        (dest / "epa_audits.json").write_text(json.dumps(epa_audits, indent=2) + "\n")
        try:
            import pandas as pd

            pd.DataFrame(all_team_games).to_parquet(
                dest / "team_game_raw_unadjusted.parquet", index=False
            )
            if all_epa_games:
                pd.DataFrame(all_epa_games).to_parquet(
                    dest / "team_game_epa_eligible.parquet", index=False
                )
        except Exception:  # noqa: BLE001
            (dest / "team_game_raw_unadjusted.json").write_text(
                json.dumps(all_team_games) + "\n"
            )
        assert_not_historical_write(dest / "inventory.json")

    return {
        "inventory": inventory,
        "team_games": all_team_games,
        "epa_team_games": all_epa_games,
        "dest": str(dest),
        "by_season": by_season,
    }


def _write_season_outputs(dest: Path, season: int, built: Mapping[str, Any]) -> None:
    season_dir = dest / f"season_{int(season)}"
    season_dir.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in built.items() if k not in {"team_games", "epa_team_games"}}
    (season_dir / "summary.json").write_text(json.dumps(slim, indent=2) + "\n")
    try:
        import pandas as pd

        pd.DataFrame(built["team_games"]).to_parquet(
            season_dir / "team_game_raw_unadjusted.parquet", index=False
        )
        if built.get("epa_team_games"):
            pd.DataFrame(built["epa_team_games"]).to_parquet(
                season_dir / "team_game_epa_eligible.parquet", index=False
            )
    except Exception:  # noqa: BLE001
        (season_dir / "team_game_raw_unadjusted.json").write_text(
            json.dumps(built["team_games"]) + "\n"
        )


def load_restored_epa_games(dest: Path) -> List[Dict[str, Any]]:
    parquet = dest / "team_game_epa_eligible.parquet"
    if parquet.exists():
        import pandas as pd

        return pd.read_parquet(parquet).to_dict(orient="records")
    rows: List[Dict[str, Any]] = []
    for child in sorted(dest.glob("season_*/team_game_epa_eligible.parquet")):
        import pandas as pd

        rows.extend(pd.read_parquet(child).to_dict(orient="records"))
    return rows


def rows_to_team_game_epa(rows: Sequence[Mapping[str, Any]]) -> List[TeamGameEpa]:
    out: List[TeamGameEpa] = []
    for r in rows:
        out.append(
            TeamGameEpa(
                season=int(r["season"]),
                week=int(r["week"]),
                game_id=str(r["game_id"]),
                offense=str(r["offense"]),
                defense=str(r["defense"]),
                y=float(r["y"]),
                n_plays=int(r["n_plays"]),
                n_weighted=float(r["n_weighted"]),
                home=float(r.get("home") or 0.0),
                fcs_offense=bool(r.get("fcs_offense")),
                fcs_defense=bool(r.get("fcs_defense")),
                available_week=int(r.get("available_week") or r["week"]),
                success_rate=r.get("success_rate"),
                explosive_rate=r.get("explosive_rate"),
                pace_plays=r.get("pace_plays"),
            )
        )
    return out


def load_restored_team_games(dest: Path) -> List[Dict[str, Any]]:
    parquet = dest / "team_game_raw_unadjusted.parquet"
    if parquet.exists():
        import pandas as pd

        return pd.read_parquet(parquet).to_dict(orient="records")
    js = dest / "team_game_raw_unadjusted.json"
    if js.exists():
        return json.loads(js.read_text())
    rows: List[Dict[str, Any]] = []
    for child in sorted(dest.glob("season_*/team_game_raw_unadjusted.parquet")):
        import pandas as pd

        rows.extend(pd.read_parquet(child).to_dict(orient="records"))
    return rows
