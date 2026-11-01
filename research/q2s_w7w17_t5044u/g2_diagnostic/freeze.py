"""Freeze input + code hashes + protocol BEFORE any outcomes parse."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

G2 = Path(__file__).resolve().parent
if str(G2) not in sys.path:
    sys.path.insert(0, str(G2))

from constants import (  # noqa: E402
    ACCEPT_TIP,
    ALEX_GO_PATH,
    CERT,
    CONSUME_HEAD,
    CONSUME_HEAD_SHA8,
    COVERAGE_LEVELS,
    ELIGIBLE_SEASON,
    IF_MUS_PATH,
    IF_MUS_SHA256,
    JOINT_JSON_PATH,
    JOINT_JSON_SHA256,
    JOINT_NPZ_PATH,
    JOINT_NPZ_SHA256,
    LABEL,
    LOGLOSS_EPS,
    LOGLOSS_N,
    LOOK_CONSUMED_PATH,
    LOOK_CONSUMED_SHA256,
    LOOK_TIP,
    MANIFEST_PATH,
    MANIFEST_SHA_PATH,
    N_DRAWS,
    N_GAMES,
    N_T2_SEALED,
    NFL,
    OUTCOMES_PATH,
    OUTCOMES_SHA256,
    PROTOCOL_ID,
    PROTOCOL_PATH,
    Q2S_ROWS_PATH,
    Q2S_ROWS_SHA256,
    Q2_EVAL_CLOSED,
    TICKET,
    WEEK_BLOCKS,
)
from hashutil import sha256_file, sha256_text  # noqa: E402
from identities import (  # noqa: E402
    extract_forecast_identities,
    identities_sha256,
    identity_boundary_cite,
)


class FreezeRefuse(RuntimeError):
    pass


EXCLUDE_NAMES = frozenset(
    {
        "FROZEN_MANIFEST.json",
        "FROZEN_MANIFEST.json.sha256",
        "ALEX_PRECOMPUTE_GO.json",
        "CURSOR_DONE.md",
        "BLOCKER.json",
        "G2_DIAGNOSTIC_RESULT.json",
        "RECEIPT_t5075u_PREVERIFY.md",
    }
)


def _rel(path: Path) -> str:
    return str(path.relative_to(G2)).replace("\\", "/")


def code_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(G2.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.name in EXCLUDE_NAMES:
            continue
        if path.parent.name == "artifacts":
            continue
        if path.suffix in {".py", ".md"}:
            files.append(path)
    return files


def hash_inputs() -> dict[str, dict[str, str]]:
    pairs = {
        "joint_json": (JOINT_JSON_PATH, JOINT_JSON_SHA256, "5076421e"),
        "joint_npz": (JOINT_NPZ_PATH, JOINT_NPZ_SHA256, "ce6b1244"),
        "if_mus": (IF_MUS_PATH, IF_MUS_SHA256, "32e97434"),
        "q2s_rows": (Q2S_ROWS_PATH, Q2S_ROWS_SHA256, "55d8c8bc"),
        "outcomes_score_only": (OUTCOMES_PATH, OUTCOMES_SHA256, "50bda875"),
        "look_consumed": (LOOK_CONSUMED_PATH, LOOK_CONSUMED_SHA256, "013d270a"),
    }
    out: dict[str, dict[str, str]] = {}
    for key, (path, expected, prefix) in pairs.items():
        if not path.is_file():
            raise FreezeRefuse(f"MISSING {key} {path}")
        live = sha256_file(path)
        if live != expected:
            raise FreezeRefuse(f"{key} sha {live} != {expected[:8]}")
        if not live.startswith(prefix):
            raise FreezeRefuse(f"{key} prefix {live[:8]} != {prefix}")
        out[key] = {
            "path": str(path.relative_to(G2.parent)).replace("\\", "/"),
            "sha256": live,
            "sha8": live[:8],
            "parse": "checksum_only" if key in {"outcomes_score_only", "look_consumed"} else "forecast",
        }
    return out


def hash_code() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in code_files():
        out[_rel(path)] = sha256_file(path)
    if "PROTOCOL.md" not in out:
        raise FreezeRefuse("PROTOCOL.md not hashed")
    return out


def protocol_block() -> dict[str, Any]:
    return {
        "id": PROTOCOL_ID,
        "ticket": TICKET,
        "label": LABEL,
        "cert": CERT,
        "nfl": NFL,
        "consume_head": CONSUME_HEAD,
        "consume_head_sha8": CONSUME_HEAD_SHA8,
        "n_games": N_GAMES,
        "n_draws": N_DRAWS,
        "n_t2_sealed_out": N_T2_SEALED,
        "season": ELIGIBLE_SEASON,
        "weeks": list(WEEK_BLOCKS),
        "join": ["season", "week", "home", "away"],
        "logloss_n": LOGLOSS_N,
        "logloss_eps": LOGLOSS_EPS,
        "logloss_clip": [LOGLOSS_EPS, 1.0 - LOGLOSS_EPS],
        "coverage_levels": list(COVERAGE_LEVELS),
        "if_distribution": "UNAVAILABLE",
        "point_candidate_total": "UNAVAILABLE",
        "point_candidate_wp": "UNAVAILABLE",
        "exclude_actual_ties_from_binary": True,
        "q2_eval": f"{Q2_EVAL_CLOSED} CLOSED",
        "no_look_invocation": True,
        "no_pass_edge_retune_selection": True,
        "outcomes_parse_before_alex_go": False,
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
    }


def build_manifest() -> dict[str, Any]:
    inputs = hash_inputs()
    joint = json.loads(JOINT_JSON_PATH.read_text())
    q2s = json.loads(Q2S_ROWS_PATH.read_text())
    if_mus = json.loads(IF_MUS_PATH.read_text())
    records = extract_forecast_identities(joint, q2s, if_mus)
    code = hash_code()
    manifest = {
        "ticket": TICKET,
        "protocol_id": PROTOCOL_ID,
        "status": "PREVERIFY",
        "executed": False,
        "awaiting": "Alex pre-compute verify / GO bound to this manifest",
        "consume_head": CONSUME_HEAD,
        "inputs": inputs,
        "code": code,
        "code_catalog_sha256": sha256_text(json.dumps(code, sort_keys=True, separators=(",", ":"))),
        "protocol": protocol_block(),
        "identities": {
            "n": len(records),
            "sha256": identities_sha256(records),
            "records": records,
            "source": "forecast joint/q2s/IF_MUS alignment; outcomes not parsed",
        },
        "identity_boundary": identity_boundary_cite(),
        "cited_tips_not_files": {
            LOOK_TIP: "LOOK — cited tip, not a path on this tree",
            ACCEPT_TIP: "ACCEPT — cited tip, not a path on this tree",
        },
        "hard_stops": [
            "no fitting/regen/retune/selection",
            "no 2024-25 protected open",
            "no spend/pull",
            "no production release",
            "no merge/C10/cert",
            "no Q2 EVAL reopen",
            "no LOOK invocation",
            "no IF distribution regen",
        ],
    }
    return manifest


def write_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = build_manifest()
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    path.write_text(text)
    digest = sha256_file(path)
    MANIFEST_SHA_PATH.write_text(digest + "  FROZEN_MANIFEST.json\n")
    manifest["_written_sha256"] = digest
    return manifest


def verify_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FreezeRefuse("FROZEN_MANIFEST.json missing")
    live = json.loads(path.read_text())
    rebuilt = build_manifest()
    # Compare without the optional write stamp.
    live_cmp = {k: v for k, v in live.items() if not str(k).startswith("_")}
    if live_cmp != rebuilt:
        raise FreezeRefuse("frozen manifest drifted from live input+code+protocol")
    digest = sha256_file(path)
    if MANIFEST_SHA_PATH.is_file():
        recorded = MANIFEST_SHA_PATH.read_text().split()[0]
        if recorded != digest:
            raise FreezeRefuse("manifest sha256 sidecar mismatch")
    return {
        "ok": True,
        "manifest_sha256": digest,
        "n_identities": live["identities"]["n"],
        "executed": live.get("executed"),
        "status": live.get("status"),
        "alex_go_present": ALEX_GO_PATH.is_file(),
    }


def main() -> int:
    try:
        if "--verify" in sys.argv:
            info = verify_manifest()
            print(json.dumps(info, indent=2))
            return 0
        manifest = write_manifest()
        print(
            json.dumps(
                {
                    "wrote": str(MANIFEST_PATH),
                    "sha256": manifest["_written_sha256"],
                    "n_identities": manifest["identities"]["n"],
                    "status": manifest["status"],
                    "executed": False,
                },
                indent=2,
            )
        )
        return 0
    except FreezeRefuse as exc:
        print(f"FREEZE_REFUSE: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
