"""Produce reconstructed IF μ from frozen tree 6ca03716 (do not consume a supplied μ).

Fetches the pinned simulator via ordinary git worktree / repo path.
Pins: simulator 52d9e909 · framework a0051cc4 · consume 19c6a4607 / 8155fd194.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
SIM_SHA256 = "52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385"
FW_SHA256 = "a0051cc423bd733c3342272fdb297ea8f22cf2a4569fe0f9ca0ec47eda04d0e3"
SEED_BASE = 201710
SEED_MOD = 1000003
SIMULATIONS = 4000
MARKET_BLEND = 0
FORBIDDEN_REST_NAMES = (
    "rest_days_from_schedule",
    "verify_rest_days",
    "nfl_offline_if_eval_w8",
)

DEFAULT_IF_TREES = (
    Path("/tmp/t5108u-if-6ca03716/services/model-service"),
    Path("/tmp/t5044u-if-6ca03716/services/model-service"),
    Path("/tmp/t4910u-if-6ca03716/services/model-service"),
)


class IFProduceRefuse(ValueError):
    """Fail-closed produce-μ."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seed_for(game_id: str) -> int:
    return SEED_BASE + (int(hashlib.sha256(game_id.encode()).hexdigest()[:12], 16) % SEED_MOD)


def locate_if_tree(explicit: Path | None = None) -> Path:
    candidates = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env = os.environ.get("T5108U_IF_TREE")
    if env:
        candidates.append(Path(env))
    candidates.extend(DEFAULT_IF_TREES)
    for path in candidates:
        if (path / "src" / "services" / "nfl_simulator.py").is_file():
            return path
    mounted = ensure_if_tree()
    if (mounted / "src" / "services" / "nfl_simulator.py").is_file():
        return mounted
    raise IFProduceRefuse(
        "frozen IF tree 6ca03716 not found after git fetch; expected worktree at "
        "/tmp/t5108u-if-6ca03716 (git worktree add --detach "
        "6ca03716fe52930332d5ffba302c312a651980cc)"
    )


def ensure_if_tree() -> Path:
    """Fetch pinned IF tip via ordinary git worktree. Sparse-not-mounted is not a blocker."""
    dest = Path("/tmp/t5108u-if-6ca03716")
    sim = dest / "services" / "model-service" / "src" / "services" / "nfl_simulator.py"
    if sim.is_file():
        return dest / "services" / "model-service"
    repo = None
    for candidate in (
        Path("/Users/ryankos/kosedge"),
        Path(__file__).resolve().parents[5],
        Path.cwd(),
    ):
        if (candidate / ".git").exists() or (candidate / ".git").is_file():
            repo = candidate
            break
    if repo is None:
        raise IFProduceRefuse("cannot locate kosedge git repo to fetch IF tip 6ca03716")
    dest.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "fetch", "--no-tags", "origin", IF_TIP],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(dest), IF_TIP],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise IFProduceRefuse(f"git worktree add {IF_TIP} failed: {exc.stderr or exc}") from exc
    if not sim.is_file():
        # Detached worktree root is dest; model-service lives under services/.
        alt = dest / "src" / "services" / "nfl_simulator.py"
        if alt.is_file():
            return dest
        raise IFProduceRefuse(f"IF tip {IF_TIP} checked out but nfl_simulator.py missing")
    return dest / "services" / "model-service"


def import_frozen_if(tree: Path | None = None) -> Any:
    root = locate_if_tree(tree)
    sim_path = root / "src" / "services" / "nfl_simulator.py"
    fw_path = root / "src" / "services" / "nfl_handicapping_framework.py"
    sim_sha = sha256_file(sim_path)
    fw_sha = sha256_file(fw_path)
    if sim_sha != SIM_SHA256:
        raise IFProduceRefuse(f"simulator sha {sim_sha} != 52d9e909 pin")
    if fw_sha != FW_SHA256:
        raise IFProduceRefuse(f"framework sha {fw_sha} != a0051cc4 pin")
    src = sim_path.read_text(encoding="utf-8")
    for name in FORBIDDEN_REST_NAMES:
        if name in src:
            raise IFProduceRefuse(f"IF simulator source mentions forbidden rest helper {name}")

    token = f"if_pin_{IF_TIP[:8]}"
    cached = sys.modules.get(f"{token}.services.nfl_simulator")
    if cached is not None:
        return cached

    # Load the pinned tree as an isolated package so it cannot bind our src.services.
    if token not in sys.modules:
        pkg = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(token, loader=None)  # type: ignore[arg-type]
        )
        pkg.__path__ = [str(root / "src")]  # type: ignore[attr-defined]
        sys.modules[token] = pkg
        svc = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(f"{token}.services", loader=None)  # type: ignore[arg-type]
        )
        svc.__path__ = [str(root / "src" / "services")]  # type: ignore[attr-defined]
        sys.modules[f"{token}.services"] = svc

    def _load(mod_name: str, file_path: Path) -> Any:
        full = f"{token}.services.{mod_name}"
        if full in sys.modules:
            return sys.modules[full]
        source = file_path.read_text(encoding="utf-8")
        source = source.replace("from src.services.", f"from {token}.services.")
        source = source.replace("import src.services.", f"import {token}.services.")
        module = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(full, loader=None)  # type: ignore[arg-type]
        )
        module.__file__ = str(file_path)
        module.__package__ = f"{token}.services"
        sys.modules[full] = module
        exec(compile(source, str(file_path), "exec"), module.__dict__)
        return module

    _load("nfl_second_order_factors", root / "src" / "services" / "nfl_second_order_factors.py")
    _load("nfl_handicapping_framework", fw_path)
    sim = _load("nfl_simulator", sim_path)
    return sim


