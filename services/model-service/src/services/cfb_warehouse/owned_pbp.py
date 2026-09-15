"""Research loader for owned SportsDataverse CFB PBP (raw + core).

Prefers ``/Volumes/KosEdgeData``. Falls back to gitignored
``data/cfb/warehouse``. Optional restore uses the same SportsDataverse
release already documented as owned — not a new vendor.

Does not fit a model. Does not opponent-adjust. Does not write KE ratings.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.services.cfb_warehouse.pbp import PBP_CORE_COLUMNS, PBP_TAG
from src.services.cfb_warehouse.paths import (
    HD_CLEAN,
    HD_RAW_PBP,
    REPO_CLEAN,
    REPO_RAW_PBP,
    hd_mounted,
)
from src.services.cfb_warehouse.sdv import SDV_BASE, fetch_sdv_file

OWNED_HIST_SEASONS = (2021, 2022, 2023, 2024)
VALIDATE_UNLOCK_SEASON = 2025

# Committed 2026-08-13 HD inventory (data/ops/cfb-historical-warehouse-v1-20260812-pbp-inventory.json).
INVENTORY_AS_OF = "2026-08-13"
INVENTORY_SOURCE = "sportsdataverse espn_cfb_pbp (load_cfb_pbp)"
INVENTORY_EXPECTED: Dict[int, Dict[str, int]] = {
    2021: {"plays": 146367, "games": 842, "raw_cols": 477, "bytes": 48771364},
    2022: {"plays": 149654, "games": 861, "raw_cols": 477, "bytes": 49703907},
    2023: {"plays": 153626, "games": 903, "raw_cols": 477, "bytes": 50724205},
    2024: {"plays": 162950, "games": 946, "raw_cols": 477, "bytes": 55106146},
    2025: {"plays": 165850, "games": 956, "raw_cols": 476, "bytes": 59265929},
}
INVENTORY_HIST_PLAYS = 612597
INVENTORY_HIST_GAMES = 3552


@dataclass(frozen=True)
class SeasonFiles:
    season: int
    raw_path: Optional[str]
    core_path: Optional[str]
    source: str  # hd | repo_fallback | missing


def _raw_name(season: int) -> str:
    return f"play_by_play_{int(season)}.parquet"


def _core_name(season: int) -> str:
    return f"pbp_{int(season)}_core.parquet"


def locate_season(season: int, *, prefer_hd: bool = True) -> SeasonFiles:
    """Resolve raw/core paths. Does not download."""
    if prefer_hd and hd_mounted():
        raw = HD_RAW_PBP / _raw_name(season)
        core = HD_CLEAN / "pbp" / _core_name(season)
        if raw.exists() or core.exists():
            return SeasonFiles(
                season=int(season),
                raw_path=str(raw) if raw.exists() else None,
                core_path=str(core) if core.exists() else None,
                source="hd",
            )
    raw = REPO_RAW_PBP / _raw_name(season)
    core = REPO_CLEAN / "pbp" / _core_name(season)
    if raw.exists() or core.exists():
        return SeasonFiles(
            season=int(season),
            raw_path=str(raw) if raw.exists() else None,
            core_path=str(core) if core.exists() else None,
            source="repo_fallback",
        )
    return SeasonFiles(season=int(season), raw_path=None, core_path=None, source="missing")


def sha256_file(path: Path, *, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def restore_raw(
    season: int,
    *,
    dest_dir: Optional[Path] = None,
    timeout: int = 300,
) -> Path:
    """Download-once the already-owned SDV release into dest_dir (default repo fallback)."""
    dest_dir = dest_dir or REPO_RAW_PBP
    return fetch_sdv_file(PBP_TAG, _raw_name(season), cache_dir=dest_dir, timeout=timeout)


def write_core_from_raw(raw_path: Path, dest: Path) -> Path:
    import pandas as pd

    df = pd.read_parquet(raw_path)
    keep = [c for c in PBP_CORE_COLUMNS if c in df.columns]
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.loc[:, keep].to_parquet(dest, index=False)
    return dest


def _truthy(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw in (None, "", 0, "0"):
        return False
    if isinstance(raw, float) and raw != raw:  # NaN
        return False
    return str(raw).lower() in {"1", "true", "t", "yes"}


def _missing_rate(series) -> Optional[float]:
    n = int(len(series))
    if n == 0:
        return None
    return round(float(series.isna().mean()), 6)


def inspect_season_frame(
    df,
    *,
    season: int,
    layer: str,
) -> Dict[str, Any]:
    """Coverage / dups / missingness for one parquet frame. No synthetic fill."""
    cols = [str(c) for c in df.columns]
    n = int(len(df))
    gid_col = "game_id" if "game_id" in df.columns else None
    id_col = "id" if "id" in df.columns else None
    n_games = int(df[gid_col].nunique(dropna=True)) if gid_col else None
    dup_id = int(df.duplicated(subset=[id_col]).sum()) if id_col else None
    dup_game_id = (
        int(df.duplicated(subset=[gid_col, id_col]).sum())
        if gid_col and id_col
        else None
    )
    missing: Dict[str, Optional[float]] = {}
    for col in PBP_CORE_COLUMNS:
        if col in df.columns:
            missing[col] = _missing_rate(df[col])
        else:
            missing[col] = None
    season_vals = sorted({int(x) for x in df["season"].dropna().unique()}) if "season" in df.columns else []
    return {
        "layer": layer,
        "season_requested": int(season),
        "seasons_in_file": season_vals,
        "plays": n,
        "games": n_games,
        "columns": len(cols),
        "column_names": cols if layer == "core" or len(cols) <= 40 else None,
        "column_names_head": cols[:40],
        "duplicate_id": dup_id,
        "duplicate_game_id": dup_game_id,
        "missing_core": missing,
        "core_columns_present": [c for c in PBP_CORE_COLUMNS if c in df.columns],
        "core_columns_absent": [c for c in PBP_CORE_COLUMNS if c not in df.columns],
    }


def inspect_files(files: SeasonFiles) -> Dict[str, Any]:
    import pandas as pd

    out: Dict[str, Any] = {
        "season": files.season,
        "source": files.source,
        "raw_path": files.raw_path,
        "core_path": files.core_path,
        "raw_sha256": None,
        "core_sha256": None,
        "raw_bytes": None,
        "core_bytes": None,
        "raw": None,
        "core": None,
        "raw_vs_core": None,
    }
    if files.raw_path:
        raw_p = Path(files.raw_path)
        out["raw_bytes"] = int(raw_p.stat().st_size)
        out["raw_sha256"] = sha256_file(raw_p)
        raw_df = pd.read_parquet(raw_p)
        out["raw"] = inspect_season_frame(raw_df, season=files.season, layer="raw")
    if files.core_path:
        core_p = Path(files.core_path)
        out["core_bytes"] = int(core_p.stat().st_size)
        out["core_sha256"] = sha256_file(core_p)
        core_df = pd.read_parquet(core_p)
        out["core"] = inspect_season_frame(core_df, season=files.season, layer="core")
    if out["raw"] and out["core"]:
        out["raw_vs_core"] = {
            "play_delta": int(out["raw"]["plays"]) - int(out["core"]["plays"]),
            "game_delta": (
                None
                if out["raw"]["games"] is None or out["core"]["games"] is None
                else int(out["raw"]["games"]) - int(out["core"]["games"])
            ),
        }
    return out


def reconcile_to_inventory(inspected: Mapping[str, Any]) -> Dict[str, Any]:
    season = int(inspected["season"])
    expected = INVENTORY_EXPECTED.get(season)
    raw = inspected.get("raw") or {}
    if not expected:
        return {"status": "no_inventory_row", "season": season}
    play_delta = (raw.get("plays") - expected["plays"]) if raw.get("plays") is not None else None
    game_delta = (raw.get("games") - expected["games"]) if raw.get("games") is not None else None
    col_delta = (raw.get("columns") - expected["raw_cols"]) if raw.get("columns") is not None else None
    byte_delta = (
        (inspected.get("raw_bytes") - expected["bytes"])
        if inspected.get("raw_bytes") is not None
        else None
    )
    match = (
        play_delta == 0
        and game_delta == 0
        and col_delta == 0
        and byte_delta == 0
    )
    return {
        "season": season,
        "inventory_as_of": INVENTORY_AS_OF,
        "expected": expected,
        "observed_plays": raw.get("plays"),
        "observed_games": raw.get("games"),
        "observed_raw_cols": raw.get("columns"),
        "observed_bytes": inspected.get("raw_bytes"),
        "play_delta": play_delta,
        "game_delta": game_delta,
        "col_delta": col_delta,
        "byte_delta": byte_delta,
        "exact_match": match,
        "status": "match" if match else "drift_or_different_copy",
    }


def load_core_records(
    season: int,
    *,
    prefer_hd: bool = True,
    columns: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Load one season as records from core, else raw core-subset."""
    import pandas as pd

    files = locate_season(season, prefer_hd=prefer_hd)
    path = files.core_path or files.raw_path
    if not path:
        raise FileNotFoundError(
            f"Owned PBP missing for {season} (hd_mounted={hd_mounted()})"
        )
    want = list(columns) if columns else list(PBP_CORE_COLUMNS)
    df = pd.read_parquet(path)
    keep = [c for c in want if c in df.columns]
    return df.loc[:, keep].to_dict(orient="records")


