"""t5208u R6_CALLER_V1 — SYNTHETIC pure caller (CERT=0)."""

from __future__ import annotations

import ast
import hashlib
import math
from pathlib import Path

import pytest

from src.services.nfl_t5107u.builder import challenger_margin
from src.services.nfl_t5107u.if_control import REQUIRED_FIELDS
from src.services.nfl_t5107u.if_produce import IF_TIP, SEED_BASE, SEED_MOD, seed_for
from src.services.nfl_t5107u.q2 import SEALED_SEASONS
from src.services.nfl_t5107u.recon_contract import CONTRACT_27 as RECON_27
from src.services.nfl_t5208u.caller import CallerRefuse, call_r6_point_margin, replay_call
from src.services.nfl_t5208u.if_tree import (
    EnsureIfTreeForbidden,
    IFTreeBlocker,
    default_if_trees_status,
    disable_ensure_if_tree,
    preflight_if_tree,
)
from src.services.nfl_t5208u.packets import (
    RealModeRefuse,
    build_synthetic_demo,
    refuse_real_mode,
)
from src.services.nfl_t5208u.pins import (
    CANDIDATE_WEIGHT,
    CONTRACT_27,
    C_FORMULA,
    FW_SHA256,
    SIM_SHA256,
)
from src.services.nfl_t5208u.schema import assert_contract_27_exact, schema_document, schema_hash

R6_DIR = Path(__file__).resolve().parents[1] / "src" / "services" / "nfl_t5208u"
ALGO_DIR = Path(__file__).resolve().parents[1] / "src" / "services" / "nfl_t5107u"


def test_contract_27_frozen_from_recon_contract() -> None:
    assert CONTRACT_27 == RECON_27
    assert len(CONTRACT_27) == 27
    assert_contract_27_exact(CONTRACT_27)
    assert set(CONTRACT_27) == set(REQUIRED_FIELDS)


def test_schema_hash_stable() -> None:
    first = schema_hash(schema_document())
    second = schema_hash(schema_document())
    assert first == second
    assert len(first) == 64
    doc = schema_document()
    assert doc["c_formula"] == C_FORMULA
    assert doc["contract_27"] == list(CONTRACT_27)
    assert doc["n_contract_27"] == 27


def test_c_formula_synthetic_controls() -> None:
    assert challenger_margin(2.0, 4.0, w=CANDIDATE_WEIGHT) == 3.0
    assert challenger_margin(-1.0, 1.0, w=CANDIDATE_WEIGHT) == 0.0
    assert C_FORMULA == "C=0.5*IF+0.5*Q2"
    with pytest.raises(Exception):
        challenger_margin(2.0, 4.0, w=0.75)
    with pytest.raises(Exception):
        challenger_margin(2.0, 4.0, extra_hfa=1.0)
    with pytest.raises(Exception):
        challenger_margin(2.0, 4.0, market_blend=0.1)


def test_real_mode_refuse() -> None:
    demo = build_synthetic_demo()
    with pytest.raises(RealModeRefuse):
        refuse_real_mode("REAL", demo["packet"])
    with pytest.raises(RealModeRefuse):
        call_r6_point_margin(demo["packet"], demo["history"], mode="LIVE")
    broken = dict(demo["packet"], real_mode_usable=True)
    with pytest.raises(RealModeRefuse):
        refuse_real_mode("SYNTHETIC", broken)


def test_synthetic_label_required() -> None:
    demo = build_synthetic_demo()
    packet = dict(demo["packet"])
    packet["channel"] = "PROD"
    with pytest.raises(RealModeRefuse):
        refuse_real_mode("SYNTHETIC", packet)
    assert demo["packet"]["envelope"]["game_id"].startswith("SYNTHETIC")
    assert demo["packet"]["real_mode_usable"] is False


def test_if_tree_preflight_in_repo_pin_match() -> None:
    report = preflight_if_tree()
    assert report["status"] == "PRESENT_PIN_MATCH"
    assert report["sim_sha256"] == SIM_SHA256
    assert report["fw_sha256"] == FW_SHA256
    assert report["default_if_trees_used"] is False
    assert report["t5108u_if_tree_env"] is None
    defaults = default_if_trees_status()
    assert all(row["exists"] is False for row in defaults)


def test_ensure_if_tree_disabled() -> None:
    from src.services.nfl_t5107u import if_produce

    disable_ensure_if_tree()
    with pytest.raises(EnsureIfTreeForbidden):
        if_produce.ensure_if_tree()


def test_t5108u_env_bypass_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("T5108U_IF_TREE", "/tmp/should-not-use")
    with pytest.raises(IFTreeBlocker, match="T5108U_IF_TREE"):
        preflight_if_tree()


def test_seed_formula() -> None:
    game_id = "SYNTHETIC_2018_W05_KC_NE"
    expected = SEED_BASE + (int(hashlib.sha256(game_id.encode()).hexdigest()[:12], 16) % SEED_MOD)
    assert seed_for(game_id) == expected


def test_finite_if_q2_c_and_replay() -> None:
    demo = build_synthetic_demo()
    replay = replay_call(demo["packet"], demo["history"])
    first = replay["first"]
    assert replay["replay_ok"] is True
    for name in ("if_margin", "q2_margin", "c_margin"):
        assert isinstance(first[name], float)
        assert math.isfinite(first[name])
    assert first["output_kind"] == "POINT_MARGIN"
    assert first["market_blend"] == 0
    assert first["simulations"] == 4000
    assert first["seed"] == seed_for(first["game_id"])
    expected_c = 0.5 * first["if_margin"] + 0.5 * first["q2_margin"]
    assert abs(first["c_margin"] - expected_c) <= 1e-12
    assert first["if_margin"] == replay["second"]["if_margin"]
    assert first["q2_margin"] == replay["second"]["q2_margin"]
    assert first["c_margin"] == replay["second"]["c_margin"]
    assert first["seed"] == replay["second"]["seed"]
    assert "if_total_mu" not in first
    assert first["if_tip"] == IF_TIP


def test_point_margin_forbids_totals_ml_prob() -> None:
    demo = build_synthetic_demo()
    out = call_r6_point_margin(demo["packet"], demo["history"])
    blob = " ".join(out.keys()).lower()
    for token in ("moneyline", "ml", "total", "probability", "joint", "play", "lean"):
        assert token not in blob


def test_sealed_seasons_not_bypassed() -> None:
    assert 2024 in SEALED_SEASONS
    demo = build_synthetic_demo()
    env = dict(demo["packet"]["envelope"], season=2026)
    packet = dict(demo["packet"], envelope=env)
    with pytest.raises(Exception, match="SEALED"):
        call_r6_point_margin(packet, demo["history"])


def test_r6_sources_do_not_call_ensure_or_fetch() -> None:
    forbidden = ("git fetch", "git worktree add", "ensure_if_tree(")
    for path in sorted(R6_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if path.name == "if_tree.py" and token == "ensure_if_tree(":
                # wrapper assignment / forbidden stub only
                continue
            assert token not in text, f"{path.name} contains {token}"
    tree = ast.parse((R6_DIR / "if_tree.py").read_text(encoding="utf-8"))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "ensure_if_tree" not in calls


def test_algo_modules_are_pinned_files() -> None:
    for name in ("if_produce", "q2", "builder", "recon_contract", "if_control"):
        assert (ALGO_DIR / f"{name}.py").is_file()
    assert not (ALGO_DIR / "r5_496_freeze.py").exists()
    assert not (ALGO_DIR / "recon_driver.py").exists()
