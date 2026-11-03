"""Opt-in SYNTHETIC IF/Q2 packet. TNF rest + franchise-alias history. CERT=0."""

from __future__ import annotations

from typing import Any

from src.services.nfl_r7_correctness_v1.calendar import bind_rest_from_et_calendar
from src.services.nfl_r7_correctness_v1.franchise import franchise_bind
from src.services.nfl_r7_correctness_v1.pins import (
    CHANNEL_SYNTHETIC,
    CONTRACT_27,
)
from src.services.nfl_t5208u.hashing import canonical_sha256
from src.services.nfl_t5208u.packets import RealModeRefuse, refuse_real_mode
from src.services.nfl_t5208u.pins import CELL_META_FIELDS
from src.services.nfl_t5208u.validate import cell_content_hash, packet_content_hash


class R7PacketRefuse(ValueError):
    """Typed R7 packet refuse."""


def _cell(value: Any, *, source: str, available_at: str, observed_at: str) -> dict[str, Any]:
    body = {
        "status": "DERIVED_PREGAME",
        "reconstructed_value": value,
        "source": source,
        "available_at": available_at,
        "observed_at": observed_at,
    }
    body["source_byte_hash"] = cell_content_hash(body)
    missing = [name for name in CELL_META_FIELDS if name not in body]
    if missing:
        raise R7PacketRefuse(f"cell missing meta {missing}")
    return body


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
    row = {
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
    row["source_byte_hash"] = canonical_sha256(
        {key: value for key, value in row.items() if key != "source_byte_hash"}
    )
    return row


def _phys(
    game_id: str,
    season: int,
    week: int,
    home: str,
    away: str,
    kickoff_utc: str,
) -> dict[str, Any]:
    """Physical-schedule row. Kickoff only. No scores / outcomes."""
    return {
        "channel": CHANNEL_SYNTHETIC,
        "game_id": game_id,
        "season": season,
        "week": week,
        "season_type": "REG",
        "home_team": home,
        "away_team": away,
        "kickoff_utc": kickoff_utc,
        "note": "SYNTHETIC_PHYSICAL_SCHEDULE_NON_OUTCOME",
    }


def synthetic_physical_schedule() -> list[dict[str, Any]]:
    """Non-outcome physical predecessors. May include same-week kickoffs.

    Not Q2 history. validate.py:299 same-week refuse must not see these rows.
    """
    return [
        _phys("SYNTHETIC_2017_W02_SD_BUF", 2017, 2, "SD", "BUF", "2017-09-17T17:00:00Z"),
        _phys("SYNTHETIC_2017_W03_STL_MIA", 2017, 3, "STL", "MIA", "2017-09-24T17:00:00Z"),
        _phys("SYNTHETIC_2017_W06_BUF_MIA", 2017, 6, "BUF", "MIA", "2017-10-15T17:00:00Z"),
        _phys("SYNTHETIC_2017_W08_NE_SD", 2017, 8, "NE", "SD", "2017-10-29T17:00:00Z"),
        _phys("SYNTHETIC_2017_W12_MIA_STL", 2017, 12, "MIA", "STL", "2017-11-26T18:00:00Z"),
        _phys("SYNTHETIC_2017_W14_BUF_NE", 2017, 14, "BUF", "NE", "2017-12-10T18:00:00Z"),
        _phys("SYNTHETIC_2018_W01_SD_MIA", 2018, 1, "SD", "MIA", "2018-09-09T17:00:00Z"),
        _phys("SYNTHETIC_2018_W02_STL_BUF", 2018, 2, "STL", "BUF", "2018-09-16T17:00:00Z"),
        _phys("SYNTHETIC_2018_W03_BUF_SD", 2018, 3, "BUF", "SD", "2018-09-23T17:00:00Z"),
        _phys("SYNTHETIC_2018_W04_MIA_STL", 2018, 4, "MIA", "STL", "2018-09-30T17:00:00Z"),
        _phys("SYNTHETIC_2018_W05_SD_KC", 2018, 5, "SD", "KC", "2018-10-07T17:00:00Z"),
        _phys("SYNTHETIC_2018_W05_STL_NE", 2018, 5, "STL", "NE", "2018-10-07T20:25:00Z"),
    ]


def synthetic_history() -> list[dict[str, Any]]:
    """Fictional REG scored history. Strictly prior assigned week for Q2.

    Not protected 2024-26 / EVAL / Q2-2017 reopen. Not a physical schedule.
    """
    return [
        _hist("SYNTHETIC_2017_W02_SD_BUF", 2017, 2, "SD", "BUF", "2017-09-17T17:00:00Z", 24, 10),
        _hist("SYNTHETIC_2017_W03_STL_MIA", 2017, 3, "STL", "MIA", "2017-09-24T17:00:00Z", 27, 17),
        _hist("SYNTHETIC_2017_W06_BUF_MIA", 2017, 6, "BUF", "MIA", "2017-10-15T17:00:00Z", 20, 13),
        _hist("SYNTHETIC_2017_W08_NE_SD", 2017, 8, "NE", "SD", "2017-10-29T17:00:00Z", 16, 23),
        _hist("SYNTHETIC_2017_W12_MIA_STL", 2017, 12, "MIA", "STL", "2017-11-26T18:00:00Z", 14, 31),
        _hist("SYNTHETIC_2017_W14_BUF_NE", 2017, 14, "BUF", "NE", "2017-12-10T18:00:00Z", 10, 28),
        _hist("SYNTHETIC_2018_W01_SD_MIA", 2018, 1, "SD", "MIA", "2018-09-09T17:00:00Z", 27, 20),
        _hist("SYNTHETIC_2018_W02_STL_BUF", 2018, 2, "STL", "BUF", "2018-09-16T17:00:00Z", 24, 6),
        _hist("SYNTHETIC_2018_W03_BUF_SD", 2018, 3, "BUF", "SD", "2018-09-23T17:00:00Z", 13, 22),
        _hist("SYNTHETIC_2018_W04_MIA_STL", 2018, 4, "MIA", "STL", "2018-09-30T17:00:00Z", 17, 38),
        _hist("SYNTHETIC_2018_W05_SD_KC", 2018, 5, "SD", "KC", "2018-10-07T17:00:00Z", 20, 17),
        _hist("SYNTHETIC_2018_W05_STL_NE", 2018, 5, "STL", "NE", "2018-10-07T20:25:00Z", 13, 27),
    ]


def build_synthetic_r7_demo(*, mode: str = CHANNEL_SYNTHETIC) -> dict[str, Any]:
    """TNF-shaped fictional slate. Opt-in SYNTHETIC only."""
    refuse_real_mode(mode)
    available_at = "2018-10-11T20:00:00Z"
    observed_at = "2018-10-11T21:00:00Z"
    source = "SYNTHETIC_TYPED_PACKET_t5289u_R7"
    envelope = {
        "game_id": "SYNTHETIC_2018_W06_LAC_LAR",
        "season": 2018,
        "week": 6,
        "season_type": "REG",
        "home_team": "LAC",
        "away_team": "LAR",
        "kickoff_utc": "2018-10-12T00:20:00Z",
        "venue_id": "SYNTHETIC_VENUE_TNF",
        "identity_kind": "SYNTHETIC_REG",
    }
    history = synthetic_history()
    physical_schedule = synthetic_physical_schedule()
    franchises = franchise_bind(envelope["home_team"], envelope["away_team"])
    rest = bind_rest_from_et_calendar(
        home_team=envelope["home_team"],
        away_team=envelope["away_team"],
        kickoff_utc=str(envelope["kickoff_utc"]),
        physical_schedule=physical_schedule,
    )
    values: dict[str, Any] = {
        "game_id": envelope["game_id"],
        "home_team": "LAC",
        "away_team": "LAR",
        "matchup_season": 2018,
        "matchup_week": 6,
        "rest_days_home": rest["rest_days_home"],
        "rest_days_away": rest["rest_days_away"],
        "offense_index_home": 1.08,
        "offense_index_away": 1.03,
        "defense_index_home": 1.01,
        "defense_index_away": 1.04,
        "home_off_epa_5g": 0.07,
        "away_off_epa_5g": 0.03,
        "home_def_epa_allowed_5g": -0.01,
        "away_def_epa_allowed_5g": 0.02,
        "home_success_offense_5g": 0.48,
        "away_success_offense_5g": 0.46,
        "home_success_defense_allowed_5g": 0.44,
        "away_success_defense_allowed_5g": 0.45,
        "home_pass_rate_5g": 0.59,
        "away_pass_rate_5g": 0.57,
        "matchup_diff_off_epa_5g": 0.04,
        "matchup_diff_def_epa_allowed_5g": -0.03,
        "matchup_diff_success_rate_5g": 0.02,
        "matchup_diff_pressure_allowed_5g": -0.01,
        "matchup_diff_pressure_generated_5g": 0.02,
        "matchup_diff_red_zone_td_rate_5g": 0.03,
    }
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
        "franchise_bind": franchises,
        "rest_calendar": rest,
    }
    packet["source_byte_hash"] = packet_content_hash(packet)
    return {
        "channel": CHANNEL_SYNTHETIC,
        "packet": packet,
        "history": history,
        "physical_schedule": physical_schedule,
        "franchise_bind": franchises,
        "rest_calendar": rest,
        "c_formula_controls": [
            {"label": "CONTROL_A_IF2_Q24", "if_margin": 2.0, "q2_margin": 4.0, "expected_c": 3.0},
            {"label": "CONTROL_B_IF_NEG1_Q2_1", "if_margin": -1.0, "q2_margin": 1.0, "expected_c": 0.0},
        ],
    }


def refuse_if_real(mode: str, packet: dict[str, Any] | None = None) -> None:
    refuse_real_mode(mode, packet)
    if packet is not None and packet.get("real_mode_usable") is True:
        raise RealModeRefuse("R7 real_mode_usable refused")
