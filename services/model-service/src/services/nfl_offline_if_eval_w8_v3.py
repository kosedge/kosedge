"""t4850u v3 — EVAL_ONLY re-execution after rest_days ET fix (OWNER t4864u).

Successor to sealed eval_w8_t4850u_v2/. Does not rewrite v1 or v2 packets.
Invoke must run at the declared execution tip (HEAD), not a parent.
"""

from __future__ import annotations

import io
import json
import math
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from uuid import uuid4

from src.services.nfl_offline_if_caller import (
    REJECT_THROUGH_W8,
    evaluate_caller,
    sha256_file,
)
from src.services.nfl_offline_if_eval_w8 import (
    BYE_ROLLING_AS_OF,
    EVAL_SEED_BASE,
    EVAL_SIMULATIONS,
    OWNER_CLEAR,
    PANEL_SHA256,
    RATING_WEEK,
    SCHEDULE_SHA256,
    SEASON,
    SUPPORTED_GAMES,
    TARGET_WEEK,
    TNF_GAME_ID,
    THROUGH_W7_ACCEPT,
    EvalW8Reject,
    build_eval_request,
    eval_pins,
    history_w1_w7,
    load_panel,
    load_schedule,
    operational_w8_still_blocked,
    refuse_public_delivery,
)
from src.services.nfl_offline_if_eval_w8_v2 import (
    AGENT_BC,
    LINEAGE_BASE,
    LINEAGE_BASE_FULL,
    OWNER_CLEAR_SHA,
    PR_NUMBER,
    V1_DIR,
    V2_DIR,
    CallAudit,
    build_unresolved,
    diff_vs_base,
    invoke_diagnostic_v2,
    resolve_commits,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
V3_DIR = REPO_ROOT / "data" / "ops" / "nfl-offline-if-caller-t4838u" / "eval_w8_t4850u_v3"
CLI_REL = "scripts/nfl/run_offline_if_eval_w8_t4850u_v3.py"
CMD = f"PYTHONPATH=services/model-service python3 {CLI_REL} --write-packet"
V2_PACKET_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
V2_PACKET_TIP_SHORT = "6ca03716"
REST_FIX_TIP = "155d3ca0b087375a78ff2f403d5f99ed382b027b"
REST_FIX_TIP_SHORT = "155d3ca0"
V2_INVOKE_PARENT = "426bd1d9e7d3eed4e9bf1166caa2b558862e7551"
SOURCE_GUARD = (
    "services/model-service/src/services/nfl_offline_if_eval_w8.py",
    "services/model-service/src/services/nfl_offline_if_eval_w8_v2.py",
    "services/model-service/src/services/nfl_offline_if_eval_w8_v3.py",
    "scripts/nfl/run_offline_if_eval_w8_t4850u_v3.py",
)
RESULT_COMPARE = (
    "margin_mu",
    "total_mu",
    "spread_home",
    "home_win_prob",
    "away_win_prob",
    "fair_home_ml",
    "fair_away_ml",
    "seed",
    "market_blend",
    "rating_week",
)
REST_COMPARE = ("rest_days_home", "rest_days_away")


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def require_execution_tip_clean() -> str:
    """Write-packet only when rest/v3 sources match HEAD (invoke == declared tip)."""
    head = _git("rev-parse", "HEAD")
    dirty = _git("diff", "--name-only", "HEAD", "--", *SOURCE_GUARD)
    if dirty:
        raise EvalW8Reject(
            "EXECUTION_TIP_DIRTY",
            f"sources dirty vs HEAD {head[:8]}: {dirty}. Commit then re-invoke.",
        )
    try:
        _git("merge-base", "--is-ancestor", REST_FIX_TIP, head)
    except subprocess.CalledProcessError as exc:
        raise EvalW8Reject(
            "REST_FIX_NOT_IN_TIP",
            f"{REST_FIX_TIP_SHORT} is not an ancestor of {head}",
        ) from exc
    if head == V2_INVOKE_PARENT:
        raise EvalW8Reject("INVOKE_AT_PARENT", "execution tip must not be v2 invoke parent 426bd1d9")
    return head


def _close(left: Any, right: Any) -> bool:
    if left is None and right is None:
        return True
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)
    return left == right


