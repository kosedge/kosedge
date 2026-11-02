"""79264 boundary: validate CONTRACT_27 + metadata BEFORE any model/IF call."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_t5107u.q2 import SEALED_SEASONS
from src.services.nfl_t5208u.hashing import canonical_sha256, require_sha256_hex, sha256_file
from src.services.nfl_t5208u.packets import PacketRefuse, SYNTHETIC_TOKEN
from src.services.nfl_t5208u.pins import (
    A_Q2,
    B_Q2,
    CANDIDATE_WEIGHT,
    CELL_META_FIELDS,
    CONTRACT_27,
    C_FORMULA,
    ENVELOPE_FIELDS,
    FW_SHA256,
    IF_TIP,
    KO_MINUS_MINUTES,
    MARKET_BLEND,
    PRIOR_CARRY,
    PURE_SOURCE_TIP,
    RIDGE,
    SEED_BASE,
    SEED_MOD,
    SIMULATIONS,
    SIM_SHA256,
)

TEXT_IDENTITY_FIELDS = ("game_id", "home_team", "away_team")
INT_FIELDS = ("matchup_season", "matchup_week")
NUMERIC_FIELDS = tuple(
    name for name in CONTRACT_27 if name not in TEXT_IDENTITY_FIELDS + INT_FIELDS
)
CELL_HASH_FIELDS = (
    "status",
    "reconstructed_value",
    "source",
    "available_at",
    "observed_at",
)
CODE_BIND_FILES = (
    "caller.py",
    "validate.py",
    "pins.py",
    "packets.py",
    "schema.py",
    "if_tree.py",
    "hashing.py",
)
ALGO_BIND_FILES = (
    "if_produce.py",
    "q2.py",
    "builder.py",
    "recon_contract.py",
    "if_control.py",
)


def parse_utc(raw: Any, *, name: str) -> datetime:
    text = str(raw or "").strip()
    if not text or text.lower() in {"not-a-time", "none", "null"}:
        raise PacketRefuse(f"{name} is not a time: {raw!r}")
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PacketRefuse(f"{name} is not a time: {raw!r}") from exc
    if dt.tzinfo is None:
        raise PacketRefuse(f"{name} naive datetime refused: {raw!r}")
    return dt.astimezone(timezone.utc)


def fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cell_content_hash(cell: Mapping[str, Any]) -> str:
    body = {name: cell.get(name) for name in CELL_HASH_FIELDS}
    return canonical_sha256(body)


def packet_content_hash(packet: Mapping[str, Any]) -> str:
    body = {key: value for key, value in packet.items() if key != "source_byte_hash"}
    return canonical_sha256(body)


def history_content_hash(history: list[Mapping[str, Any]]) -> str:
    return canonical_sha256(list(history))


def config_content_hash() -> str:
    return canonical_sha256(
        {
            "a_q2": A_Q2,
            "b_q2": B_Q2,
            "c_formula": C_FORMULA,
            "candidate_weight": CANDIDATE_WEIGHT,
            "fw_sha256": FW_SHA256,
            "if_tip": IF_TIP,
            "ko_minus_minutes": KO_MINUS_MINUTES,
            "market_blend": MARKET_BLEND,
            "prior_carry": PRIOR_CARRY,
            "pure_source_tip": PURE_SOURCE_TIP,
            "ridge": RIDGE,
            "seed_base": SEED_BASE,
            "seed_mod": SEED_MOD,
            "sim_sha256": SIM_SHA256,
            "simulations": SIMULATIONS,
        }
    )


def code_content_hash() -> str:
    here = Path(__file__).resolve().parent
    algo = here.parent / "nfl_t5107u"
    rows: list[str] = []
    for name in CODE_BIND_FILES:
        path = here / name
        if not path.is_file():
            raise PacketRefuse(f"code bind missing {path}")
        rows.append(f"r6/{name}={sha256_file(path)}")
    for name in ALGO_BIND_FILES:
        path = algo / name
        if not path.is_file():
            raise PacketRefuse(f"code bind missing {path}")
        rows.append(f"algo/{name}={sha256_file(path)}")
    digest = canonical_sha256(rows)
    if digest == "0" * 64:
        raise PacketRefuse("code_hash collapsed to empty default")
    return digest


def _require_nonempty_str(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PacketRefuse(f"{name} must be a non-empty string")
    return value


def _require_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PacketRefuse(f"{name} is not an int (bool-as-number refused)")
    return int(value)


def _require_finite_number(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PacketRefuse(f"{name} is not a number (bool-as-number refused)")
    number = float(value)
    if not math.isfinite(number):
        raise PacketRefuse(f"{name} is not finite")
    return number


def _require_cell_map(cell: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(cell, Mapping):
        raise PacketRefuse(f"{name} cell is missing/invalid")
    missing = [field for field in CELL_META_FIELDS if field not in cell]
    if missing:
        raise PacketRefuse(f"{name} missing metadata {missing}")
    return dict(cell)


def validate_before_model(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Fail-closed 79264 gate. Must not invoke IF/Q2/model."""
    if not isinstance(packet, Mapping):
        raise PacketRefuse("packet is missing/invalid")
    if not isinstance(history, list) or not history:
        raise PacketRefuse("history is missing/invalid")

    env = packet.get("envelope")
    if not isinstance(env, Mapping):
        raise PacketRefuse("envelope is missing/invalid")
    missing_env = [name for name in ENVELOPE_FIELDS if name not in env or env.get(name) in (None, "")]
    if missing_env:
        raise PacketRefuse(f"envelope missing {missing_env}")

    kickoff = parse_utc(env.get("kickoff_utc"), name="envelope.kickoff_utc")
    seal = kickoff
    cutoff = seal - timedelta(minutes=KO_MINUS_MINUTES)
    season = _require_int(env.get("season"), name="envelope.season")
    week = _require_int(env.get("week"), name="envelope.week")
    if season in SEALED_SEASONS:
        raise PacketRefuse(f"SEALED_SEASONS refuse: target season {season}")
    season_type = _require_nonempty_str(env.get("season_type"), name="envelope.season_type").upper()
    if season_type != "REG":
        raise PacketRefuse(f"bad REG identity: season_type={season_type!r}")
    game_id = _require_nonempty_str(env.get("game_id"), name="envelope.game_id")
    home = _require_nonempty_str(env.get("home_team"), name="envelope.home_team")
    away = _require_nonempty_str(env.get("away_team"), name="envelope.away_team")
    identity = _require_nonempty_str(env.get("identity_kind"), name="envelope.identity_kind")
    if SYNTHETIC_TOKEN not in game_id or SYNTHETIC_TOKEN not in identity:
        raise PacketRefuse("bad SYNTHETIC identity")
    _require_nonempty_str(env.get("venue_id"), name="envelope.venue_id")

    cells = packet.get("contract_27")
    if not isinstance(cells, Mapping):
        raise PacketRefuse("contract_27 is missing/invalid")
    missing = [name for name in CONTRACT_27 if name not in cells]
    extra = sorted(set(cells) - set(CONTRACT_27))
    if missing:
        raise PacketRefuse(f"contract_27 missing {missing}")
    if extra:
        raise PacketRefuse(f"contract_27 unknown fields {extra}")

    values: dict[str, Any] = {}
    for name in CONTRACT_27:
        cell = _require_cell_map(cells[name], name=name)
        if str(cell.get("status") or "") != "DERIVED_PREGAME":
            raise PacketRefuse(f"{name} status is not DERIVED_PREGAME")
        _require_nonempty_str(cell.get("source"), name=f"{name}.source")
        available = parse_utc(cell.get("available_at"), name=f"{name}.available_at")
        observed = parse_utc(cell.get("observed_at"), name=f"{name}.observed_at")
        if available > observed:
            raise PacketRefuse(f"{name} available_at after observed_at")
        if available == seal or observed == seal:
            raise PacketRefuse(f"{name} equal-to-seal time {fmt_utc(seal)}")
        if available > cutoff or observed > cutoff:
            raise PacketRefuse(
                f"{name} late vs KO−{KO_MINUS_MINUTES} cutoff {fmt_utc(cutoff)}"
            )
        claimed = cell.get("source_byte_hash")
        try:
            claimed_hex = require_sha256_hex(claimed, name=f"{name}.source_byte_hash")
        except ValueError as exc:
            raise PacketRefuse(str(exc)) from exc
        actual = cell_content_hash(cell)
        if claimed_hex != actual:
            raise PacketRefuse(f"{name} wrong source_byte_hash")

        raw = cell.get("reconstructed_value")
        if raw in (None, ""):
            raise PacketRefuse(f"{name} reconstructed_value missing/invalid")
        if name in TEXT_IDENTITY_FIELDS:
            values[name] = _require_nonempty_str(raw, name=name)
        elif name in INT_FIELDS:
            values[name] = _require_int(raw, name=name)
        else:
            values[name] = _require_finite_number(raw, name=name)

    if values["game_id"] != game_id:
        raise PacketRefuse("envelope/cell game_id identity mismatch")
    if values["home_team"] != home or values["away_team"] != away:
        raise PacketRefuse("envelope/cell team identity mismatch")
    if values["matchup_season"] != season or values["matchup_week"] != week:
        raise PacketRefuse("envelope/cell season/week identity mismatch")
    if not str(values["game_id"]).startswith(SYNTHETIC_TOKEN):
        raise PacketRefuse("cell game_id is not SYNTHETIC-prefixed")

    try:
        packet_claimed = require_sha256_hex(
            packet.get("source_byte_hash"), name="packet.source_byte_hash"
        )
    except ValueError as exc:
        raise PacketRefuse(str(exc)) from exc
    packet_hash = packet_content_hash(packet)
    if packet_claimed != packet_hash:
        raise PacketRefuse("packet wrong source_byte_hash")

    for index, row in enumerate(history):
        if not isinstance(row, Mapping):
            raise PacketRefuse(f"history[{index}] is missing/invalid")
        if str(row.get("channel") or "") != "SYNTHETIC":
            raise PacketRefuse(f"history[{index}] is not SYNTHETIC")
        gid = _require_nonempty_str(row.get("game_id"), name=f"history[{index}].game_id")
        if not gid.startswith(SYNTHETIC_TOKEN):
            raise PacketRefuse(f"history[{index}] game_id is not SYNTHETIC-prefixed")
        if gid == game_id:
            raise PacketRefuse("history includes target game_id (own-state refuse)")
        row_season = _require_int(row.get("season"), name=f"history[{index}].season")
        row_week = _require_int(row.get("week"), name=f"history[{index}].week")
        if row_season in SEALED_SEASONS:
            raise PacketRefuse(f"SEALED_SEASONS refuse: history season {row_season}")
        row_type = _require_nonempty_str(
            row.get("season_type"), name=f"history[{index}].season_type"
        ).upper()
        if row_type != "REG":
            raise PacketRefuse(f"history[{index}] is not REG")
        _require_nonempty_str(row.get("home_team"), name=f"history[{index}].home_team")
        _require_nonempty_str(row.get("away_team"), name=f"history[{index}].away_team")
        row_ko = parse_utc(row.get("kickoff_utc"), name=f"history[{index}].kickoff_utc")
        if row_ko >= cutoff:
            raise PacketRefuse(f"history[{index}] kickoff not < KO−{KO_MINUS_MINUTES}")
        if row_season > season or (row_season == season and row_week >= week):
            raise PacketRefuse(f"history[{index}] same-week/future vs target")
        _require_finite_number(row.get("home_score"), name=f"history[{index}].home_score")
        _require_finite_number(row.get("away_score"), name=f"history[{index}].away_score")
        if "source_byte_hash" in row:
            try:
                claimed_row = require_sha256_hex(
                    row.get("source_byte_hash"), name=f"history[{index}].source_byte_hash"
                )
            except ValueError as exc:
                raise PacketRefuse(str(exc)) from exc
            actual_row = canonical_sha256(
                {key: value for key, value in row.items() if key != "source_byte_hash"}
            )
            if claimed_row != actual_row:
                raise PacketRefuse(f"history[{index}] wrong source_byte_hash")

    history_hash = history_content_hash(history)
    config_hash = config_content_hash()
    code_hash = code_content_hash()
    for label, digest in (
        ("packet_hash", packet_hash),
        ("history_hash", history_hash),
        ("config_hash", config_hash),
        ("code_hash", code_hash),
    ):
        require_sha256_hex(digest, name=label)

    return {
        "packet_hash": packet_hash,
        "history_hash": history_hash,
        "config_hash": config_hash,
        "code_hash": code_hash,
        "cutoff_utc": fmt_utc(cutoff),
        "seal_utc": fmt_utc(seal),
        "ko_minus_minutes": KO_MINUS_MINUTES,
        "n_contract_27": len(CONTRACT_27),
        "validated": True,
    }


def rehash_cell(cell: dict[str, Any]) -> dict[str, Any]:
    cell["source_byte_hash"] = cell_content_hash(cell)
    return cell


def rehash_packet(packet: dict[str, Any]) -> dict[str, Any]:
    packet["source_byte_hash"] = packet_content_hash(packet)
    return packet
