"""Neutral-site / venue identity helpers for Lab research (Train-A).

Authoritative venue source for Lab fair challengers that gate HCA:
  Schedule SoT packs (`ncaam_official_schedule_YYYY_YY.json`) field `neutral_site`.

This module does NOT read sealed holdout packages, Test-A frames, or pocket data.
Fail-closed: missing / ambiguous / conflicting keys never become home or neutral.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import polars as pl

from ncaam_lab.holdout_2425.venue_contract import normalize_venue_status

VENUE_STATUS_HOME = "confirmed_home"
VENUE_STATUS_NEUTRAL = "confirmed_neutral"
VENUE_STATUS_UNKNOWN = "unknown"

IDENTITY_SCHEMA_VERSION = "ncaam-neutral-site-identity-v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_train_a_schedule_packs() -> List[Path]:
    """Train-A tip window packs only (2022-23 + 2023-24). No 2024-25 holdout pack."""
    base = (
        _repo_root()
        / "services"
        / "model-service"
        / "src"
        / "services"
        / "ncaam_schedule"
        / "data"
    )
    return [
        base / "ncaam_official_schedule_2022_23.json",
        base / "ncaam_official_schedule_2023_24.json",
    ]


def assert_no_holdout_or_test_a_paths(paths: Sequence[Path]) -> None:
    """Hard refuse sealed holdout / Test-A / pocket artifact paths."""
    forbidden_tokens = (
        "holdout_2024_25",
        "holdout_2425",
        "test_a",
        "test-a",
        "pocket_2025",
        "pocket-2025",
        "ncaam_official_schedule_2024_25",
        "ncaam-fair-lab-test_a",
    )
    for p in paths:
        s = str(p).replace("\\", "/").lower()
        for tok in forbidden_tokens:
            if tok in s:
                raise ValueError(
                    f"neutral_site_identity refuses path touching {tok!r}: {p}"
                )


def classify_venue_status(
    *,
    neutral_site_raw: Optional[bool],
    venue_name: Optional[str] = None,
    home_team_id: Optional[str] = None,
    season_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Map raw SoT flag → venue_status via the Phase 2.6 venue contract.

    Tournament / multi-team events are NOT auto-neutral; designated home is NOT
    auto home-court when postseason venue token conflicts (→ unknown).
    """
    return normalize_venue_status(
        neutral_site_raw=neutral_site_raw,
        venue_name=venue_name,
        home_team_id=home_team_id,
        season_type=season_type,
    )