def ensure_season(
    season: int,
    *,
    prefer_hd: bool = True,
    allow_fetch: bool = False,
) -> SeasonFiles:
    files = locate_season(season, prefer_hd=prefer_hd)
    if files.source != "missing":
        if files.raw_path and not files.core_path:
            dest = Path(files.raw_path).parent
            # core lives under clean/pbp
            core_dest = (
                (HD_CLEAN / "pbp" / _core_name(season))
                if files.source == "hd"
                else (REPO_CLEAN / "pbp" / _core_name(season))
            )
            write_core_from_raw(Path(files.raw_path), core_dest)
            return locate_season(season, prefer_hd=prefer_hd)
        return files
    if not allow_fetch:
        return files
    raw = restore_raw(season)
    core_dest = REPO_CLEAN / "pbp" / _core_name(season)
    write_core_from_raw(raw, core_dest)
    return locate_season(season, prefer_hd=False)


def hist_totals(seasons: Iterable[int] = OWNED_HIST_SEASONS) -> Dict[str, int]:
    exp_plays = sum(INVENTORY_EXPECTED[s]["plays"] for s in seasons)
    exp_games = sum(INVENTORY_EXPECTED[s]["games"] for s in seasons)
    return {"plays": exp_plays, "games": exp_games}


def provenance_block() -> Dict[str, Any]:
    return {
        "source": INVENTORY_SOURCE,
        "release_tag": PBP_TAG,
        "release_url_pattern": f"{SDV_BASE}/{PBP_TAG}/play_by_play_{{year}}.parquet",
        "inventory_as_of": INVENTORY_AS_OF,
        "hd_root": str(HD_RAW_PBP),
        "repo_fallback_raw": str(REPO_RAW_PBP),
        "hd_mounted": hd_mounted(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Checksums are of the file bytes actually read. A restore copy may differ from the 2026-08-13 HD ingest.",
    }


def files_as_dict(files: SeasonFiles) -> Dict[str, Any]:
    return asdict(files)
