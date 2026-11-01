#!/usr/bin/env python3
"""CLEAR-P1 local D3-fixture shadow orchestrator (t4768u / DECISION 23c825de).

D3 fixture → Independent Fair (market_blend=0) → L0 → L1 (honest missing)
→ pinned L4 → auditable receipt.

Local fixture only. No live callers, HF layer, DDL, Odds, Railway/C10,
overlays, or public paint. P2/P3 HOLD. H-IFT-1 E2/E3 not executed.

Usage
-----
  PYTHONPATH=services/model-service python3 scripts/nfl/shadow_handicap_e2e_t4761u.py \\
      --out data/ops/nfl-shadow-e2e-t4768u
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

REPO = Path(__file__).resolve().parents[2]
MS_SRC = REPO / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))

# Import-time guard used by several model-service modules. Never a live DSN.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_handicap_ledger import (  # noqa: E402
    FORECAST_HANDICAP_DELTA,
    FORECAST_INDEPENDENT_FAIR,
    FORECAST_MARKET_INFORMED_FAIR,
    L0_LAYER,
    L1_LAYER,
    L4_LAYER,
    LEDGER_SCHEMA_VERSION,
    AppendOnlyHandicapLedger,
    HandicapLedgerReject,
    commit_l1_stage,
)
from src.services.nfl_simulator import (  # noqa: E402
    DEFAULT_NFL_MODEL_VERSION,
    INDEPENDENT_FAIR_FORECAST_LABEL,
    NFL_INDEPENDENT_FAIR_PATH,
    NflGameInputs,
    independent_fair_mus,
    simulate_nfl_game,
    simulate_nfl_game_independent_fair,
)

# --- D3 pins (test_nfl_handicap_clear_a_d3.py). Do not expand the slate. ---
D3II_FIXED_SEED = 47401
D3II_SIMULATIONS = 800
D3II_MARKET_SPREAD_HOME = 3.5
D3II_MARKET_TOTAL = 43.5
D3II_BASELINE_SHA256 = "75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224"
D3_GAME_ID = "d3ii-clear-a-baseline"
D3_HOME = "CLE"
D3_AWAY = "BAL"
D3_SEASON = 2026
D3_WEEK = 8

# Frozen ledger clocks — not wall time — so receipt + JSONL are reproducible.
AS_OF_TS = "2026-10-29T15:00:00Z"
DECISION_TS = "2026-10-29T16:00:00Z"
CAPTURED_AT = "2026-10-29T15:30:00Z"
CREATED_AT = "2026-10-29T16:00:00Z"

CAPTURE_ID = "cap-d3ii-t4761u"
# L1 business identity does not include `factor`. Per-factor capture suffixes
# keep injury_availability and weather as distinct append-only rows.
L1_CAPTURE_PREFIX = "cap-d3ii-t4761u#l1#"
SOURCE_SNAPSHOT_ID = "snap-d3ii-t4761u"
REGISTRY_ID = "reg-clear-a-p1"
BASELINE_PERSONNEL_REF = "baseline-personnel-ref-dev"
# Explicit fixture constants (plan §P1 step 4). Not imputed from sim fields.
L0_EFF_PACE = 1.0
MARKET_SNAPSHOT_ID = "pin-d3ii-3.5-43.5"

# Frozen allow-list already used in CLEAR-A tests. No new factors. P2 HOLD.
L1_ALLOWLIST_FACTORS = ("injury_availability", "weather")
L1_ENTRY_POINT = "points"

PUBLIC_CONTROL_FILE = REPO / "apps" / "web" / "lib" / "cfb-edge-board-public.ts"

AUTHORITY = {
    "decision": "23c825de",
    "order": "a39c8f63",
    "plan_sha8": "69b9ef5f",
    "ticket": "t4768u",
    "clear": "CLEAR-P1",
    "schema_version": LEDGER_SCHEMA_VERSION,
}


class ShadowE2EReject(ValueError):
    """Fail-closed orchestrator reject. Callers must not impute."""


def d3_inputs() -> NflGameInputs:
    """Exact D3 fixture. Missing required identity ⇒ REJECT (no impute)."""
    if not D3_GAME_ID or not D3_HOME or not D3_AWAY:
        raise ShadowE2EReject("D3 fixture missing game/team identity (no impute)")
    return NflGameInputs(
        game_id=D3_GAME_ID,
        home_team=D3_HOME,
        away_team=D3_AWAY,
        offense_index_home=0.96,
        offense_index_away=1.05,
        defense_index_home=1.04,
        defense_index_away=0.98,
        rest_days_home=7.0,
        rest_days_away=6.0,
        matchup_season=D3_SEASON,
        matchup_week=D3_WEEK,
    )


def d3_sim_kwargs() -> Dict[str, Any]:
    return {
        "simulations": D3II_SIMULATIONS,
        "seed": D3II_FIXED_SEED,
        "market_spread_home": D3II_MARKET_SPREAD_HOME,
        "market_total": D3II_MARKET_TOTAL,
    }


def canonical_sha256(obj: object) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()


def _require_finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShadowE2EReject(f"{name} missing or non-numeric (no impute)")
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise ShadowE2EReject(f"{name} not finite (no impute)")
    return out


def assert_independent_fair_path_off() -> None:
    if NFL_INDEPENDENT_FAIR_PATH is not False:
        raise ShadowE2EReject("NFL_INDEPENDENT_FAIR_PATH must stay False (unread by sim)")


def assert_distribution_valid(if_out: Mapping[str, Any]) -> Dict[str, Any]:
    """P1b: finite mus, σ>0, quantile order, win probs in (0,1), blend exact 0."""
    block = if_out.get("independent_fair")
    if not isinstance(block, dict):
        raise ShadowE2EReject("Independent Fair block missing (no impute)")
    if block.get("forecast_label") != INDEPENDENT_FAIR_FORECAST_LABEL:
        raise ShadowE2EReject("Independent Fair forecast_label missing")
    blend = block.get("market_blend")
    if isinstance(blend, bool) or blend != 0:
        raise ShadowE2EReject("Independent Fair market_blend must be exact 0")
    margin_mu, total_mu = independent_fair_mus(dict(if_out))
    _require_finite("margin_mu", margin_mu)
    _require_finite("total_mu", total_mu)
    sigma = _require_finite("sigma", block.get("sigma"))
    if sigma <= 0:
        raise ShadowE2EReject("sigma must be > 0")
    markets = if_out.get("markets")
    if not isinstance(markets, dict):
        raise ShadowE2EReject("markets missing (no impute)")
    p10 = _require_finite("total_p10", markets.get("total_p10"))
    p50 = _require_finite("total_p50", markets.get("total_p50"))
    p90 = _require_finite("total_p90", markets.get("total_p90"))
    if not (p10 <= p50 <= p90):
        raise ShadowE2EReject("total_p10 <= total_p50 <= total_p90 failed")
    home_p = _require_finite("home_win_prob", markets.get("home_win_prob"))
    away_p = _require_finite("away_win_prob", markets.get("away_win_prob"))
    if not (0.0 < home_p < 1.0 and 0.0 < away_p < 1.0):
        raise ShadowE2EReject("win probs must be in (0, 1)")
    if abs((home_p + away_p) - 1.0) > 1e-6:
        raise ShadowE2EReject("win probs must sum to 1")
    return {
        "margin_mu": margin_mu,
        "total_mu": total_mu,
        "sigma": sigma,
        "market_blend": 0,
        "total_p10": p10,
        "total_p50": p50,
        "total_p90": p90,
        "home_win_prob": home_p,
        "away_win_prob": away_p,
        "markets_total_mean": _require_finite("total_mean", markets.get("total_mean")),
        "r1_f8_note": (
            "markets.total_mean may differ from independent_fair.total_mu "
            "because linear totals calibration still runs on markets (R1/F8)."
        ),
    }


def read_publication_control_pins(
    path: Path = PUBLIC_CONTROL_FILE,
) -> Dict[str, str]:
    """Parse Coming Soon / CERT=0 constants from source. Fail-closed on miss."""
    if not path.is_file():
        raise ShadowE2EReject(f"publication control file missing: {path}")
    text = path.read_text(encoding="utf-8")
    required = {
        "NFL_EDGE_BOARD_PUBLIC_ENABLED": r"export const NFL_EDGE_BOARD_PUBLIC_ENABLED = false;",
        "NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED": r"export const NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED = false;",
        "NFL_FAIR_LINES_PUBLIC_ML_ENABLED": r"export const NFL_FAIR_LINES_PUBLIC_ML_ENABLED = false;",
        "NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED": r"export const NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED = false;",
        "NFL_FAIR_LINES_PLAY_ENABLED": r"export const NFL_FAIR_LINES_PLAY_ENABLED = false;",
        "NFL_FAIR_LINES_KELLY_ENABLED": r"export const NFL_FAIR_LINES_KELLY_ENABLED = false;",
        "NFL_FAIR_LINES_CERTIFIED_RUN_ID": r"export const NFL_FAIR_LINES_CERTIFIED_RUN_ID: string \| null = null;",
        "NFL_FAIR_LINES_CERTIFIED_SHA256": r"export const NFL_FAIR_LINES_CERTIFIED_SHA256: string \| null = null;",
        "NFL_FAIR_LINES_CERTIFIED_AT": r"export const NFL_FAIR_LINES_CERTIFIED_AT: string \| null = null;",
        "FOOTBALL_PUBLIC_NUMBERS_HEADING": r'export const FOOTBALL_PUBLIC_NUMBERS_HEADING = "Coming soon";',
    }
    found: Dict[str, str] = {}
    for name, pattern in required.items():
        if not re.search(pattern, text):
            raise ShadowE2EReject(f"publication control pin missing or flipped: {name}")
        found[name] = "pinned"
    found["coming_soon"] = "ON"
    found["cert"] = "0"
    found["public_paint"] = "closed"
    found["source"] = str(path.relative_to(REPO))
    return found


def assert_local_only_source(source_path: Path = Path(__file__)) -> None:
    """Refuse live-caller / paid-odds / overlay unlock imports in this file."""
    for line in source_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("from ", "import ")):
            if any(needle in stripped for needle in ("odds_api", "src.tasks", "src.routes")):
                raise ShadowE2EReject(f"local-only import refuse: {stripped}")
        compact = stripped.replace(" ", "")
        unlock_needle = "unlock_" + "overlays=" + "True"
        if unlock_needle in compact:
            raise ShadowE2EReject("local-only refuse overlay unlock")
        c10_needle = "confirm_" + "c10_clear"
        if c10_needle in stripped:
            raise ShadowE2EReject("local-only refuse C10 dispatch")


def build_l0_row(dist: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "game_id": D3_GAME_ID,
        "model_version": DEFAULT_NFL_MODEL_VERSION,
        "as_of_ts": AS_OF_TS,
        "capture_id": CAPTURE_ID,
        "baseline_personnel_ref": BASELINE_PERSONNEL_REF,
        "off_eff_h": L0_EFF_PACE,
        "off_eff_a": L0_EFF_PACE,
        "def_eff_h": L0_EFF_PACE,
        "def_eff_a": L0_EFF_PACE,
        "pace_h": L0_EFF_PACE,
        "pace_a": L0_EFF_PACE,
        "margin_mu": dist["margin_mu"],
        "total_mu": dist["total_mu"],
        "sigma": dist["sigma"],
        "market_blend": 0,
        "forecast_label": FORECAST_INDEPENDENT_FAIR,
        "decision_ts": DECISION_TS,
        "created_at": CREATED_AT,
        "source_snapshot_id": SOURCE_SNAPSHOT_ID,
        "registry_id": REGISTRY_ID,
    }


def l1_capture_id(factor: str) -> str:
    if factor not in L1_ALLOWLIST_FACTORS:
        raise ShadowE2EReject(f"L1 factor not on frozen allow-list: {factor!r}")
    return f"{L1_CAPTURE_PREFIX}{factor}"


def build_l1_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for factor in L1_ALLOWLIST_FACTORS:
        rows.append(
            {
                "game_id": D3_GAME_ID,
                "capture_id": l1_capture_id(factor),
                "as_of_ts": AS_OF_TS,
                "baseline_ref": BASELINE_PERSONNEL_REF,
                "registry_id": REGISTRY_ID,
                "source_snapshot_id": SOURCE_SNAPSHOT_ID,
                "factor": factor,
                "entry_point": L1_ENTRY_POINT,
                "delta": 0.0,
                "uncertainty": 0.0,
                "missing": True,
                "missingness": {factor: True},
                "forecast_label": FORECAST_HANDICAP_DELTA,
                "decision_ts": DECISION_TS,
                "created_at": CREATED_AT,
                "model_version": DEFAULT_NFL_MODEL_VERSION,
            }
        )
    return rows


def build_l4_row(dist: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "game_id": D3_GAME_ID,
        "as_of_ts": AS_OF_TS,
        "capture_id": CAPTURE_ID,
        "forecast_label": FORECAST_MARKET_INFORMED_FAIR,
        "market_snapshot_id": MARKET_SNAPSHOT_ID,
        "captured_at": CAPTURED_AT,
        "decision_ts": DECISION_TS,
        "created_at": CREATED_AT,
        "source_snapshot_id": SOURCE_SNAPSHOT_ID,
        "registry_id": REGISTRY_ID,
        "baseline_ref": BASELINE_PERSONNEL_REF,
        "model_version": DEFAULT_NFL_MODEL_VERSION,
        "pinned_market_spread_home": D3II_MARKET_SPREAD_HOME,
        "pinned_market_total": D3II_MARKET_TOTAL,
        "if_margin_mu": dist["margin_mu"],
        "if_total_mu": dist["total_mu"],
        "spread_delta_if_minus_pinned": round(
            (-float(dist["margin_mu"])) - D3II_MARKET_SPREAD_HOME, 4
        ),
        "total_delta_if_minus_pinned": round(
            float(dist["total_mu"]) - D3II_MARKET_TOTAL, 4
        ),
        "used_as_fair": False,
        "note": "Pinned D3 market compare only. L5 never reads MIF as fair.",
    }


def run_shadow_p1(out_dir: Path) -> Dict[str, Any]:
    """Run the local slice. Writes ledger JSONL + receipt JSON under out_dir."""
    assert_independent_fair_path_off()
    assert_local_only_source()
    pub = read_publication_control_pins()

    inputs = d3_inputs()
    kwargs = d3_sim_kwargs()

    blended = simulate_nfl_game(inputs, **kwargs)
    blended_sha = canonical_sha256(blended)
    if blended_sha != D3II_BASELINE_SHA256:
        raise ShadowE2EReject(
            f"D3(ii) SHA drift: {blended_sha} != {D3II_BASELINE_SHA256}"
        )
    if "independent_fair" in blended or "forecast_label" in blended:
        raise ShadowE2EReject("default path must not carry IF chrome")

    if_out = simulate_nfl_game_independent_fair(inputs, **kwargs)
    dist = assert_distribution_valid(if_out)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "ledger.jsonl"
    receipt_path = out_dir / "receipt.json"
    if ledger_path.exists():
        ledger_path.unlink()

    store = AppendOnlyHandicapLedger(ledger_path)
    l0_written = store.append_layer(
        build_l0_row(dist),
        layer=L0_LAYER,
        forecast_label=FORECAST_INDEPENDENT_FAIR,
        decision_ts=DECISION_TS,
    )
    l1_written = commit_l1_stage(store, build_l1_rows(), decision_ts=DECISION_TS)
    l4_written = store.append_layer(
        build_l4_row(dist),
        layer=L4_LAYER,
        forecast_label=FORECAST_MARKET_INFORMED_FAIR,
        decision_ts=DECISION_TS,
    )

    labels = [str(row.get("forecast_label")) for row in store.rows()]
    if FORECAST_HANDICAP_DELTA not in labels:
        raise ShadowE2EReject("L1 handicap_delta missing")
    if any(label == "handicapped_fair" for label in labels):
        raise ShadowE2EReject("HF row written (P3 HOLD)")
    layers = [str(row.get("layer")) for row in store.rows()]
    if layers.count(L0_LAYER) != 1 or layers.count(L4_LAYER) != 1:
        raise ShadowE2EReject("expected exactly 1 L0 and 1 L4")
    if layers.count(L1_LAYER) != len(L1_ALLOWLIST_FACTORS):
        raise ShadowE2EReject("L1 allow-list row count mismatch")

    # Reload must re-validate (R7 clean).
    reloaded = AppendOnlyHandicapLedger(ledger_path)
    if len(reloaded) != len(store):
        raise ShadowE2EReject("JSONL reload row-count mismatch")

    receipt: Dict[str, Any] = {
        "authority": AUTHORITY,
        "locks": {
            "nfl_nogo": True,
            "cert": 0,
            "coming_soon": "ON",
            "f2_frozen": True,
            "c10_hold": True,
            "overlays_off": True,
            "p2_p3_hold": True,
            "h_ift1_e2_e3_not_executed": True,
        },
        "fixture": {
            "game_id": D3_GAME_ID,
            "home": D3_HOME,
            "away": D3_AWAY,
            "season": D3_SEASON,
            "week": D3_WEEK,
            "seed": D3II_FIXED_SEED,
            "simulations": D3II_SIMULATIONS,
            "pinned_market_spread_home": D3II_MARKET_SPREAD_HOME,
            "pinned_market_total": D3II_MARKET_TOTAL,
        },
        "independent_fair": {
            "forecast_label": INDEPENDENT_FAIR_FORECAST_LABEL,
            "market_blend": 0,
            "margin_mu": dist["margin_mu"],
            "total_mu": dist["total_mu"],
            "sigma": dist["sigma"],
            "nfl_independent_fair_path": False,
        },
        "distribution": dist,
        "blended_default_path": {
            "sha256": blended_sha,
            "pin": D3II_BASELINE_SHA256,
            "match": blended_sha == D3II_BASELINE_SHA256,
            "has_if_chrome": False,
        },
        "ledger": {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "path": str(ledger_path),
            "l0_prediction_id": l0_written["prediction_id"],
            "l1_prediction_ids": [row["prediction_id"] for row in l1_written],
            "l1_factors": [row["payload"].get("factor") for row in l1_written],
            "l1_missing": True,
            "l4_prediction_id": l4_written["prediction_id"],
            "row_count": len(store),
            "distinct_prediction_ids": len({row["prediction_id"] for row in store.rows()}),
            "hf_rows": 0,
        },
        "market_compare": {
            "market_snapshot_id": MARKET_SNAPSHOT_ID,
            "pinned_spread_home": D3II_MARKET_SPREAD_HOME,
            "pinned_total": D3II_MARKET_TOTAL,
            "spread_delta_if_minus_pinned": l4_written["payload"]["spread_delta_if_minus_pinned"],
            "total_delta_if_minus_pinned": l4_written["payload"]["total_delta_if_minus_pinned"],
            "used_as_fair": False,
        },
        "publication_control": pub,
        "refusals": {
            "live_callers": True,
            "hf_layer": True,
            "ddl": True,
            "odds": True,
            "railway_c10": True,
            "unlock_overlays": True,
        },
        "receipt_path": str(receipt_path),
    }
    stable = {k: v for k, v in receipt.items() if k != "receipt_path"}
    # Drop ledger.path too — it embeds out_dir.
    ledger_stable = dict(receipt["ledger"])
    ledger_stable.pop("path", None)
    stable["ledger"] = ledger_stable
    core_blob = json.dumps(stable, sort_keys=True, indent=2, default=str) + "\n"
    receipt["receipt_sha256"] = hashlib.sha256(core_blob.encode("utf-8")).hexdigest()
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return receipt


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CLEAR-P1 local D3 shadow E2E")
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Directory for ledger.jsonl + receipt.json (local only)",
    )
    args = parser.parse_args(argv)
    try:
        receipt = run_shadow_p1(args.out)
    except (ShadowE2EReject, HandicapLedgerReject) as exc:
        print(f"REJECT: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(
        {
            "ok": True,
            "receipt_path": receipt.get("receipt_path"),
            "receipt_sha256": receipt.get("receipt_sha256"),
            "l0": receipt["ledger"]["l0_prediction_id"],
            "l1": receipt["ledger"]["l1_prediction_ids"],
            "l4": receipt["ledger"]["l4_prediction_id"],
            "if_margin_mu": receipt["independent_fair"]["margin_mu"],
            "if_total_mu": receipt["independent_fair"]["total_mu"],
            "d3ii_sha": receipt["blended_default_path"]["sha256"],
            "coming_soon": receipt["publication_control"]["coming_soon"],
            "cert": receipt["publication_control"]["cert"],
        },
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
