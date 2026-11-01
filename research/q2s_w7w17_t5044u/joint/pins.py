"""Pin constants + verify that does NOT open 50bda875 / LOOK / outcomes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PACKET = Path(__file__).resolve().parents[1]
JOINT = Path(__file__).resolve().parent

Q2S_PATH = PACKET / "phase4" / "artifacts" / "q2s_rows_w7w17.json"
IF_MUS_PATH = PACKET / "phase4" / "artifacts" / "IF_MUS_W7W17.json"
MATRIX_PATH = PACKET / "gate2" / "RECON_MATRIX_W7W17.csv"
PARENT_FREEZE_PATH = PACKET / "phase4" / "artifacts" / "PROTOCOL_FREEZE.json"
T5055U_FREEZE_PATH = PACKET / "evaluator" / "FINAL_PRELOOK_FREEZE_t5055u.json"
HISTORY_FREEZE_PATH = PACKET / "evaluator" / "FINAL_PRELOOK_FREEZE.json"

Q2S_SHA = "55d8c8bc2155705c04e9ef88ba5637ea491bf5c245e4f7bb8fcfb3523f9ec925"
IF_MUS_SHA = "32e9743483259f2a9c13efe9826e550f610a6068995fad3bc9fdb6b1698d5d43"
MATRIX_SHA = "b56be1462e591ac5e04cfaf860938118e013664a2c661e156afdf5c5f41bc216"
PARENT_FREEZE_SHA = (
    "90774bd40c03c1b1de6f16967f29ba3ff2017b25d93620c6d5e351f56460df98"
)
T5055U_FREEZE_SHA = (
    "60b5f4b0140c147e519e3c2d904bbc0f162282af79e542e779499569b0f87291"
)
HISTORY_FREEZE_SHA = (
    "a46523231f55fc3b147a8e3864f74faf3de08d8f6c76d4cc92eebdeee7c174d4"
)
SIM_SHA = "52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385"
FW_SHA = "a0051cc423bd733c3342272fdb297ea8f22cf2a4569fe0f9ca0ec47eda04d0e3"
IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"

OUTCOMES_NAME = "outcomes_2013_2022_score_only.csv"
OUTCOMES_SHA8 = "50bda875"
LOOK_NAMES = ("LOOK_CONSUMED.json", "LOOK_RESULT.json")

N_GAMES = 141
N_DRAWS = 4000
N_T2 = 24
N_EXAMINED_70 = 70


class PinRefuse(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    if _forbidden_path(path):
        raise PinRefuse(f"refused to open forbidden path {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _forbidden_path(path: Path) -> bool:
    name = path.name
    if name == OUTCOMES_NAME or OUTCOMES_SHA8 in name:
        return True
    if name in LOOK_NAMES:
        return True
    text = str(path)
    if OUTCOMES_NAME in text or "/LOOK_" in text:
        return True
    return False


def verify_input_pins() -> dict[str, str]:
    """Re-hash allowed input pins. Never opens outcomes or LOOK files."""
    pairs = {
        "q2s": (Q2S_PATH, Q2S_SHA),
        "if_mus": (IF_MUS_PATH, IF_MUS_SHA),
        "matrix": (MATRIX_PATH, MATRIX_SHA),
        "parent_freeze_bytes": (PARENT_FREEZE_PATH, PARENT_FREEZE_SHA),
        "t5055u_freeze_bytes": (T5055U_FREEZE_PATH, T5055U_FREEZE_SHA),
        "history_freeze_bytes": (HISTORY_FREEZE_PATH, HISTORY_FREEZE_SHA),
    }
    out: dict[str, str] = {}
    for key, (path, expected) in pairs.items():
        live = sha256_file(path)
        if live != expected:
            raise PinRefuse(f"{key} sha {live} != {expected[:8]}")
        out[key] = live
    _assert_freeze_maps_not_traversed_into_outcomes()
    return out


def _assert_freeze_maps_not_traversed_into_outcomes() -> None:
    """Read freeze JSON objects only. Do not hash listed outcome entries."""
    parent = json.loads(PARENT_FREEZE_PATH.read_text())
    files = parent.get("files") or {}
    if any(OUTCOMES_NAME in str(rel) for rel in files):
        # Presence in the historical map is expected; we do not open it.
        pass
    t5055 = json.loads(T5055U_FREEZE_PATH.read_text())
    t_files = t5055.get("files") or {}
    for rel in list(files) + list(t_files):
        if OUTCOMES_NAME in str(rel):
            continue  # skip — never sha256 the outcomes pin


def load_q2s_rows() -> dict[str, Any]:
    verify_input_pins()
    payload = json.loads(Q2S_PATH.read_text())
    rows = payload.get("rows") or []
    if len(rows) != N_GAMES:
        raise PinRefuse(f"q2s n={len(rows)} != {N_GAMES}")
    return payload


def load_if_mus() -> dict[str, Any]:
    verify_input_pins()
    payload = json.loads(IF_MUS_PATH.read_text())
    rows = payload.get("rows") or []
    if len(rows) != N_GAMES:
        raise PinRefuse(f"if mus n={len(rows)} != {N_GAMES}")
    return payload
