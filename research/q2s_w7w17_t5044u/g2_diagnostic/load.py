"""Gated loaders for t5075u G2. Outcomes parse is opt-in after Alex GO."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

G2 = Path(__file__).resolve().parent
JOINT = G2.parent / "joint"
if str(G2) not in sys.path:
    sys.path.insert(0, str(G2))
if str(JOINT) not in sys.path:
    sys.path.insert(0, str(JOINT))

from constants import (  # noqa: E402
    IF_DIST_NOTE,
    IF_MUS_PATH,
    IF_MUS_SHA256,
    JOINT_JSON_SHA256,
    JOINT_NPZ_SHA256,
    N_DRAWS,
    N_GAMES,
    OUTCOMES_PATH,
    OUTCOMES_SHA256,
    POINT_TOTAL_NOTE,
    POINT_WP_NOTE,
    Q2S_ROWS_PATH,
    Q2S_ROWS_SHA256,
    UNAVAILABLE,
)
from identities import (  # noqa: E402
    Identity,
    IdentityRefuse,
    identity_key,
    keys_from_records,
    require_exact_141,
)

from consume import consume_q2s_joint  # noqa: E402
from hashutil import sha256_file  # noqa: E402


class LoadRefuse(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return sha256_file(path)


def assert_pin(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise LoadRefuse(f"MISSING pin {label}: {path}")
    live = _sha(path)
    if live != expected:
        raise LoadRefuse(f"{label} sha {live} != {expected[:8]}")
    return live


def if_distribution_status(if_payload: Mapping[str, Any]) -> str:
    """Means-only IF_MUS → UNAVAILABLE. Never synthesize draws."""
    if "H" in if_payload or "A" in if_payload or "draws" in if_payload:
        rows = if_payload.get("rows") or []
        # Even if a future file grew draw keys, this package will not consume
        # unsanctioned IF draws. Mark UNAVAILABLE unless the frozen contract
        # is explicitly amended (it is not).
        _ = rows
    return UNAVAILABLE


def load_forecasts(
    *,
    joint_json_sha: str = JOINT_JSON_SHA256,
    joint_npz_sha: str = JOINT_NPZ_SHA256,
    if_path: Path = IF_MUS_PATH,
    q2s_path: Path = Q2S_ROWS_PATH,
    expected_if_sha: str = IF_MUS_SHA256,
    expected_q2s_sha: str = Q2S_ROWS_SHA256,
) -> dict[str, Any]:
    """Load joint handoff + IF/q2s means. No outcomes."""
    assert_pin(if_path, expected_if_sha, "if_mus")
    assert_pin(q2s_path, expected_q2s_sha, "q2s")
    handoff = consume_q2s_joint(
        expected_json_sha256=joint_json_sha,
        expected_npz_sha256=joint_npz_sha,
    )
    if_payload = json.loads(if_path.read_text())
    q2s_payload = json.loads(q2s_path.read_text())
    if if_distribution_status(if_payload) != UNAVAILABLE:
        raise LoadRefuse("IF distribution unexpectedly present — do not silently consume")
    if int(handoff.cond_cell_count) != 34:
        raise LoadRefuse(f"COND {handoff.cond_cell_count} != 34")
    if int(handoff.j14_not_emitted_count) != N_GAMES:
        raise LoadRefuse("J14 NOT_EMITTED drifted")

    if_by_id = {str(r["game_id"]): r for r in if_payload["rows"]}
    q_by_id = {str(r["game_id"]): r for r in q2s_payload["rows"]}

    joint_margin: list[float] = []
    joint_total: list[float] = []
    joint_wp: list[float] = []
    if_margin: list[float] = []
    if_total: list[float] = []
    if_wp: list[float] = []
    point_margin: list[float] = []
    weeks: list[int] = []
    records: list[dict[str, Any]] = []
    for row in handoff.rows:
        gid = str(row["game_id"])
        if gid not in if_by_id or gid not in q_by_id:
            raise LoadRefuse(f"forecast miss {gid}")
        ifr = if_by_id[gid]
        qr = q_by_id[gid]
        rec = {
            "game_id": gid,
            "season": int(row["season"]),
            "week": int(row["week"]),
            "home": str(row["home"]),
            "away": str(row["away"]),
        }
        if identity_key(rec) != identity_key(ifr) or identity_key(rec) != identity_key(qr):
            raise LoadRefuse(f"identity mismatch {gid}")
        records.append(rec)
        weeks.append(int(rec["week"]))
        joint_margin.append(float(row["mean_D"]))
        joint_total.append(float(row["mean_S"]))
        joint_wp.append(float(row["home_wp"]))
        if_margin.append(float(ifr["if_margin_mu"]))
        if_total.append(float(ifr["if_total_mu"]))
        if_wp.append(float(ifr["if_forecast_wp_home"]))
        point_margin.append(float(qr["research"]["q2s"]["margin_mu_q2s"]))
        if qr.get("baseline", {}).get("no_candidate_probabilities") is not True:
            raise LoadRefuse(f"{gid}: point-candidate WP unexpectedly present")

    require_exact_141(keys_from_records(records), context="forecasts")
    return {
        "handoff": handoff,
        "records": records,
        "weeks": weeks,
        "preds": {
            "joint": {
                "margin": np.asarray(joint_margin, dtype=np.float64),
                "total": np.asarray(joint_total, dtype=np.float64),
                "wp": np.asarray(joint_wp, dtype=np.float64),
            },
            "if": {
                "margin": np.asarray(if_margin, dtype=np.float64),
                "total": np.asarray(if_total, dtype=np.float64),
                "wp": np.asarray(if_wp, dtype=np.float64),
            },
            "point": {
                "margin": np.asarray(point_margin, dtype=np.float64),
                "total": None,
                "wp": None,
            },
        },
        "H": handoff.H,
        "A": handoff.A,
        "unavailable": {
            "if_distribution": UNAVAILABLE,
            "if_distribution_note": IF_DIST_NOTE,
            "point_candidate_total": UNAVAILABLE,
            "point_candidate_total_note": POINT_TOTAL_NOTE,
            "point_candidate_wp": UNAVAILABLE,
            "point_candidate_wp_note": POINT_WP_NOTE,
        },
        "gates_preserved": {
            "cond": int(handoff.cond_cell_count),
            "j14_not_emitted": int(handoff.j14_not_emitted_count),
        },
    }


def parse_score_only_restricted(
    path: Path,
    *,
    expected_sha: str,
    eligible: Sequence[Mapping[str, Any]],
) -> dict[Identity, tuple[float, float]]:
    """Parse 50bda875 (or a fixture) and keep only the 141 eligible keys.

    Extra CSV rows are ignored, not scored. Missing eligible keys refuse.
    Other-season keys in `eligible` refuse before scores are used.
    """
    live = assert_pin(path, expected_sha, "outcomes")
    keys = require_exact_141(keys_from_records(eligible), context="eligible")
    wanted = set(keys)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"season", "week", "home", "away", "home_score", "away_score"}
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise LoadRefuse("outcomes CSV missing score-only columns")
        extra = set(reader.fieldnames) - required
        if extra:
            # Score-only pin is 6 columns. Refuse extras so 1ee90fac cannot sneak in.
            raise LoadRefuse(f"outcomes extra columns refused: {sorted(extra)}")
        kept: dict[Identity, tuple[float, float]] = {}
        for rec in reader:
            key = (
                int(rec["season"]),
                int(rec["week"]),
                str(rec["home"]),
                str(rec["away"]),
            )
            if key not in wanted:
                continue
            if key in kept:
                raise LoadRefuse(f"duplicate eligible outcome {key}")
            hs = float(rec["home_score"])
            aws = float(rec["away_score"])
            if not np.isfinite(hs) or not np.isfinite(aws):
                raise LoadRefuse(f"non-finite score {key}")
            kept[key] = (hs, aws)
    missing = [k for k in keys if k not in kept]
    if missing:
        raise LoadRefuse(f"eligible identity miss {missing[0]} (n_miss={len(missing)})")
    if len(kept) != N_GAMES:
        raise LoadRefuse(f"restricted n={len(kept)} != {N_GAMES}")
    _ = live
    return kept


def align_actuals(
    records: Sequence[Mapping[str, Any]],
    outcomes: Mapping[Identity, tuple[float, float]],
) -> dict[str, np.ndarray]:
    keys = require_exact_141(keys_from_records(records), context="align")
    margins: list[float] = []
    totals: list[float] = []
    for key in keys:
        if key not in outcomes:
            raise IdentityRefuse(f"align miss {key}")
        hs, aws = outcomes[key]
        margins.append(float(hs) - float(aws))
        totals.append(float(hs) + float(aws))
    return {
        "margin": np.asarray(margins, dtype=np.float64),
        "total": np.asarray(totals, dtype=np.float64),
    }


def default_outcomes_pin() -> tuple[Path, str]:
    return OUTCOMES_PATH, OUTCOMES_SHA256


def assert_draw_shape(H: np.ndarray, A: np.ndarray) -> None:
    if H.shape != (N_GAMES, N_DRAWS) or A.shape != (N_GAMES, N_DRAWS):
        raise LoadRefuse(f"draw shape {H.shape}/{A.shape}")
    if H.dtype != np.float64 or A.dtype != np.float64:
        raise LoadRefuse("draw dtype drifted")
