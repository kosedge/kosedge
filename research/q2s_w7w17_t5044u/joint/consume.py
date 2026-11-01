"""Read-only consumer of pinned research.q2s.joint artifacts.

Returns an in-memory ``research.q2s.joint.handoff`` only.
Does not regenerate draws, write outputs, invoke the simulator, or open
outcomes / LOOK / historical freeze maps.

CERT=0. Research only. Loaded ≠ PASS / calibrated / settlement / ops accept.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

JOINT = Path(__file__).resolve().parent
if str(JOINT) not in sys.path:
    sys.path.insert(0, str(JOINT))

from pins import (  # noqa: E402
    FW_SHA,
    IF_TIP,
    N_DRAWS,
    N_GAMES,
    SIM_SHA,
    PinRefuse,
    _forbidden_path,
    sha256_file,
)
from sim_q2s_joint import (  # noqa: E402
    JointRefuse,
    derive_from_pairs,
    paired_draw_hash,
)

NAMESPACE = "research.q2s.joint.handoff"
SOURCE_NAMESPACE = "research.q2s.joint"

CANONICAL_JSON_SHA256 = (
    "5076421ef1fba943df9c1e8eeaefede4f7a7e30a36ae2ed792a7f2bc295c4e27"
)
CANONICAL_NPZ_SHA256 = (
    "ce6b1244895df065ea8428851261becbb8012c7379d6184770116a7dfbcb0fc5"
)

DEFAULT_JSON = JOINT / "artifacts" / "Q2S_JOINT_W7W17.json"
DEFAULT_NPZ = JOINT / "artifacts" / "Q2S_JOINT_DRAWS_W7W17.npz"

ALLOWED_BASENAMES = frozenset(
    {
        "Q2S_JOINT_W7W17.json",
        "Q2S_JOINT_DRAWS_W7W17.npz",
    }
)

HEADER_KEYS = frozenset(
    {
        "N",
        "ats_ou",
        "blend",
        "cert",
        "cite",
        "construction",
        "draw_order",
        "draws_catalog_sha256",
        "draws_file_sha256",
        "draws_path",
        "framework_sha256",
        "game_ids",
        "gate_counts_by_name",
        "gate_counts_cellwise",
        "if_tip",
        "j12_diagnostic",
        "label",
        "look_run",
        "n",
        "namespace",
        "nfl",
        "opened_50bda875",
        "pins",
        "q1_d0",
        "q1_details",
        "research_only",
        "rows",
        "scored",
        "simulator_sha256",
        "ticket",
        "totals_cal",
        "weight",
        "worst_gate_counts",
    }
)
ROW_KEYS = frozenset(
    {
        "N",
        "ats_ou",
        "away",
        "away_wp",
        "corr_HA",
        "d",
        "draw_hash",
        "fair_away_ml",
        "fair_home_ml",
        "game_id",
        "gates",
        "home",
        "home_wins",
        "home_wp",
        "if_margin_mu",
        "margin_mu_q2s",
        "mean_D",
        "mean_S",
        "mu_a",
        "mu_a_p",
        "mu_h",
        "mu_h_p",
        "q5_diag",
        "sd_D",
        "season",
        "seed",
        "sigma",
        "spread_home",
        "tie_count",
        "total_raw",
        "week",
        "worst_gate",
    }
)
NPZ_KEYS = frozenset({"game_ids", "H", "A"})
PIN_KEYS = (
    "q2s",
    "if_mus",
    "matrix",
    "parent_freeze",
    "t5055u_freeze",
    "history_freeze",
)
FLOAT_REDRIVE = (
    "home_wp",
    "away_wp",
    "spread_home",
    "total_raw",
    "mean_D",
    "mean_S",
)
INT_REDRIVE = ("home_wins", "tie_count", "fair_home_ml", "fair_away_ml")

LIMITATIONS = MappingProxyType(
    {
        "loaded_is_not_all_gates_pass": True,
        "loaded_is_not_calibrated_probabilities": True,
        "loaded_is_not_book_settlement": True,
        "loaded_is_not_operational_acceptance": True,
        "tie_convention": "D=0 (0-0 only) counts AWAY; home_wp = #(D>0)/N",
        "score_convention": "continuous floored scores; not integer book lines",
        "cert": 0,
        "nfl": "NO-GO",
        "clears": "joint artifact consumption only; not #682 / production #6/#8",
    }
)


class _FairMl:
    """Local ML transform for derive_from_pairs. Not a simulator."""

    @staticmethod
    def _fair_moneyline_from_prob(prob: float) -> int:
        p = min(0.999, max(0.001, float(prob)))
        if p >= 0.5:
            return int(round(-(100.0 * p) / (1.0 - p)))
        return int(round((100.0 * (1.0 - p)) / p))


def allowed_file_set(
    json_path: Path | None = None,
    npz_path: Path | None = None,
) -> tuple[Path, ...]:
    json_p = (json_path or DEFAULT_JSON).resolve()
    npz_p = (npz_path or DEFAULT_NPZ).resolve()
    return (json_p, npz_p)


def _freeze(obj: Any) -> Any:
    if isinstance(obj, dict):
        return MappingProxyType({k: _freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_freeze(v) for v in obj)
    return obj


def _assert_openable(path: Path) -> Path:
    resolved = path.resolve()
    if _forbidden_path(resolved):
        raise PinRefuse(f"forbidden path {resolved}")
    if resolved.name not in ALLOWED_BASENAMES:
        raise JointRefuse(f"path not on consumer allowlist: {resolved.name}")
    return resolved


def _readonly_copy(arr: np.ndarray) -> np.ndarray:
    out = np.array(arr, dtype=np.float64, copy=True, order="C")
    out.setflags(write=False)
    return out


def _validate_header(payload: Mapping[str, Any], npz_sha: str) -> None:
    keys = set(payload)
    if keys != HEADER_KEYS:
        missing = sorted(HEADER_KEYS - keys)
        extra = sorted(keys - HEADER_KEYS)
        raise JointRefuse(f"header schema mismatch missing={missing} extra={extra}")
    if payload["namespace"] != SOURCE_NAMESPACE:
        raise JointRefuse("namespace is not research.q2s.joint")
    if int(payload["cert"]) != 0:
        raise JointRefuse("cert != 0")
    if payload["research_only"] is not True:
        raise JointRefuse("research_only is not true")
    if payload["scored"] is not False:
        raise JointRefuse("scored is not false")
    if payload["opened_50bda875"] is not False:
        raise JointRefuse("opened_50bda875 is not false")
    if payload["look_run"] is not False:
        raise JointRefuse("look_run is not false")
    if int(payload["N"]) != N_DRAWS:
        raise JointRefuse(f"N {payload['N']} != {N_DRAWS}")
    if int(payload["n"]) != N_GAMES:
        raise JointRefuse(f"n {payload['n']} != {N_GAMES}")
    if payload["simulator_sha256"] != SIM_SHA:
        raise JointRefuse("simulator_sha256 drifted")
    if payload["framework_sha256"] != FW_SHA:
        raise JointRefuse("framework_sha256 drifted")
    if payload["if_tip"] != IF_TIP:
        raise JointRefuse("if_tip drifted")
    if payload["ats_ou"] != "NOT_EMITTED":
        raise JointRefuse("ats_ou is not NOT_EMITTED")
    if payload["draws_file_sha256"] != npz_sha:
        raise JointRefuse("draws_file_sha256 != live npz sha")
    pins = payload["pins"]
    if set(pins) != set(PIN_KEYS):
        raise JointRefuse(f"source pins keys mismatch {sorted(pins)}")
    for key in PIN_KEYS:
        if not isinstance(pins[key], str) or len(pins[key]) != 64:
            raise JointRefuse(f"source pin {key} malformed")
    if payload["gate_counts_cellwise"].get("COND") != 34:
        raise JointRefuse("cellwise COND != 34 (do not hide)")
    if payload["gate_counts_by_name"].get("J14", {}).get("NOT_EMITTED") != 141:
        raise JointRefuse("J14 NOT_EMITTED count != 141")


def _ordered_ids(payload: Mapping[str, Any]) -> list[str]:
    ids = payload["game_ids"]
    rows = payload["rows"]
    if not isinstance(ids, list) or not isinstance(rows, list):
        raise JointRefuse("game_ids/rows must be lists")
    if len(ids) != N_GAMES or len(rows) != N_GAMES:
        raise JointRefuse(f"identity length {len(ids)}/{len(rows)} != {N_GAMES}")
    if any(not isinstance(g, str) or not g for g in ids):
        raise JointRefuse("malformed game_id")
    if len(set(ids)) != N_GAMES:
        raise JointRefuse("duplicate game_id")
    row_ids = [r.get("game_id") for r in rows]
    if row_ids != ids:
        raise JointRefuse("row game_id order != game_ids")
    for row in rows:
        if set(row) != ROW_KEYS:
            raise JointRefuse(
                f"row schema mismatch {row.get('game_id')}: "
                f"missing={sorted(ROW_KEYS - set(row))} extra={sorted(set(row) - ROW_KEYS)}"
            )
        if int(row["N"]) != N_DRAWS:
            raise JointRefuse(f"{row['game_id']} N != 4000")
        if row["ats_ou"] != "NOT_EMITTED":
            raise JointRefuse(f"{row['game_id']} ats_ou emitted")
        if "J14" not in row["gates"] or row["gates"]["J14"].get("status") != "NOT_EMITTED":
            raise JointRefuse(f"{row['game_id']} J14 not NOT_EMITTED")
    return list(ids)


def _validate_draws(
    H: np.ndarray,
    A: np.ndarray,
    npz_ids: list[str],
    json_ids: list[str],
) -> None:
    if npz_ids != json_ids:
        raise JointRefuse("npz game_ids order != json game_ids")
    if H.shape != (N_GAMES, N_DRAWS) or A.shape != (N_GAMES, N_DRAWS):
        raise JointRefuse(f"draw shape {H.shape}/{A.shape}")
    if H.dtype != np.float64 or A.dtype != np.float64:
        raise JointRefuse(f"draw dtype {H.dtype}/{A.dtype} (no cast)")
    if not np.isfinite(H).all() or not np.isfinite(A).all():
        raise JointRefuse("nonfinite draws")
    if np.any(H < 0.0) or np.any(A < 0.0):
        raise JointRefuse("negative draws")


def _catalog_sha(game_ids: list[str], H: np.ndarray, A: np.ndarray) -> str:
    catalog = hashlib.sha256()
    for i, gid in enumerate(game_ids):
        catalog.update(gid.encode())
        catalog.update(np.ascontiguousarray(H[i]).tobytes())
        catalog.update(np.ascontiguousarray(A[i]).tobytes())
    return catalog.hexdigest()


def _rederive_row(row: Mapping[str, Any], H: np.ndarray, A: np.ndarray) -> None:
    digest = paired_draw_hash(H, A)
    if digest != row["draw_hash"]:
        raise JointRefuse(f"{row['game_id']} draw_hash mismatch")
    stats = derive_from_pairs(H, A, _FairMl)
    for key in INT_REDRIVE:
        if int(stats[key]) != int(row[key]):
            raise JointRefuse(f"{row['game_id']} {key} {stats[key]} != {row[key]}")
    for key in FLOAT_REDRIVE:
        err = abs(float(stats[key]) - float(row[key]))
        if not math.isfinite(err) or err > 1e-12:
            raise JointRefuse(f"{row['game_id']} {key} abs err {err} > 1e-12")


@dataclass(frozen=True)
class JointHandoff:
    namespace: str
    provenance: Mapping[str, Any]
    limitations: Mapping[str, Any]
    game_ids: tuple[str, ...]
    rows: tuple[Any, ...]
    H: np.ndarray
    A: np.ndarray
    gate_counts_cellwise: Mapping[str, Any]
    worst_gate_counts: Mapping[str, Any]
    cond_cell_count: int
    j14_not_emitted_count: int

    def __post_init__(self) -> None:
        if self.namespace != NAMESPACE:
            raise JointRefuse("handoff namespace drifted")


def consume_q2s_joint(
    *,
    expected_json_sha256: str,
    expected_npz_sha256: str,
    json_path: Path | None = None,
    npz_path: Path | None = None,
) -> JointHandoff:
    """Load pinned joint artifacts into a research-only in-memory handoff.

    Callers MUST pass the canonical hashes. Altered files cannot be blessed.
    """
    if expected_json_sha256 != CANONICAL_JSON_SHA256:
        raise JointRefuse("caller JSON digest is not the canonical pin")
    if expected_npz_sha256 != CANONICAL_NPZ_SHA256:
        raise JointRefuse("caller NPZ digest is not the canonical pin")

    json_p = _assert_openable(json_path or DEFAULT_JSON)
    npz_p = _assert_openable(npz_path or DEFAULT_NPZ)
    if not json_p.is_file() or not npz_p.is_file():
        raise JointRefuse("canonical joint artifact missing")

    live_json = sha256_file(json_p)
    live_npz = sha256_file(npz_p)
    if live_json != expected_json_sha256:
        raise JointRefuse("JSON sha != caller/canonical pin")
    if live_npz != expected_npz_sha256:
        raise JointRefuse("NPZ sha != caller/canonical pin")

    payload = json.loads(json_p.read_text())
    if not isinstance(payload, dict):
        raise JointRefuse("JSON root is not an object")
    _validate_header(payload, live_npz)
    json_ids = _ordered_ids(payload)

    with np.load(npz_p, allow_pickle=False) as handle:
        keys = set(handle.files)
        if keys != NPZ_KEYS:
            raise JointRefuse(f"npz keys {sorted(keys)} != {sorted(NPZ_KEYS)}")
        npz_ids = [str(x) for x in handle["game_ids"]]
        H_raw = handle["H"]
        A_raw = handle["A"]
        _validate_draws(H_raw, A_raw, npz_ids, json_ids)
        if _catalog_sha(json_ids, H_raw, A_raw) != payload["draws_catalog_sha256"]:
            raise JointRefuse("draws catalog sha mismatch")
        rows_out = []
        cond_cells = 0
        j14 = 0
        for i, row in enumerate(payload["rows"]):
            _rederive_row(row, H_raw[i], A_raw[i])
            for name, gate in row["gates"].items():
                if gate.get("status") == "COND":
                    cond_cells += 1
                if name == "J14" and gate.get("status") == "NOT_EMITTED":
                    j14 += 1
            rows_out.append(_freeze(copy.deepcopy(row)))
        H = _readonly_copy(H_raw)
        A = _readonly_copy(A_raw)

    if cond_cells != 34:
        raise JointRefuse(f"preserved COND cells {cond_cells} != 34")
    if j14 != N_GAMES:
        raise JointRefuse(f"J14 NOT_EMITTED {j14} != 141")

    provenance = _freeze(
        {
            "namespace_source": SOURCE_NAMESPACE,
            "namespace_handoff": NAMESPACE,
            "json_sha256": live_json,
            "npz_sha256": live_npz,
            "draws_catalog_sha256": payload["draws_catalog_sha256"],
            "if_tip": payload["if_tip"],
            "simulator_sha256": payload["simulator_sha256"],
            "framework_sha256": payload["framework_sha256"],
            "pins": dict(payload["pins"]),
            "n": N_GAMES,
            "N": N_DRAWS,
            "draw_order": payload["draw_order"],
            "construction": payload["construction"],
            "allowed_files": [str(json_p), str(npz_p)],
        }
    )
    return JointHandoff(
        namespace=NAMESPACE,
        provenance=provenance,
        limitations=LIMITATIONS,
        game_ids=tuple(json_ids),
        rows=tuple(rows_out),
        H=H,
        A=A,
        gate_counts_cellwise=_freeze(copy.deepcopy(payload["gate_counts_cellwise"])),
        worst_gate_counts=_freeze(copy.deepcopy(payload["worst_gate_counts"])),
        cond_cell_count=cond_cells,
        j14_not_emitted_count=j14,
    )
