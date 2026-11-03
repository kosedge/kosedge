"""OWNED_MARKET_TRACE_V1 readiness probe. CERT=0.

Bounded metadata/value projection for owned 2020/21 selected-187 /
missingness-400 / clock provenance. Never labels fiction as owned completion.
No Cos-host staging. No outcome join.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    CERT,
    PACKAGE,
    PROFILE_OWNED_MARKET_TRACE,
    ROLE_OWNED_READINESS,
    SCHEMA_OWNED_MARKET_TRACE,
)
from src.services.nfl_owned_market_v1.hashing import canonical_sha256, sha256_file

# Exact worker-visible paths this return will accept as the selected SoT.
# Absence here is UNAVAILABLE — not filled from Odds-API date dumps.
REQUIRED_OWNED_INPUTS: tuple[dict[str, str], ...] = (
    {
        "id": "selected_187",
        "path": "data/ops/nfl_owned_market_v1/owned_2020_21_selected_187.json",
        "field": "quotes[187].quote_id",
        "need": "owned 2020/21 selected 187 quote-trace identity list",
    },
    {
        "id": "missingness_400",
        "path": "data/ops/nfl_owned_market_v1/missingness_400.json",
        "field": "rows[400].missing_enum",
        "need": "owned 400-row missingness projection",
    },
    {
        "id": "clock_provenance",
        "path": "data/ops/nfl_owned_market_v1/clock_provenance.json",
        "field": "quotes[].available_at|observed_at|captured_at_utc",
        "need": "owned clock provenance for the selected 187",
    },
)

RELATED_NOT_SOURCE: tuple[dict[str, str], ...] = (
    {
        "path": "apps/web/data/raw/odds/open/2020-*.json + 2021-*.json",
        "field": "Odds-API historical date dump (timestamp/data)",
        "reason": "date dumps exist on this VM but are not the selected-187 identity, not missingness-400, and carry no owned clock-provenance contract",
    },
    {
        "path": "apps/web/data/raw/odds/close/2020-*.json + 2021-*.json",
        "field": "Odds-API historical date dump",
        "reason": "same: raw dumps ≠ selected owned quote trace",
    },
    {
        "path": "data/ops/nfl-owned-data-20260705T201049Z/*.ndjson",
        "field": "nfl_dp_* season=2025 warehouse export",
        "reason": "2025 player/schedule dump; no 2020/21 quote rows; no selected-187",
    },
    {
        "path": "DATABASE_URL / odds_snapshots / nfl_market_history_snapshots",
        "field": "Postgres owned open/close",
        "reason": "DATABASE_URL unset; no local postgres listener on this Cursor worker",
    },
)


def _exists(repo_root: Path, rel: str) -> bool:
    if rel.startswith("/"):
        return Path(rel).exists()
    return (repo_root / rel).exists()


def probe_owned_inputs(repo_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for spec in REQUIRED_OWNED_INPUTS:
        present = _exists(repo_root, spec["path"])
        row = {
            **spec,
            "status": "PRESENT" if present else "UNAVAILABLE",
        }
        if present:
            path = Path(spec["path"]) if spec["path"].startswith("/") else repo_root / spec["path"]
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
        rows.append(row)
    env_db = bool(os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_PSYCOPG"))
    return {
        "required": rows,
        "all_present": all(r["status"] == "PRESENT" for r in rows),
        "database_url_set": env_db,
        "related_but_not_source": list(RELATED_NOT_SOURCE),
    }


def build_owned_readiness_document(repo_root: Path) -> dict[str, Any]:
    probe = probe_owned_inputs(repo_root)
    unavailable = [r for r in probe["required"] if r["status"] == "UNAVAILABLE"]
    doc: dict[str, Any] = {
        "cert": CERT,
        "channel": "OWNED_READINESS",
        "data_label": "OWNED_SOURCE_UNAVAILABLE" if unavailable else "OWNED_SOURCE_BOUND",
        "owned_completion_claimed": False,
        "package": PACKAGE,
        "probe": probe,
        "profile": PROFILE_OWNED_MARKET_TRACE,
        "profile_role": ROLE_OWNED_READINESS,
        "schema_version": SCHEMA_OWNED_MARKET_TRACE,
        "scientific_hold": [
            "no historical performance",
            "no outcome join",
            "no real forecast",
            "no scientific GO",
        ],
        "source_byte_hash": "11" * 32,
        "unavailable": unavailable,
    }
    body = {k: v for k, v in doc.items() if k != "source_byte_hash"}
    doc["source_byte_hash"] = canonical_sha256(body)
    return doc
