"""t5213u R6 79264 RETURN — pre-model validation + actual hash binds (CERT=0)."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

from src.services.nfl_t5107u.if_produce import seed_for
from src.services.nfl_t5208u import caller as caller_mod
from src.services.nfl_t5208u.caller import call_r6_point_margin, model_spy_counts, reset_model_spy
from src.services.nfl_t5208u.hashing import require_sha256_hex
from src.services.nfl_t5208u.packets import PacketRefuse, RealModeRefuse, build_synthetic_demo
from src.services.nfl_t5208u.validate import (
    config_content_hash,
    history_content_hash,
    packet_content_hash,
    rehash_cell,
    rehash_packet,
    validate_before_model,
)


def _demo() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = build_synthetic_demo()
    return copy.deepcopy(raw["packet"]), copy.deepcopy(raw["history"])


def _rehash_all(packet: dict[str, Any]) -> dict[str, Any]:
    for cell in packet["contract_27"].values():
        rehash_cell(cell)
    return rehash_packet(packet)


def _spy_if(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    reset_model_spy()
    counts = {"produce_if_mu": 0, "asof_for_targets": 0}
    real_if = caller_mod.produce_if_mu
    real_asof = caller_mod.asof_for_targets

    def wrapped_if(*args: Any, **kwargs: Any) -> Any:
        counts["produce_if_mu"] += 1
        return real_if(*args, **kwargs)

    def wrapped_asof(*args: Any, **kwargs: Any) -> Any:
        counts["asof_for_targets"] += 1
        return real_asof(*args, **kwargs)

    monkeypatch.setattr(caller_mod, "produce_if_mu", wrapped_if)
    monkeypatch.setattr(caller_mod, "asof_for_targets", wrapped_asof)
    return counts


def test_positive_finite_if_q2_c_with_actual_hash_binds() -> None:
    packet, history = _demo()
    reset_model_spy()
    out = call_r6_point_margin(packet, history)
    for name in ("if_margin", "q2_margin", "c_margin"):
        assert isinstance(out[name], float)
        assert math.isfinite(out[name])
    assert abs(out["c_margin"] - (0.5 * out["if_margin"] + 0.5 * out["q2_margin"])) <= 1e-12
    assert out["seed"] == seed_for(out["game_id"])
    assert out["cutoff_utc"] == "2018-10-14T16:00:00Z"
    assert out["seal_utc"] == out["cutoff_utc"]
    assert out["kickoff_utc"] == "2018-10-14T17:00:00Z"
    assert out["packet_hash"] == packet_content_hash(packet)
    assert out["history_hash"] == history_content_hash(history)
    assert out["config_hash"] == config_content_hash()
    for key in ("packet_hash", "history_hash", "config_hash", "code_hash"):
        require_sha256_hex(out[key], name=key)
        assert out[key] != out["schema_hash"]
        assert out[key] != "0" * 64
        assert out["binds"][key] == out[key]
    assert out["binds"]["schema_hash_is_not_an_input_bind"] is True
    assert model_spy_counts()["produce_if_mu"] == 1
    bound = validate_before_model(packet, history)
    assert bound["packet_hash"] == out["packet_hash"]


def test_real_mode_refuse_zero_model_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    packet, history = _demo()
    counts = _spy_if(monkeypatch)
    with pytest.raises(RealModeRefuse):
        call_r6_point_margin(packet, history, mode="LIVE")
    assert counts["produce_if_mu"] == 0
    assert counts["asof_for_targets"] == 0
    assert model_spy_counts()["produce_if_mu"] == 0


@pytest.mark.parametrize(
    "mutator,match",
    [
        (
            lambda p, _h: p["contract_27"].pop("rest_days_home"),
            "missing",
        ),
        (
            lambda p, _h: p["contract_27"]["rest_days_home"].pop("available_at"),
            "missing metadata",
        ),
        (
            lambda p, _h: (
                p["contract_27"]["rest_days_home"].__setitem__("reconstructed_value", True),
                _rehash_all(p),
            ),
            "bool-as-number",
        ),
        (
            lambda p, _h: (
                p["contract_27"]["offense_index_home"].__setitem__(
                    "reconstructed_value", float("nan")
                ),
                _rehash_all(p),
            ),
            "not finite",
        ),
        (
            lambda p, _h: (
                p["contract_27"]["rest_days_away"].__setitem__("reconstructed_value", float("inf")),
                _rehash_all(p),
            ),
            "not finite",
        ),
        (
            lambda p, _h: (
                p["contract_27"]["home_off_epa_5g"].__setitem__("available_at", "2018-10-14T16:15:00Z"),
                p["contract_27"]["home_off_epa_5g"].__setitem__("observed_at", "2018-10-14T16:30:00Z"),
                _rehash_all(p),
            ),
            "late vs KO",
        ),
        (
            lambda p, _h: (
                p["contract_27"]["home_off_epa_5g"].__setitem__("available_at", "2018-10-14T15:00:00Z"),
                p["contract_27"]["home_off_epa_5g"].__setitem__("observed_at", "2018-10-14T16:00:00Z"),
                _rehash_all(p),
            ),
            "equal-to-seal",
        ),
        (
            lambda p, _h: (
                p["envelope"].__setitem__("game_id", "SYNTHETIC_2018_W05_OTHER"),
                _rehash_all(p),
            ),
            "identity mismatch",
        ),
        (
            lambda p, _h: (
                p["envelope"].__setitem__("season_type", "POST"),
                _rehash_all(p),
            ),
            "bad REG identity",
        ),
        (
            lambda p, _h: (
                p["envelope"].__setitem__("kickoff_utc", "not-a-time"),
                _rehash_all(p),
            ),
            "not a time",
        ),
        (
            lambda p, _h: p["contract_27"]["defense_index_home"].__setitem__(
                "source_byte_hash", "abcd1234"
            ),
            "not a full sha256",
        ),
        (
            lambda p, _h: p["contract_27"]["defense_index_home"].__setitem__(
                "source_byte_hash", "0" * 64
            ),
            "empty/default zero hash",
        ),
        (
            lambda p, _h: p["contract_27"]["defense_index_home"].__setitem__(
                "reconstructed_value", 9.99
            ),
            "wrong source_byte_hash",
        ),
        (
            lambda p, _h: p.__setitem__("source_byte_hash", "11" * 32),
            "packet wrong source_byte_hash",
        ),
        (
            lambda _p, h: h[0].__setitem__("kickoff_utc", "not-a-time"),
            "not a time",
        ),
        (
            lambda _p, h: (
                h[0].__setitem__("home_score", True),
            ),
            "bool-as-number",
        ),
        (
            lambda _p, h: h[0].__setitem__("season_type", "POST"),
            "is not REG",
        ),
        (
            lambda _p, h: h[0].__setitem__("game_id", "2017_W02_KC_BUF"),
            "not SYNTHETIC-prefixed",
        ),
    ],
)
def test_invalid_input_zero_model_calls(
    monkeypatch: pytest.MonkeyPatch, mutator: Any, match: str
) -> None:
    packet, history = _demo()
    mutator(packet, history)
    counts = _spy_if(monkeypatch)
    with pytest.raises((PacketRefuse, RealModeRefuse, ValueError), match=match):
        call_r6_point_margin(packet, history)
    assert counts["produce_if_mu"] == 0
    assert counts["asof_for_targets"] == 0
    assert model_spy_counts()["produce_if_mu"] == 0
    assert model_spy_counts()["asof_for_targets"] == 0


def test_validate_before_model_does_not_import_simulator(monkeypatch: pytest.MonkeyPatch) -> None:
    packet, history = _demo()
    reset_model_spy()

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("produce_if_mu must not run during validate_before_model")

    monkeypatch.setattr(caller_mod, "produce_if_mu", boom)
    bound = validate_before_model(packet, history)
    require_sha256_hex(bound["packet_hash"], name="packet_hash")
    assert bound["validated"] is True
    assert model_spy_counts()["produce_if_mu"] == 0
