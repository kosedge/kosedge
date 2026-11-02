"""t5218u R6 timing delta — seal=cutoff=KO−60, strictly precede (CERT=0)."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.services.nfl_t5208u import caller as caller_mod
from src.services.nfl_t5208u.caller import call_r6_point_margin, model_spy_counts, reset_model_spy
from src.services.nfl_t5208u.packets import PacketRefuse, build_synthetic_demo
from src.services.nfl_t5208u.pins import KO_MINUS_MINUTES
from src.services.nfl_t5208u.validate import rehash_cell, rehash_packet, validate_before_model

KO = datetime(2018, 10, 14, 17, 0, tzinfo=timezone.utc)
CUTOFF = KO - timedelta(minutes=KO_MINUS_MINUTES)
CUTOFF_MINUS_1S = CUTOFF - timedelta(seconds=1)
CUTOFF_PLUS_1S = CUTOFF + timedelta(seconds=1)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _demo() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = build_synthetic_demo()
    return copy.deepcopy(raw["packet"]), copy.deepcopy(raw["history"])


def _set_all_cell_times(packet: dict[str, Any], available: str, observed: str) -> dict[str, Any]:
    for cell in packet["contract_27"].values():
        cell["available_at"] = available
        cell["observed_at"] = observed
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


def test_cutoff_minus_1s_valid_before_and_through_model() -> None:
    packet, history = _demo()
    _set_all_cell_times(packet, _fmt(CUTOFF_MINUS_1S), _fmt(CUTOFF_MINUS_1S))
    reset_model_spy()
    bound = validate_before_model(packet, history)
    assert bound["seal_utc"] == bound["cutoff_utc"] == _fmt(CUTOFF)
    assert bound["kickoff_utc"] == _fmt(KO)
    assert model_spy_counts()["produce_if_mu"] == 0
    out = call_r6_point_margin(packet, history)
    assert out["seal_utc"] == out["cutoff_utc"] == _fmt(CUTOFF)
    assert out["kickoff_utc"] == _fmt(KO)
    assert out["if_margin"] == pytest.approx(0.8675824382397918)
    assert out["q2_margin"] == pytest.approx(1.2472862060776504)
    assert out["c_margin"] == pytest.approx(1.057434322158721)
    assert out["seed"] == 282632


@pytest.mark.parametrize(
    "stamp,match",
    [
        (_fmt(CUTOFF), "equal-to-seal"),
        (_fmt(CUTOFF_PLUS_1S), "late vs KO"),
    ],
)
def test_cutoff_and_after_refuse_before_model(
    monkeypatch: pytest.MonkeyPatch, stamp: str, match: str
) -> None:
    packet, history = _demo()
    _set_all_cell_times(packet, _fmt(CUTOFF_MINUS_1S), stamp)
    counts = _spy_if(monkeypatch)
    with pytest.raises(PacketRefuse, match=match):
        validate_before_model(packet, history)
    with pytest.raises(PacketRefuse, match=match):
        call_r6_point_margin(packet, history)
    assert counts["produce_if_mu"] == 0
    assert counts["asof_for_targets"] == 0
    assert model_spy_counts()["produce_if_mu"] == 0


def test_history_kickoff_at_cutoff_refused_before_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet, history = _demo()
    history[0]["kickoff_utc"] = _fmt(CUTOFF)
    counts = _spy_if(monkeypatch)
    with pytest.raises(PacketRefuse, match="strictly < cutoff/seal"):
        validate_before_model(packet, history)
    assert counts["produce_if_mu"] == 0
    assert model_spy_counts()["produce_if_mu"] == 0
