"""t5075u G2 diagnostic runner. ONE execution after Alex GO. CERT=0."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np

G2 = Path(__file__).resolve().parent
if str(G2) not in sys.path:
    sys.path.insert(0, str(G2))

from constants import (  # noqa: E402
    ALEX_GO_PATH,
    BLOCKER_PATH,
    CERT,
    CLAIM_KEYS,
    CURSOR_DONE_PATH,
    FORBIDDEN_RESULT_TOKENS,
    LABEL,
    LEGACY_WP_NOTE,
    MANIFEST_PATH,
    N_GAMES,
    NAMESPACE,
    NFL,
    PROTOCOL_ID,
    RESULTS_PATH,
    TICKET,
)
from freeze import FreezeRefuse, verify_manifest  # noqa: E402
from hashutil import sha256_file  # noqa: E402
from identities import IdentityRefuse, identity_boundary_cite  # noqa: E402
from load import (  # noqa: E402
    LoadRefuse,
    align_actuals,
    assert_draw_shape,
    default_outcomes_pin,
    load_forecasts,
    parse_score_only_restricted,
)
from metrics import (  # noqa: E402
    MetricRefuse,
    binary_scores,
    draw_diagnostics,
    mae_rmse_bundle,
    per_week_summaries,
    refuse_if_distribution_regen,
)


class DiagnosticRefuse(RuntimeError):
    pass


def require_alex_go(*, manifest_sha: str, go_path: Path = ALEX_GO_PATH) -> dict[str, Any]:
    if not go_path.is_file():
        raise DiagnosticRefuse(
            "Alex pre-compute GO absent — STOP. Do not parse outcomes or run diagnostics."
        )
    receipt = json.loads(go_path.read_text())
    bind = str(receipt.get("binds_frozen_manifest_sha256") or "")
    if bind != manifest_sha:
        raise DiagnosticRefuse("Alex GO does not bind the live frozen manifest sha")
    if receipt.get("authorizes_g2_diagnostic_execute") is not True:
        raise DiagnosticRefuse("Alex GO does not authorize execute")
    if int(receipt.get("cert", 1)) != 0:
        raise DiagnosticRefuse("Alex GO cert != 0")
    return receipt


def _claims() -> dict[str, bool]:
    return {k: False for k in CLAIM_KEYS}


def build_result(
    *,
    forecasts: Mapping[str, Any],
    actual_margin: np.ndarray,
    actual_total: np.ndarray,
    manifest_sha: str,
    outcomes_sha: str,
    alex_go: Mapping[str, Any],
) -> dict[str, Any]:
    preds = forecasts["preds"]
    weeks = forecasts["weeks"]
    assert_draw_shape(forecasts["H"], forecasts["A"])
    bundle = mae_rmse_bundle(
        actual_margin=actual_margin,
        actual_total=actual_total,
        preds={
            "joint": {"margin": preds["joint"]["margin"], "total": preds["joint"]["total"]},
            "if": {"margin": preds["if"]["margin"], "total": preds["if"]["total"]},
            "point": {"margin": preds["point"]["margin"], "total": preds["point"]["total"]},
        },
    )
    week_tbl = per_week_summaries(
        weeks=weeks,
        actual_margin=actual_margin,
        actual_total=actual_total,
        preds={
            "joint": {"margin": preds["joint"]["margin"], "total": preds["joint"]["total"]},
            "if": {"margin": preds["if"]["margin"], "total": preds["if"]["total"]},
            "point": {"margin": preds["point"]["margin"], "total": preds["point"]["total"]},
        },
    )
    binary = {
        "joint": binary_scores(
            preds["joint"]["wp"],
            actual_margin,
            source="joint.home_wp",
            legacy_rounding="none — persisted home_wp = #(D>0)/N",
        ),
        "if": binary_scores(
            preds["if"]["wp"],
            actual_margin,
            source="if.if_forecast_wp_home",
            legacy_rounding="legacy 4-decimal IF WP",
        ),
        "point": binary_scores(
            preds["point"]["wp"],
            actual_margin,
            source="point.wp",
        ),
        "disclosure": LEGACY_WP_NOTE,
    }
    draws = draw_diagnostics(
        H=forecasts["H"],
        A=forecasts["A"],
        actual_margin=actual_margin,
        actual_total=actual_total,
    )
    result = {
        "ticket": TICKET,
        "namespace": NAMESPACE,
        "protocol_id": PROTOCOL_ID,
        "label": LABEL,
        "cert": CERT,
        "nfl": NFL,
        "role": "consumed_data_descriptive_only",
        "claims": _claims(),
        "n": N_GAMES,
        "identity_boundary": identity_boundary_cite(),
        "manifest_sha256": manifest_sha,
        "outcomes_sha256": outcomes_sha,
        "alex_go": {
            "bound": True,
            "binds_frozen_manifest_sha256": alex_go.get("binds_frozen_manifest_sha256"),
        },
        "unavailable": forecasts["unavailable"],
        "gates_preserved": forecasts["gates_preserved"],
        "mae_rmse": bundle,
        "per_week": week_tbl,
        "binary": binary,
        "draws": draws,
        "executed": True,
        "one_run": True,
    }
    blob = json.dumps(result, sort_keys=True)
    for token in FORBIDDEN_RESULT_TOKENS:
        if token in blob:
            raise DiagnosticRefuse(f"forbidden result token {token}")
    return result


def execute_authorized(
    *,
    manifest_sha: str,
    alex_go: Mapping[str, Any],
    outcomes_path: Path | None = None,
    outcomes_sha: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    forecasts = load_forecasts()
    path, expected = default_outcomes_pin()
    if outcomes_path is not None:
        path = outcomes_path
    if outcomes_sha is not None:
        expected = outcomes_sha
    outcomes = parse_score_only_restricted(
        path,
        expected_sha=expected,
        eligible=forecasts["records"],
    )
    actuals = align_actuals(forecasts["records"], outcomes)
    result = build_result(
        forecasts=forecasts,
        actual_margin=actuals["margin"],
        actual_total=actuals["total"],
        manifest_sha=manifest_sha,
        outcomes_sha=expected,
        alex_go=alex_go,
    )
    if write:
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        results_sha = sha256_file(RESULTS_PATH)
        CURSOR_DONE_PATH.write_text(
            _cursor_done_text(manifest_sha=manifest_sha, results_sha=results_sha)
        )
        result["results_sha256"] = results_sha
        result["results_sha8"] = results_sha[:8]
    return result


def _cursor_done_text(*, manifest_sha: str, results_sha: str) -> str:
    return (
        "# CURSOR_DONE t5075u G2 DIAGNOSTIC\n\n"
        f"**CERT=0 · NFL NO-GO · DRAFT.** Protocol `{PROTOCOL_ID}`.\n\n"
        f"- consume head **43b5a622**\n"
        f"- frozen manifest `{manifest_sha[:8]}` / `{manifest_sha}`\n"
        f"- results `{results_sha[:8]}` / `{results_sha}`\n"
        "- pins 5076421e / ce6b1244 / 32e97434 / 55d8c8bc / 50bda875\n"
        "- LOOK 8bea4ca3 / ACCEPT bd51eb3e / LOOK_CONSUMED 013d270a (cited; not re-invoked)\n"
        "- Q2 EVAL 03a4dd90 CLOSED\n"
        "- 34 COND + J14 NOT_EMITTED preserved\n"
        "- IF distribution UNAVAILABLE (not regenerated)\n"
        "- descriptive only: no PASS / edge / retune / selection\n"
        "- STOP for Alex independent RO → CoS scoped ACCEPT\n"
    )


def record_blocker(message: str) -> None:
    BLOCKER_PATH.write_text(
        json.dumps(
            {
                "ticket": TICKET,
                "status": "BLOCKER",
                "executed": False,
                "message": message,
                "fallback": (
                    "approved pin/identity/read-boundary fixtures only; "
                    "no invented data"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> int:
    if "--freeze-only" in sys.argv or "--preverify" in sys.argv:
        from freeze import write_manifest

        if "--preverify" in sys.argv and MANIFEST_PATH.is_file():
            info = verify_manifest()
            print(json.dumps({"preverify": info, "executed": False}, indent=2))
            return 0
        manifest = write_manifest()
        print(
            json.dumps(
                {
                    "freeze": "wrote",
                    "sha256": manifest["_written_sha256"],
                    "executed": False,
                },
                indent=2,
            )
        )
        return 0
    try:
        info = verify_manifest()
        go = require_alex_go(manifest_sha=info["manifest_sha256"])
        # Explicit: still do not regen IF draws.
        try:
            refuse_if_distribution_regen()
        except MetricRefuse:
            pass
        result = execute_authorized(
            manifest_sha=info["manifest_sha256"],
            alex_go=go,
        )
        print(
            json.dumps(
                {
                    "executed": True,
                    "n": result["n"],
                    "results_sha8": result.get("results_sha8"),
                    "manifest_sha8": info["manifest_sha256"][:8],
                },
                indent=2,
            )
        )
        return 0
    except (DiagnosticRefuse, FreezeRefuse, LoadRefuse, IdentityRefuse, MetricRefuse) as exc:
        print(f"G2_REFUSE: {exc}")
        if "MISSING" in str(exc):
            record_blocker(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
