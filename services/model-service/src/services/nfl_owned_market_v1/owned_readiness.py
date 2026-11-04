"""OWNED_MARKET_TRACE_V1 readiness. CERT=0.

Names actual original git locators at 7834cbc7 — not invented destinations.
Projects 2020–21 selected-187 identities before quote-value exposure.
Does not invent clock fields or missingness causes. No Cos staging.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    CERT,
    PACKAGE,
    PIN_ADMISSIBLE_PATH,
    PIN_ADMISSIBLE_SHA256,
    PIN_FREEZE_PATH,
    PIN_INTERSECTION_N,
    PIN_MISSING_N,
    PIN_OWNED_HISTORY,
    PIN_REG496_IDENTITY_SHA256,
    PIN_REG496_N,
    PIN_SELECTED_187,
    PROFILE_OWNED_MARKET_TRACE,
    ROLE_OWNED_READINESS,
    SCHEMA_OWNED_MARKET_TRACE,
)
from src.services.nfl_owned_market_v1.hashing import canonical_sha256
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse

IDENTITY_ONLY_FIELDS: tuple[str, ...] = (
    "game_id",
    "season",
    "week",
    "book",
    "market",
    "source",
)
FORBIDDEN_VALUE_FIELDS: frozenset[str] = frozenset(
    {
        "line",
        "price",
        "price_home",
        "price_away",
        "spread_home",
        "home_margin",
        "total_points",
        "age_hours",
    }
)
CLOCK_FIELDS_ON_ORIGINAL: tuple[str, ...] = (
    "captured_at",
    "cutoff_utc",
    "kickoff_utc",
)

ORIGINAL_LOCATORS: tuple[dict[str, str], ...] = (
    {
        "id": "admissible_quotes_b1",
        "commit": PIN_OWNED_HISTORY,
        "path": PIN_ADMISSIBLE_PATH,
        "field": "jsonl rows (B1 admissible quotes; Cos-verified sha256)",
        "need": "original owned quote universe for 2020–21 identity projection",
        "expected_sha256": PIN_ADMISSIBLE_SHA256,
    },
    {
        "id": "market_arm_freeze",
        "commit": PIN_OWNED_HISTORY,
        "path": PIN_FREEZE_PATH,
        "field": "reg496.n / intersection.n / intersection.missing_n / intersection.games[].quotes",
        "need": "original freeze: selected-187 quotes + missing_n=400 identities",
    },
)


def git_root(start: Path) -> Path:
    seeds = [start.resolve(), Path(__file__).resolve()]
    for seed in seeds:
        for path in (seed, *seed.parents):
            if (path / ".git").exists():
                return path
    raise OwnedMarketRefuse(f"git root not found from {start}")


def _git_show_bytes(root: Path, commit: str, rel: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{rel}"],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise FileNotFoundError(f"git show {commit}:{rel} failed: {err}")
    return proc.stdout


def restore_original_locator(root: Path, spec: dict[str, str]) -> dict[str, Any]:
    row = {
        "id": spec["id"],
        "commit": spec["commit"],
        "path": spec["path"],
        "field": spec["field"],
        "need": spec["need"],
        "locator": f"{spec['commit']}:{spec['path']}",
        "on_main": False,
        "on_tip_9ce485e9": False,
    }
    try:
        raw = _git_show_bytes(root, spec["commit"], spec["path"])
    except FileNotFoundError as exc:
        row["status"] = "UNAVAILABLE"
        row["unavailable_original"] = f"{spec['commit']}:{spec['path']}"
        row["error"] = str(exc)
        return row
    digest = hashlib.sha256(raw).hexdigest()
    row["status"] = "RESTORED_FROM_HISTORY"
    row["bytes"] = len(raw)
    row["sha256"] = digest
    expected = spec.get("expected_sha256")
    if expected:
        row["expected_sha256"] = expected
        row["sha256_match"] = digest == expected
        if digest != expected:
            raise OwnedMarketRefuse(
                f"{spec['path']} sha256 {digest} != Cos-verified {expected}"
            )
    return row


def probe_original_locators(repo_root: Path) -> dict[str, Any]:
    root = git_root(repo_root)
    rows = [restore_original_locator(root, spec) for spec in ORIGINAL_LOCATORS]
    return {
        "git_root": str(root),
        "history_commit": PIN_OWNED_HISTORY,
        "required": rows,
        "all_restored": all(r["status"] == "RESTORED_FROM_HISTORY" for r in rows),
        "database_url_set": bool(
            os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_PSYCOPG")
        ),
        "invented_destinations_not_used": [
            "data/ops/nfl_owned_market_v1/owned_2020_21_selected_187.json",
            "data/ops/nfl_owned_market_v1/missingness_400.json",
            "data/ops/nfl_owned_market_v1/clock_provenance.json",
        ],
    }


def _project_identities(freeze: dict[str, Any]) -> dict[str, Any]:
    reg = freeze.get("reg496") or {}
    inter = freeze.get("intersection") or {}
    if int(reg.get("n") or 0) != PIN_REG496_N:
        raise OwnedMarketRefuse(f"reg496.n {reg.get('n')} != {PIN_REG496_N}")
    if str(reg.get("identity_sha256") or "") != PIN_REG496_IDENTITY_SHA256:
        raise OwnedMarketRefuse("reg496.identity_sha256 mismatch")
    if int(inter.get("n") or 0) != PIN_INTERSECTION_N:
        raise OwnedMarketRefuse(f"intersection.n {inter.get('n')} != {PIN_INTERSECTION_N}")
    if int(inter.get("missing_n") or 0) != PIN_MISSING_N:
        raise OwnedMarketRefuse(f"intersection.missing_n {inter.get('missing_n')} != {PIN_MISSING_N}")

    identities: list[dict[str, Any]] = []
    seasons: dict[int, int] = {}
    for game in inter.get("games") or []:
        for quote in game.get("quotes") or []:
            season = quote.get("season")
            if season not in (2020, 2021):
                raise OwnedMarketRefuse(f"non 2020/21 identity refused: season={season!r}")
            hit = sorted(set(quote) & FORBIDDEN_VALUE_FIELDS)
            # values may exist on the original quote; do not copy them
            row = {field: quote.get(field) for field in IDENTITY_ONLY_FIELDS}
            if any(row[field] in (None, "") for field in ("game_id", "season", "week")):
                raise OwnedMarketRefuse("identity missing game_id/season/week")
            identities.append(row)
            seasons[int(season)] = seasons.get(int(season), 0) + 1
            _ = hit  # original may contain values; projection drops them
    if len(identities) != PIN_SELECTED_187:
        raise OwnedMarketRefuse(
            f"selected identities {len(identities)} != {PIN_SELECTED_187}"
        )
    missing_ids = list(inter.get("missing_game_ids") or [])
    if len(missing_ids) != PIN_MISSING_N:
        raise OwnedMarketRefuse(f"missing_game_ids {len(missing_ids)} != {PIN_MISSING_N}")
    limits = freeze.get("limitations") or {}
    return {
        "selected_187": {
            "n": len(identities),
            "n_by_season": {"2020": seasons.get(2020, 0), "2021": seasons.get(2021, 0)},
            "fields": list(IDENTITY_ONLY_FIELDS),
            "value_fields_copied": [],
            "identities": identities,
            "source_locator": f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#intersection.games[].quotes",
        },
        "missingness_400": {
            "n": PIN_MISSING_N,
            "n_by_season": inter.get("missing_n_by_season"),
            "game_ids": missing_ids,
            "causes_invented": False,
            "source_locator": f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#intersection.missing_n",
        },
        "clock": {
            "invented": False,
            "original_clock_fields": list(CLOCK_FIELDS_ON_ORIGINAL),
            "publication_timestamp_status": limits.get("publication_timestamp_status"),
            "observation_timestamp_status": limits.get("observation_timestamp_status"),
            "source_locator": f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#limitations",
            "status": "UNVERIFIED_ON_ORIGINAL",
        },
        "reg496": {
            "n": PIN_REG496_N,
            "identity_sha256": PIN_REG496_IDENTITY_SHA256,
            "n_by_season": reg.get("n_by_season"),
        },
        "intersection": {"n": PIN_INTERSECTION_N},
    }


def build_owned_readiness_document(repo_root: Path) -> dict[str, Any]:
    probe = probe_original_locators(repo_root)
    unavailable = [r for r in probe["required"] if r["status"] != "RESTORED_FROM_HISTORY"]
    projection: dict[str, Any] | None = None
    label = "OWNED_SOURCE_UNAVAILABLE"
    if probe["all_restored"]:
        root = git_root(repo_root)
        freeze = json.loads(_git_show_bytes(root, PIN_OWNED_HISTORY, PIN_FREEZE_PATH))
        projection = _project_identities(freeze)
        label = "OWNED_IDENTITIES_PROJECTED"
    doc: dict[str, Any] = {
        "cert": CERT,
        "channel": "OWNED_READINESS",
        "data_label": label,
        "owned_completion_claimed": False,
        "package": PACKAGE,
        "probe": probe,
        "profile": PROFILE_OWNED_MARKET_TRACE,
        "profile_role": ROLE_OWNED_READINESS,
        "projection": projection,
        "schema_version": SCHEMA_OWNED_MARKET_TRACE,
        "scientific_hold": [
            "no historical performance",
            "no outcome join",
            "no real forecast",
            "no scientific GO",
            "no 2022/23 quote values",
            "identities before quote-value exposure",
            "no invented clock fields",
            "no invented missingness causes",
        ],
        "source_byte_hash": "11" * 32,
        "unavailable": unavailable,
    }
    body = {k: v for k, v in doc.items() if k != "source_byte_hash"}
    doc["source_byte_hash"] = canonical_sha256(body)
    return doc
