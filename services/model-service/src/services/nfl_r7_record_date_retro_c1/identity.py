"""Bind 2320 REG history identity pointers. IDENTITY COLUMNS ONLY. CERT=0."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_r7_record_date_retro_c1.pins import (
    FORBIDDEN_SCORE_KEYS,
    GAMES_SHA256,
    IDENTITY_REL,
    IDENTITY_SHA256,
    N_2020_21,
    N_HISTORY_2013_19,
    N_IDENTITY,
    OUTCOMES_SHA256,
    REG_IDENTITY_SOURCE_SHA256,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse

ALLOWED_KEYS = frozenset(
    {
        "away_franchise",
        "game_id",
        "home_franchise",
        "nominal_kickoff_utc",
        "role",
        "score_source_row_identity_only",
        "season",
        "season_type",
        "source_row",
        "week",
    }
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scan_forbidden(payload: Any, *, where: str) -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key).casefold() in FORBIDDEN_SCORE_KEYS:
                raise RetroRefuse(f"{where} contains forbidden score key {key}")
            _scan_forbidden(value, where=where)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _scan_forbidden(item, where=where)


def bind_identity_pointers(root: Path) -> dict[str, Any]:
    path = Path(root) / IDENTITY_REL
    if not path.is_file():
        raise RetroRefuse(f"identity pointers missing {IDENTITY_REL}")
    digest = sha256_file(path)
    if digest != IDENTITY_SHA256:
        raise RetroRefuse(f"identity pointers sha256 {digest} != {IDENTITY_SHA256}")
    body = json.loads(path.read_text(encoding="utf-8"))
    _scan_forbidden(body, where="identity pointers")
    if body.get("schema") != "REG_HISTORY_IDENTITY_POINTERS_ONLY_V1":
        raise RetroRefuse("identity schema drifted")
    if body.get("games_source_sha256") != GAMES_SHA256:
        raise RetroRefuse("games source pin drifted")
    if body.get("score_source_sha256") != OUTCOMES_SHA256:
        raise RetroRefuse("outcomes source pin drifted")
    if body.get("reg_identity_source_sha256") != REG_IDENTITY_SOURCE_SHA256:
        raise RetroRefuse("reg identity source pin drifted")
    if body.get("no_score_values_read_or_projected") is not True:
        raise RetroRefuse("identity file claims score projection")
    if body.get("no_model_fit_solve_score") is not True:
        raise RetroRefuse("identity file claims model/score work")
    rows = list(body.get("rows") or [])
    if len(rows) != N_IDENTITY:
        raise RetroRefuse(f"identity n={len(rows)} != {N_IDENTITY}")
    ids = [str(row["game_id"]) for row in rows]
    if len(set(ids)) != N_IDENTITY:
        raise RetroRefuse("identity game_ids not unique")
    n_1319 = sum(1 for row in rows if 2013 <= int(row["season"]) <= 2019)
    n_2021 = sum(1 for row in rows if int(row["season"]) in (2020, 2021))
    if n_1319 != N_HISTORY_2013_19 or n_2021 != N_2020_21:
        raise RetroRefuse(f"identity split {n_1319}+{n_2021} != {N_HISTORY_2013_19}+{N_2020_21}")
    for row in rows:
        extra = set(row) - ALLOWED_KEYS
        if extra:
            raise RetroRefuse(f"identity extra columns {sorted(extra)}")
        if row.get("season_type") != "REG":
            raise RetroRefuse(f"non-REG identity {row.get('game_id')}")
        if row.get("role") != "history_identity_only":
            raise RetroRefuse(f"identity role drifted {row.get('game_id')}")
        if not isinstance(row.get("week"), int):
            raise RetroRefuse("week-number REG proxy refused — week must be source int")
    return {
        "path": IDENTITY_REL,
        "sha256": digest,
        "n": N_IDENTITY,
        "n_history_2013_19": N_HISTORY_2013_19,
        "n_2020_21": N_2020_21,
        "game_ids": ids,
        "games_source_sha256": GAMES_SHA256,
        "score_source_sha256": OUTCOMES_SHA256,
        "scores_opened": False,
        "week_number_reg_proxy": False,
        "eval_2017_reopened": False,
        "rows": [
            {
                "game_id": str(row["game_id"]),
                "season": int(row["season"]),
                "week": int(row["week"]),
                "season_type": "REG",
                "home_franchise": str(row["home_franchise"]),
                "away_franchise": str(row["away_franchise"]),
                "nominal_kickoff_utc": row.get("nominal_kickoff_utc"),
                "role": "history_identity_only",
            }
            for row in rows
        ],
    }