def _cell(packet: Mapping[str, Any], name: str) -> Any:
    cell = packet.get(name)
    if isinstance(cell, Mapping):
        if str(cell.get("status") or "") != "DERIVED_PREGAME":
            raise IFProduceRefuse(f"{name} is not DERIVED_PREGAME")
        return cell.get("reconstructed_value", cell.get("value"))
    return cell


def produce_if_mu(
    packet: Mapping[str, Any],
    *,
    tree: Path | None = None,
    simulations: int | None = None,
    config_overrides: Mapping[str, Any] | None = None,
    apply_linear_totals_calibration: bool | None = None,
    totals_settings: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Run frozen IF @ 6ca03716 on a complete DERIVED_PREGAME packet. Produces μ."""
    from .if_control import REQUIRED_FIELDS, missing_required_fields

    missing = missing_required_fields(packet)
    if missing:
        raise IFProduceRefuse("incomplete recon packet: " + ", ".join(missing))

    game_id = str(_cell(packet, "game_id"))
    kwargs: dict[str, Any] = {}
    for name in REQUIRED_FIELDS:
        value = _cell(packet, name)
        if name in {"game_id", "home_team", "away_team"}:
            kwargs[name] = str(value)
        elif name in {"matchup_season", "matchup_week"}:
            kwargs[name] = int(value)
        else:
            kwargs[name] = float(value)

    sim = import_frozen_if(tree)
    inputs = sim.NflGameInputs(**kwargs)
    if float(inputs.rest_days_home) != float(kwargs["rest_days_home"]):
        raise IFProduceRefuse(f"{game_id} rest_days_home not bound from packet")
    if float(inputs.rest_days_away) != float(kwargs["rest_days_away"]):
        raise IFProduceRefuse(f"{game_id} rest_days_away not bound from packet")
    seed = seed_for(game_id)
    sims = SIMULATIONS if simulations is None else int(simulations)
    cal_flag = True if apply_linear_totals_calibration is None else bool(apply_linear_totals_calibration)
    totals_token = None
    if totals_settings is not None:
        from src.services.nfl_r7_correctness_v1.config_adapter import (
            install_totals_adapter,
            push_totals_settings,
            reset_totals_settings,
        )

        install_totals_adapter(sim)
        totals_token = push_totals_settings(totals_settings)
    try:
        projection = sim.simulate_nfl_game_independent_fair(
            inputs,
            simulations=sims,
            seed=seed,
            market_spread_home=None,
            market_total=None,
            config_overrides=dict(config_overrides) if config_overrides is not None else None,
            apply_linear_totals_calibration=cal_flag,
        )
    finally:
        if totals_token is not None:
            reset_totals_settings(totals_token)
    block = projection.get("independent_fair") or {}
    if block.get("market_blend") != MARKET_BLEND:
        raise IFProduceRefuse(f"{game_id} market_blend {block.get('market_blend')} != 0")
    margin_mu, total_mu = sim.independent_fair_mus(projection)
    if not isinstance(margin_mu, (int, float)):
        raise IFProduceRefuse(f"{game_id} non-finite IF mu")
    return {
        "game_id": game_id,
        "if_margin_mu": float(margin_mu),
        "if_total_mu": float(total_mu),
        "if_sigma": float(block.get("sigma") or 0.0),
        "seed": seed,
        "simulations": sims,
        "market_blend": 0,
        "if_tip": IF_TIP,
        "if_forecast_label": projection.get("forecast_label"),
        "source": "reconstructed_if_produce",
        "if_tree": str(locate_if_tree(tree)),
        "apply_linear_totals_calibration": cal_flag,
        "totals_settings_forwarded": totals_settings is not None,
    }