def load_schedule_venue_rows(
    pack_paths: Optional[Sequence[Path]] = None,
) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Load unique (tip_date, home, away) venue rows; drop ambiguous keys."""
    paths = (
        list(pack_paths)
        if pack_paths is not None
        else default_train_a_schedule_packs()
    )
    assert_no_holdout_or_test_a_paths(paths)

    rows: List[Dict[str, Any]] = []
    key_counts: Dict[Tuple[str, str, str], int] = {}
    receipt: Dict[str, Any] = {
        "schema_version": IDENTITY_SCHEMA_VERSION,
        "authoritative_source": "espn_scoreboard_public_via_schedule_sot_packs",
        "raw_field": "neutral_site",
        "packs": [],
        "n_ambiguous_keys_dropped": 0,
        "known_limitations": [
            "semi-home tournaments may be labeled neutral inconsistently upstream",
            "mislabeled_neutral risk inherited from ESPN scoreboard",
            "pack as_of is retrospective pack-build time, not game-time PIT stamp",
            "renamed venues / relocated games inherit pack snapshot only",
        ],
    }

    for path in paths:
        info: Dict[str, Any] = {
            "path": str(path),
            "exists": path.exists(),
        }
        if not path.exists():
            receipt["packs"].append(info)
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        games = blob.get("games") or []
        info.update(
            {
                "as_of": blob.get("as_of"),
                "source": blob.get("source"),
                "n_games": len(games),
                "n_with_neutral_flag": sum(1 for g in games if "neutral_site" in g),
            }
        )
        for g in games:
            tip_raw = str(g.get("tipoff") or g.get("date") or "")[:10]
            try:
                tip = date.fromisoformat(tip_raw)
            except ValueError:
                continue
            hid = str(g.get("home") or "").strip().lower()
            aid = str(g.get("away") or "").strip().lower()
            if not hid or not aid or "neutral_site" not in g:
                continue
            key = (tip.isoformat(), hid, aid)
            key_counts[key] = key_counts.get(key, 0) + 1
            norm = classify_venue_status(
                neutral_site_raw=bool(g["neutral_site"]),
                venue_name=g.get("venue"),
                home_team_id=hid,
                season_type=g.get("season_type"),
            )
            rows.append(
                {
                    "tip_date": tip,
                    "home_team_id": hid,
                    "away_team_id": aid,
                    "neutral_site_raw": bool(g["neutral_site"]),
                    "venue_status": norm["venue_status"],
                    "venue_name": g.get("venue"),
                    "season_type": g.get("season_type"),
                    "conflict_reason": norm.get("conflict_reason"),
                    "source_pack": path.name,
                }
            )
        receipt["packs"].append(info)

    amb = sum(1 for c in key_counts.values() if c > 1)
    receipt["n_ambiguous_keys_dropped"] = int(amb)
    clean = [
        r
        for r in rows
        if key_counts[
            (r["tip_date"].isoformat(), r["home_team_id"], r["away_team_id"])
        ]
        == 1
    ]
    if not clean:
        empty = pl.DataFrame(
            schema={
                "tip_date": pl.Date,
                "home_team_id": pl.Utf8,
                "away_team_id": pl.Utf8,
                "neutral_site_raw": pl.Boolean,
                "venue_status": pl.Utf8,
                "venue_name": pl.Utf8,
                "season_type": pl.Utf8,
                "conflict_reason": pl.Utf8,
                "source_pack": pl.Utf8,
            }
        )
        return empty, receipt
    # Explicit schema: conflict_reason is often null (mixed None/str breaks infer).
    return (
        pl.DataFrame(
            {
                "tip_date": [r["tip_date"] for r in clean],
                "home_team_id": [r["home_team_id"] for r in clean],
                "away_team_id": [r["away_team_id"] for r in clean],
                "neutral_site_raw": [r["neutral_site_raw"] for r in clean],
                "venue_status": [r["venue_status"] for r in clean],
                "venue_name": [r.get("venue_name") for r in clean],
                "season_type": [r.get("season_type") for r in clean],
                "conflict_reason": [r.get("conflict_reason") for r in clean],
                "source_pack": [r.get("source_pack") for r in clean],
            },
            schema={
                "tip_date": pl.Date,
                "home_team_id": pl.Utf8,
                "away_team_id": pl.Utf8,
                "neutral_site_raw": pl.Boolean,
                "venue_status": pl.Utf8,
                "venue_name": pl.Utf8,
                "season_type": pl.Utf8,
                "conflict_reason": pl.Utf8,
                "source_pack": pl.Utf8,
            },
        ),
        receipt,
    )


def attach_venue_status(
    games: pl.DataFrame,
    *,
    pack_paths: Optional[Sequence[Path]] = None,
) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Left-join venue_status onto Lab games. Null join → unknown (never coerced)."""
    if pack_paths is not None:
        assert_no_holdout_or_test_a_paths(pack_paths)
    venue, receipt = load_schedule_venue_rows(pack_paths)
    required = {"tip_date", "home_team_id", "away_team_id"}
    missing = required - set(games.columns)
    if missing:
        raise ValueError(f"attach_venue_status missing columns: {sorted(missing)}")

    left = games.with_columns(
        [
            pl.col("home_team_id").cast(pl.Utf8).str.to_lowercase().alias("home_team_id"),
            pl.col("away_team_id").cast(pl.Utf8).str.to_lowercase().alias("away_team_id"),
            pl.col("tip_date").cast(pl.Date).alias("tip_date"),
        ]
    )
    if venue.height == 0:
        out = left.with_columns(
            [
                pl.lit(None).cast(pl.Boolean).alias("neutral_site_raw"),
                pl.lit(VENUE_STATUS_UNKNOWN).alias("venue_status"),
                pl.lit(None).cast(pl.Utf8).alias("venue_conflict_reason"),
            ]
        )
        receipt["n_joined_nonnull"] = 0
        receipt["n_unknown"] = int(out.height)
        return out, receipt

    join_cols = [
        "tip_date",
        "home_team_id",
        "away_team_id",
        "neutral_site_raw",
        "venue_status",
        "conflict_reason",
    ]
    out = left.join(
        venue.select(join_cols),
        on=["tip_date", "home_team_id", "away_team_id"],
        how="left",
    ).with_columns(
        [
            pl.when(pl.col("venue_status").is_null())
            .then(pl.lit(VENUE_STATUS_UNKNOWN))
            .otherwise(pl.col("venue_status"))
            .alias("venue_status"),
            pl.col("conflict_reason").alias("venue_conflict_reason"),
        ]
    ).drop("conflict_reason")

    receipt["n_joined_nonnull"] = int(
        out.filter(pl.col("neutral_site_raw").is_not_null()).height
    )
    receipt["n_confirmed_home"] = int(
        out.filter(pl.col("venue_status") == VENUE_STATUS_HOME).height
    )
    receipt["n_confirmed_neutral"] = int(
        out.filter(pl.col("venue_status") == VENUE_STATUS_NEUTRAL).height
    )
    receipt["n_unknown"] = int(
        out.filter(pl.col("venue_status") == VENUE_STATUS_UNKNOWN).height
    )
    return out, receipt