def load_v2_baseline() -> Dict[str, Any]:
    results = json.loads((V2_DIR / "RESULTS.json").read_text(encoding="utf-8"))
    eligibility = json.loads((V2_DIR / "ELIGIBILITY.json").read_text(encoding="utf-8"))
    return {
        "results": {row["game_id"]: row for row in results},
        "eligibility": {row["game_id"]: row for row in eligibility},
        "sha256sums": (V2_DIR / "SHA256SUMS").read_text(encoding="utf-8"),
    }


def compare_to_v2(
    eligibility: Sequence[Mapping[str, Any]],
    results: Sequence[Mapping[str, Any]],
    baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    changed: List[Dict[str, Any]] = []
    unchanged: List[str] = []
    for row in results:
        game_id = str(row["game_id"])
        before_r = baseline["results"][game_id]
        before_e = baseline["eligibility"][game_id]
        after_e = next(item for item in eligibility if item["game_id"] == game_id)
        deltas: Dict[str, Any] = {}
        for key in RESULT_COMPARE:
            old, new = before_r.get(key), row.get(key)
            if not _close(old, new):
                deltas[key] = {"before": old, "after": new}
        for key in REST_COMPARE:
            old, new = (before_e.get("rest") or {}).get(key), (after_e.get("rest") or {}).get(key)
            if not _close(old, new):
                deltas[key] = {"before": old, "after": new}
        if deltas:
            changed.append(
                {
                    "game_id": game_id,
                    "changed": True,
                    "deltas": deltas,
                    "before_rest": (before_e.get("rest") or {}).get("rest_days_home"),
                    "after_rest": (after_e.get("rest") or {}).get("rest_days_home"),
                }
            )
        else:
            unchanged.append(game_id)
    return {
        "baseline_packet": "eval_w8_t4850u_v2",
        "baseline_packet_tip": V2_PACKET_TIP,
        "n_changed": len(changed),
        "n_unchanged": len(unchanged),
        "changed": changed,
        "unchanged": unchanged,
        "phi_was_changed": any(item["game_id"] == "2026-W08-PHI@WAS" for item in changed),
        "chi_sea_changed": any(item["game_id"] == "2026-W08-CHI@SEA" for item in changed),
    }


def render_before_after_md(doc: Mapping[str, Any]) -> str:
    lines = [
        "# BEFORE/AFTER t4850u v3 vs sealed v2",
        "",
        f"Baseline packet `eval_w8_t4850u_v2/` tip `{V2_PACKET_TIP_SHORT}`.",
        f"Changed `{doc['n_changed']}` · unchanged `{doc['n_unchanged']}`.",
        "",
        "## Changed",
        "",
    ]
    for item in doc.get("changed") or []:
        lines.append(f"### {item['game_id']}")
        lines.append("")
        lines.append(f"- rest_days before `{item['before_rest']}` → after `{item['after_rest']}`")
        for key, pair in (item.get("deltas") or {}).items():
            lines.append(f"- `{key}`: `{pair['before']}` → `{pair['after']}`")
        lines.append("")
    lines.extend(["## Unchanged", ""])
    if not doc.get("unchanged"):
        lines.append("None.")
    for game_id in doc.get("unchanged") or []:
        lines.append(f"- `{game_id}`")
    lines.extend(["", "≠FREE_PUBLIC ≠BETTING ≠E1. NFL NO-GO · CERT=0.", ""])
    return "\n".join(lines)


def run_eval_slate_v3(*, write: bool = False) -> Dict[str, Any]:
    if write:
        execution_tip = require_execution_tip_clean()
    else:
        execution_tip = _git("rev-parse", "HEAD")
    run_id = (
        f"eval-w8-t4850u-v3-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{uuid4().hex[:8]}"
    )
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    audit = CallAudit()
    commits = resolve_commits()
    if commits["head"] != execution_tip:
        raise EvalW8Reject("HEAD_DRIFT", f"{commits['head']} != {execution_tip}")
    baseline = load_v2_baseline()
    with audit, redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        print(f"RUN_ID={run_id}", flush=True)
        print(f"CMD={CMD}", flush=True)
        print(f"HEAD={execution_tip}", flush=True)
        print(f"EXECUTION_TIP={execution_tip}", flush=True)
        print(f"BASELINE_V2_TIP={V2_PACKET_TIP}", flush=True)
        print(f"REST_FIX_TIP={REST_FIX_TIP}", flush=True)
        print(f"LINEAGE_BASE={LINEAGE_BASE} ({LINEAGE_BASE_FULL})", flush=True)
        print("PR=667 DRAFT", flush=True)
        panel = load_panel()
        schedule = load_schedule()
        history = history_w1_w7(schedule)
        by_id = {str(g["game_id"]): g for g in schedule.get("games") or []}
        eligibility: List[Dict[str, Any]] = []
        results: List[Dict[str, Any]] = []
        for game_id in SUPPORTED_GAMES:
            req, elig = build_eval_request(
                game_id=game_id,
                schedule_game=by_id[game_id],
                panel=panel,
                history=history,
            )
            print(
                f"INVOKE {game_id} seed={req.seed} sims={req.simulations} "
                f"rest={elig['rest']['rest_days_home']}",
                flush=True,
            )
            row = invoke_diagnostic_v2(req)
            row["note"] = (
                "EVAL_ONLY diagnostic v3 re-execution after ET rest_days. "
                "Not an admissible E1 forecast. IF-derived win-prob/ML are not Odds."
            )
            eligibility.append(elig)
            results.append(row)
        print(f"INVOKED={len(results)}", flush=True)
        print(f"INVOKE_AT_EXECUTION_TIP={execution_tip}", flush=True)

    stdout_text = stdout_buf.getvalue()
    stderr_text = stderr_buf.getvalue()
    if audit.forbidden_hits:
        raise EvalW8Reject("FORBIDDEN_CALL", f"forbidden calls: {audit.forbidden_hits}")
    if f"HEAD={execution_tip}" not in stdout_text:
        raise EvalW8Reject("INVOKE_HEAD_MISSING", "invoke log missing declared execution tip")

    before_after = compare_to_v2(eligibility, results, baseline)
    operational = operational_w8_still_blocked()
    caller = evaluate_caller(write=False)
    if not operational["blocked"] or caller.status != "BLOCKED" or REJECT_THROUGH_W8 not in caller.codes:
        raise EvalW8Reject("OPERATIONAL_PATH_NOT_BLOCKED", "W8/W9 operational path must stay BLOCKED")

    unresolved = build_unresolved([], eligibility)
    pins = eval_pins()
    pins["eval"]["execution_tip"] = execution_tip
    pins["eval"]["execution_tip_short"] = execution_tip[:8]
    pins["eval"]["baseline_v2_packet_tip"] = V2_PACKET_TIP
    pins["eval"]["rest_fix_tip"] = REST_FIX_TIP
    pins["eval"]["pr"] = PR_NUMBER
    pins["eval"]["run_id"] = run_id
    manifest = {
        "run_id": run_id,
        "agent_bc": AGENT_BC,
        "pr": PR_NUMBER,
        "label": "DIAGNOSTIC / EVAL_ONLY",
        "packet_version": "t4850u_v3",
        "public_delivery": False,
        "e1_admissible": False,
        "scoring_admissible_now": False,
        "cmd": CMD,
        "execution_tip": execution_tip,
        "execution_tip_short": execution_tip[:8],
        "invoke_head": execution_tip,
        "invoke_head_matches_execution_tip": True,
        "baseline_v2_packet_tip": V2_PACKET_TIP,
        "baseline_v2_packet_tip_short": V2_PACKET_TIP_SHORT,
        "rest_fix_tip": REST_FIX_TIP,
        "rest_fix_tip_short": REST_FIX_TIP_SHORT,
        "v2_invoke_parent_not_used": V2_INVOKE_PARENT,
        "lineage_base": LINEAGE_BASE,
        "lineage_base_full": LINEAGE_BASE_FULL,
        "diff_vs_b6d019b0": diff_vs_base(LINEAGE_BASE),
        "owner_clear": OWNER_CLEAR,
        "owner_clear_sha8": OWNER_CLEAR_SHA,
        "v1_dir_untouched": True,
        "v2_dir_untouched": True,
        "config": {
            "if_blend": 0,
            "source_pin": "52d9e909",
            "as_of": "cf514078",
            "rating_week": RATING_WEEK,
            "target_week": TARGET_WEEK,
            "season": SEASON,
            "through_w7": THROUGH_W7_ACCEPT,
            "panel": PANEL_SHA256,
            "schedule": SCHEDULE_SHA256,
            "simulations": EVAL_SIMULATIONS,
            "seed_base": EVAL_SEED_BASE,
            "tnf_excluded": TNF_GAME_ID,
            "bye_rolling_as_of": BYE_ROLLING_AS_OF,
            "rest_days": "America/New_York kick local date",
            "sportsbook": False,
            "hl": False,
            "odds": False,
            "c10": False,
            "railway": False,
        },
    }
    packet = {
        "status": "DIAGNOSTIC_SEALED",
        "eval_class": "EVAL_ONLY",
        "packet_version": "t4850u_v3",
        "run_id": run_id,
        "pr": PR_NUMBER,
        "execution_tip": execution_tip,
        "execution_tip_short": execution_tip[:8],
        "e1_admissible": False,
        "scoring_admissible": False,
        "scoring_admissible_now": False,
        "public_delivery": False,
        "n_supported": 13,
        "n_invoked": len(results),
        "n_fail_closed": 0,
        "tnf_excluded": TNF_GAME_ID,
        "cmd": CMD,
        "pins": pins,
        "operational_path": operational,
        "before_after": {
            "n_changed": before_after["n_changed"],
            "n_unchanged": before_after["n_unchanged"],
            "phi_was_changed": before_after["phi_was_changed"],
            "chi_sea_changed": before_after["chi_sea_changed"],
        },
    }
    controls = refuse_public_delivery(packet)
    packet["publication_controls"] = controls
    findings = {
        "readiness_1_wired_admissible_run": {
            "wired_diagnostic_run": len(results) == 13,
            "scoring_admissible": False,
            "e1_admissible": False,
            "fact": (
                f"13/13 remaining W8 games re-invoked Independent Fair at execution tip "
                f"{execution_tip[:8]} (blend=0, rating_week=7, through-W7 {THROUGH_W7_ACCEPT}, "
                f"ET rest_days). DIAGNOSTIC, not E1."
            ),
        },
        "readiness_4_coherence": {
            "status": "DIAGNOSTIC_IF_ONLY",
            "joint_st_ml": "INSUFFICIENT",
            "fact": (
                "No sealed joint ST/ML coherence packet. Do not treat omitted failed "
                "coherence outputs as validation of remaining prices."
            ),
        },
        "readiness_6_fail_closed": {
            "tnf_excluded": True,
            "operational_through_w8_still_blocked": True,
            "fact": (
                "TNF CAR@GB rejected; operational THROUGH_W8_DATA_ACCEPT_MISSING; "
                "utc_et_dow_mismatch keeps VERIFY_AT_CONSUME; no invented rest."
            ),
        },
        "readiness_8_publication_controls": {
            "prepared": True,
            "enabled": False,
            "public_delivery": False,
            "fact": "Controls tested. Public delivery not enabled.",
        },
    }
    out = {
        "manifest": manifest,
        "eligibility": eligibility,
        "results": results,
        "unresolved": unresolved,
        "findings": findings,
        "publication_controls": controls,
        "packet": packet,
        "call_audit": audit.report(),
        "logs": {"stdout": stdout_text, "stderr": stderr_text},
        "pins": pins,
        "before_after": before_after,
    }
    refuse_public_delivery(packet)
    if write:
        _write_v3(out, baseline["sha256sums"])
    return out


def _write_v3(artifacts: Mapping[str, Any], v2_sha256sums: str) -> None:
    V3_DIR.mkdir(parents=True, exist_ok=True)
    dest = V3_DIR / "inputs"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("team_efficiency_current_through_w7.json", "ACCEPT.json"):
        dest.joinpath(name).write_bytes((V2_DIR / "inputs" / name).read_bytes())
    (V3_DIR / "V2_BASELINE_SHA256SUMS").write_text(v2_sha256sums, encoding="utf-8")
    mapping = {
        "MANIFEST.json": artifacts["manifest"],
        "ELIGIBILITY.json": artifacts["eligibility"],
        "RESULTS.json": artifacts["results"],
        "UNRESOLVED.json": artifacts["unresolved"],
        "FINDINGS.json": artifacts["findings"],
        "PUBLICATION_CONTROLS.json": artifacts["publication_controls"],
        "DIAGNOSTIC_PACKET.json": artifacts["packet"],
        "PINS.json": artifacts["pins"],
        "CALL_AUDIT.json": artifacts["call_audit"],
        "INVOKE_LOG.json": artifacts["logs"],
        "BEFORE_AFTER.json": artifacts["before_after"],
    }
    for name, payload in mapping.items():
        (V3_DIR / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
    (V3_DIR / "BEFORE_AFTER.md").write_text(
        render_before_after_md(artifacts["before_after"]), encoding="utf-8"
    )
    (V3_DIR / "INVOKE_STDOUT.txt").write_text(artifacts["logs"]["stdout"], encoding="utf-8")
    (V3_DIR / "INVOKE_STDERR.txt").write_text(artifacts["logs"]["stderr"] or "", encoding="utf-8")
    (V3_DIR / "DIAGNOSTIC_PACKET.md").write_text(_render_packet_md(artifacts), encoding="utf-8")
    (V3_DIR / "FINDINGS.md").write_text(_render_findings_md(artifacts), encoding="utf-8")
    from src.services.nfl_offline_if_eval_w8_v2 import render_unresolved_md

    (V3_DIR / "UNRESOLVED.md").write_text(
        render_unresolved_md(artifacts["unresolved"]), encoding="utf-8"
    )
    _write_sha256sums()


def _write_sha256sums() -> None:
    lines = []
    for path in sorted(V3_DIR.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        rel = path.relative_to(V3_DIR).as_posix()
        lines.append(f"{sha256_file(path)}  {rel}")
    (V3_DIR / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_packet_md(artifacts: Mapping[str, Any]) -> str:
    m = artifacts["manifest"]
    packet = artifacts["packet"]
    return "\n".join(
        [
            "# DIAGNOSTIC PACKET t4850u v3 — EVAL_ONLY W8 re-execution",
            "",
            f"**Status:** `{packet.get('status')}`",
            f"**run_id:** `{m['run_id']}`",
            f"**execution_tip:** `{m['execution_tip_short']}` (`{m['execution_tip']}`)",
            f"**invoke_head_matches_execution_tip:** `{m['invoke_head_matches_execution_tip']}`",
            f"**baseline v2 tip:** `{V2_PACKET_TIP_SHORT}` · **rest_fix:** `{REST_FIX_TIP_SHORT}`",
            f"- cmd `{CMD}`",
            f"- #667 DRAFT · agent `{AGENT_BC}`",
            f"**Invoked:** {packet.get('n_invoked')}/13 · TNF excluded `{TNF_GAME_ID}`",
            f"**e1_admissible:** false · **scoring_admissible_now:** false · **public_delivery:** false",
            "",
            "IF blend=0 · rating_week=7 · through-W7 c674da77 · ET rest_days.",
            "≠FREE_PUBLIC ≠BETTING ≠E1 ≠merge. NFL NO-GO · CERT=0 · Coming Soon ON.",
            "",
        ]
    )


def _render_findings_md(artifacts: Mapping[str, Any]) -> str:
    findings = artifacts["findings"]
    return "\n".join(
        [
            "# Engineering findings t4850u v3 (facts only)",
            "",
            "## #1 wired admissible run",
            findings["readiness_1_wired_admissible_run"]["fact"],
            "",
            "## #4 coherence",
            findings["readiness_4_coherence"]["fact"],
            "",
            "## #6 fail-closed",
            findings["readiness_6_fail_closed"]["fact"],
            "",
            "## #8 publication controls",
            findings["readiness_8_publication_controls"]["fact"],
            "",
            "≠FREE_PUBLIC ≠BETTING. NFL NO-GO · CERT=0.",
            "",
        ]
    )
