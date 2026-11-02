"""SYNTHETIC typed packets. Unusable by any real-mode gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.services.nfl_t5107u.q2 import Game, SEALED_SEASONS
from src.services.nfl_t5208u.pins import (
    CELL_META_FIELDS,
    CHANNEL_SYNTHETIC,
    CONTRACT_27,
    KO_MINUS_MINUTES,
)

SYNTHETIC_TOKEN = "SYNTHETIC"


class RealModeRefuse(ValueError):
    """SYNTHETIC packets / real-mode callers are hard-refused."""


class PacketRefuse(ValueError):
    """Typed packet failed structural or cutoff checks."""


def _utc(text: str) -> datetime:
    raw = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise PacketRefuse(f"naive kickoff refused: {text!r}")
    return dt.astimezone(timezone.utc)


def _source_byte_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cell(value: Any, *, source: str, available_at: str, observed_at: str) -> dict[str, Any]:
    body = {
        "status": "DERIVED_PREGAME",
        "reconstructed_value": value,
        "source": source,
        "available_at": available_at,
        "observed_at": observed_at,
    }
    body["source_byte_hash"] = _source_byte_hash(body)
    missing = [name for name in CELL_META_FIELDS if name not in body]
    if missing:
        raise PacketRefuse(f"cell missing meta {missing}")
    return body


def refuse_real_mode(mode: str, packet: Mapping[str, Any] | None = None) -> None:
    if str(mode or "").upper() != CHANNEL_SYNTHETIC:
        raise RealModeRefuse(f"real-mode refused: mode={mode!r} (SYNTHETIC only)")
    if packet is None:
        return
    channel = str(packet.get("channel") or "")
    packet_class = str(packet.get("packet_class") or "")
    if channel != CHANNEL_SYNTHETIC or packet_class != CHANNEL_SYNTHETIC:
        raise RealModeRefuse(
            f"packet not SYNTHETIC: channel={channel!r} packet_class={packet_class!r}"
        )
    if packet.get("real_mode_usable") is True:
        raise RealModeRefuse("packet marked real_mode_usable — refused")
    identity = str((packet.get("envelope") or {}).get("identity_kind") or "")
    if SYNTHETIC_TOKEN not in identity:
        raise RealModeRefuse(f"identity_kind {identity!r} is not SYNTHETIC")
    game_id = str((packet.get("envelope") or {}).get("game_id") or packet.get("game_id") or "")
    if not game_id.startswith(SYNTHETIC_TOKEN):
        raise RealModeRefuse(f"game_id {game_id!r} is not SYNTHETIC-prefixed")


def _assert_history_cutoff(
    history: list[Mapping[str, Any]],
    *,
    target_game_id: str,
    target_kickoff: datetime,
    target_season: int,
    target_week: int,
) -> list[Game]:
    cutoff = target_kickoff - timedelta(minutes=KO_MINUS_MINUTES)
    games: list[Game] = []
    for row in history:
        if str(row.get("channel") or CHANNEL_SYNTHETIC) != CHANNEL_SYNTHETIC:
            raise PacketRefuse("history row is not SYNTHETIC")
        season = int(row["season"])
        if season in SEALED_SEASONS:
            raise PacketRefuse(f"SEALED_SEASONS refuse: history season {season}")
        season_type = str(row.get("season_type") or "REG").upper()
        if season_type != "REG":
            raise PacketRefuse(f"Q2 history must be REG, got {season_type}")
        gid = str(row["game_id"])
        if not gid.startswith(SYNTHETIC_TOKEN):
            raise PacketRefuse(f"history game_id {gid!r} is not SYNTHETIC-prefixed")
        if gid == target_game_id:
            raise PacketRefuse("history includes target game_id (own-state refuse)")
        ko = _utc(str(row["kickoff_utc"]))
        if ko >= cutoff:
            raise PacketRefuse(
                f"{gid} kickoff {ko.isoformat()} is not < KO−{KO_MINUS_MINUTES}"
            )
        week = int(row["week"])
        if season > target_season:
            raise PacketRefuse(f"{gid} future season vs target")
        if season == target_season and week >= target_week:
            raise PacketRefuse(f"{gid} same-week/future week vs target W{target_week}")
        hs = row.get("home_score")
        aws = row.get("away_score")
        if hs in (None, "") or aws in (None, ""):
            raise PacketRefuse(f"{gid} history missing scores")
        games.append(
            Game(
                season=season,
                week=week,
                game_id=gid,
                home=str(row["home_team"]),
                away=str(row["away_team"]),
                kickoff_utc=ko,
                home_score=float(hs),
                away_score=float(aws),
                season_type="REG",
            )
        )
    return games


def build_synthetic_demo() -> dict[str, Any]:
    """Two-control SYNTHETIC slate. Not a real schedule. Not outcomes scoring."""
    available_at = "2018-10-14T15:00:00Z"
    observed_at = "2018-10-14T15:30:00Z"
    source = "SYNTHETIC_TYPED_PACKET_t5208u"
    envelope = {
        "game_id": "SYNTHETIC_2018_W05_KC_NE",
        "season": 2018,
        "week": 5,
        "season_type": "REG",
        "home_team": "KC",
        "away_team": "NE",
        "kickoff_utc": "2018-10-14T17:00:00Z",
        "venue_id": "SYNTHETIC_VENUE_ARROWHEAD",
        "identity_kind": "SYNTHETIC_REG",
    }
    values: dict[str, Any] = {
        "game_id": envelope["game_id"],
        "home_team": "KC",
        "away_team": "NE",
        "matchup_season": 2018,
        "matchup_week": 5,
        "rest_days_home": 7.0,
        "rest_days_away": 7.0,
        "offense_index_home": 1.12,
        "offense_index_away": 1.04,
        "defense_index_home": 0.98,
        "defense_index_away": 1.06,
        "home_off_epa_5g": 0.11,
        "away_off_epa_5g": 0.04,
        "home_def_epa_allowed_5g": -0.02,
        "away_def_epa_allowed_5g": 0.03,
        "home_success_offense_5g": 0.49,
        "away_success_offense_5g": 0.46,
        "home_success_defense_allowed_5g": 0.43,
        "away_success_defense_allowed_5g": 0.45,
        "home_pass_rate_5g": 0.61,
        "away_pass_rate_5g": 0.58,
        "matchup_diff_off_epa_5g": 0.07,
        "matchup_diff_def_epa_allowed_5g": -0.05,
        "matchup_diff_success_rate_5g": 0.03,
        "matchup_diff_pressure_allowed_5g": -0.02,
        "matchup_diff_pressure_generated_5g": 0.03,
        "matchup_diff_red_zone_td_rate_5g": 0.04,
    }
    if tuple(values) != CONTRACT_27:
        # Keep construction order identical to the frozen tuple.
        values = {name: values[name] for name in CONTRACT_27}
    contract_27 = {
        name: _cell(
            values[name],
            source=source,
            available_at=available_at,
            observed_at=observed_at,
        )
        for name in CONTRACT_27
    }
    packet = {
        "channel": CHANNEL_SYNTHETIC,
        "packet_class": CHANNEL_SYNTHETIC,
        "mode_gate": "SYNTHETIC_ONLY",
        "real_mode_usable": False,
        "envelope": envelope,
        "contract_27": contract_27,
    }
    packet["source_byte_hash"] = _source_byte_hash(packet)

    history = [
        _hist("SYNTHETIC_2017_W02_KC_BUF", 2017, 2, "KC", "BUF", "2017-09-17T17:00:00Z", 24, 10),
        _hist("SYNTHETIC_2017_W03_NE_MIA", 2017, 3, "NE", "MIA", "2017-09-24T17:00:00Z", 27, 17),
        _hist("SYNTHETIC_2017_W06_BUF_MIA", 2017, 6, "BUF", "MIA", "2017-10-15T17:00:00Z", 20, 13),
        _hist("SYNTHETIC_2017_W08_NE_KC", 2017, 8, "NE", "KC", "2017-10-29T17:00:00Z", 16, 23),
        _hist("SYNTHETIC_2017_W12_MIA_KC", 2017, 12, "MIA", "KC", "2017-11-26T18:00:00Z", 14, 31),
        _hist("SYNTHETIC_2017_W14_BUF_NE", 2017, 14, "BUF", "NE", "2017-12-10T18:00:00Z", 10, 28),
        _hist("SYNTHETIC_2018_W01_KC_MIA", 2018, 1, "KC", "MIA", "2018-09-09T17:00:00Z", 27, 20),
        _hist("SYNTHETIC_2018_W02_NE_BUF", 2018, 2, "NE", "BUF", "2018-09-16T17:00:00Z", 24, 6),
        _hist("SYNTHETIC_2018_W03_BUF_KC", 2018, 3, "BUF", "KC", "2018-09-23T17:00:00Z", 13, 22),
        _hist("SYNTHETIC_2018_W04_MIA_NE", 2018, 4, "MIA", "NE", "2018-09-30T17:00:00Z", 17, 38),
    ]
    control_a = {
        "label": "CONTROL_A_IF2_Q24",
        "if_margin": 2.0,
        "q2_margin": 4.0,
        "expected_c": 3.0,
    }
    control_b = {
        "label": "CONTROL_B_IF_NEG1_Q2_1",
        "if_margin": -1.0,
        "q2_margin": 1.0,
        "expected_c": 0.0,
    }
    return {
        "channel": CHANNEL_SYNTHETIC,
        "packet": packet,
        "history": history,
        "c_formula_controls": [control_a, control_b],
    }


def _hist(
    game_id: str,
    season: int,
    week: int,
    home: str,
    away: str,
    kickoff_utc: str,
    home_score: float,
    away_score: float,
) -> dict[str, Any]:
    return {
        "channel": CHANNEL_SYNTHETIC,
        "game_id": game_id,
        "season": season,
        "week": week,
        "season_type": "REG",
        "home_team": home,
        "away_team": away,
        "kickoff_utc": kickoff_utc,
        "home_score": home_score,
        "away_score": away_score,
        "note": "SYNTHETIC_REG_SCORE_HISTORY_STATE_ONLY",
    }


def contract_packet_for_if(packet: Mapping[str, Any]) -> dict[str, Any]:
    cells = packet.get("contract_27")
    if not isinstance(cells, Mapping):
        raise PacketRefuse("packet missing contract_27")
    missing = [name for name in CONTRACT_27 if name not in cells]
    if missing:
        raise PacketRefuse(f"contract_27 missing {missing}")
    extra = sorted(set(cells) - set(CONTRACT_27))
    if extra:
        raise PacketRefuse(f"contract_27 unknown fields {extra}")
    return {name: cells[name] for name in CONTRACT_27}


def history_games_for_q2(packet: Mapping[str, Any], history: list[Mapping[str, Any]]) -> tuple[Game, list[Game]]:
    env = packet.get("envelope") or {}
    season = int(env["season"])
    if season in SEALED_SEASONS:
        raise PacketRefuse(f"SEALED_SEASONS refuse: target season {season}")
    if str(env.get("season_type") or "REG").upper() != "REG":
        raise PacketRefuse("target is not REG")
    target = Game(
        season=season,
        week=int(env["week"]),
        game_id=str(env["game_id"]),
        home=str(env["home_team"]),
        away=str(env["away_team"]),
        kickoff_utc=_utc(str(env["kickoff_utc"])),
        home_score=None,
        away_score=None,
        season_type="REG",
    )
    hist = _assert_history_cutoff(
        history,
        target_game_id=target.game_id,
        target_kickoff=target.kickoff_utc,
        target_season=target.season,
        target_week=target.week,
    )
    return target, hist
