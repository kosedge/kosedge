"""t4850u v2 — EVAL_ONLY diagnostic packet (Alex RO t4851u HARD-gap close).

Paper add-only under OWNER CLEAR a936f86d. Does not rewrite eval_w8_t4850u/.
Does not merge, publish, emit E1, or touch the W9 path.
"""

from __future__ import annotations

import io
import json
import os
import socket
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from uuid import uuid4

from src.services.nfl_offline_if_caller import (
    ASOF_MODULE_SHA256,
    CALLER_MODE_DRY_RUN,
    IF_SOURCE_PIN_SHA256,
    OfflineIfCallerReject,
    REJECT_ASOF,
    REJECT_INPUTS,
    REJECT_SOURCE_PIN,
    build_contract_inputs,
    enforce_asof_and_history,
    sha256_file,
    verify_asof_module,
    verify_source_pin,
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
    refuse_public_delivery,
    run_eval_slate,
)
from src.services.nfl_simulator import (
    independent_fair_mus,
    simulate_nfl_game_independent_fair,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
V1_DIR = REPO_ROOT / "data" / "ops" / "nfl-offline-if-caller-t4838u" / "eval_w8_t4850u"
V2_DIR = REPO_ROOT / "data" / "ops" / "nfl-offline-if-caller-t4838u" / "eval_w8_t4850u_v2"
CLI_REL = "scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py"
PARENT_TIP = "426bd1d9"
PARENT_TIP_FULL = "426bd1d9e7d3eed4e9bf1166caa2b558862e7551"
LINEAGE_BASE = "b6d019b0"
LINEAGE_BASE_FULL = "b6d019b051f13156354504097d1635b64ab7ceae"
PR_NUMBER = 667
AGENT_BC = "bc-09ab3a07-8e33-54d4-bfdf-e71c44d61c0c"
ALEX_RO_BLOCKED = "4ca263b307bf510aaf8c6747cc16c277a22f6ff997460628167bec7d7bfd31d1"
OWNER_CLEAR_SHA = "a936f86d"
CMD = f"PYTHONPATH=services/model-service python3 {CLI_REL} --write-packet"
TEST_6_1_CMD = (
    f"PYTHONPATH=services/model-service python3 {CLI_REL} --test-6-1-missing-field"
)
TEST_6_3_CMD = (
    f"PYTHONPATH=services/model-service python3 {CLI_REL} --test-6-3-pin-mismatch"
)
FORBIDDEN_MODULE_SUBSTR = (
    "odds_api",
    "odds_client",
    "nfl_odds",
    "railway",
    "celery",
    "handicap_ledger",
    "nfl_kei",
    "stripe",
)


class CallAudit:
    """Record network/module activity. Fail closed if forbidden *new* calls occur."""

    def __init__(self) -> None:
        self.socket_attempts: List[str] = []
        self.forbidden_hits: List[str] = []
        self.modules_seen: List[str] = []
        self.preexisting: List[str] = []
        self._orig_connect = socket.socket.connect
        self._modules_at_enter: set[str] = set()

    def __enter__(self) -> "CallAudit":
        audit = self
        self._modules_at_enter = set(sys.modules)
        self.preexisting = sorted(
            name
            for name in self._modules_at_enter
            if any(token in name.lower() for token in FORBIDDEN_MODULE_SUBSTR)
        )

        def blocked_connect(sock, address):  # type: ignore[no-untyped-def]
            target = str(address)
            audit.socket_attempts.append(target)
            audit.forbidden_hits.append(f"socket.connect:{target}")
            raise OSError(f"EVAL_ONLY network blocked: {target}")

        socket.socket.connect = blocked_connect  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: object) -> None:
        socket.socket.connect = self._orig_connect  # type: ignore[method-assign]
        new_names = sorted(set(sys.modules) - self._modules_at_enter)
        self.modules_seen = [
            name
            for name in new_names
            if any(token in name.lower() for token in FORBIDDEN_MODULE_SUBSTR)
        ]
        for name in self.modules_seen:
            self.forbidden_hits.append(f"module:{name}")

    def report(self) -> Dict[str, Any]:
        return {
            "odds_calls": 0,
            "c10_calls": 0,
            "railway_calls": 0,
            "hl_adjustments": 0,
            "socket_attempts": self.socket_attempts,
            "new_forbidden_modules": self.modules_seen,
            "preexisting_matching_modules": self.preexisting,
            "forbidden_hits": self.forbidden_hits,
            "network_blocked": True,
            "passed": not self.forbidden_hits and not self.socket_attempts,
            "note": (
                "socket.socket.connect patched closed for the diagnostic invoke. "
                "passed=true means no Odds/C10/Railway/HL/network calls during this run. "
                "preexisting_matching_modules are informational only (already imported)."
            ),
        }


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def resolve_commits() -> Dict[str, str]:
    head = _git("rev-parse", "HEAD")
    try:
        parent_full = _git("rev-parse", PARENT_TIP)
    except subprocess.CalledProcessError:
        parent_full = PARENT_TIP_FULL
    try:
        base_full = _git("rev-parse", LINEAGE_BASE)
    except subprocess.CalledProcessError:
        base_full = LINEAGE_BASE_FULL
    return {
        "head": head,
        "head_short": head[:8],
        "parent_v1_tip": PARENT_TIP,
        "parent_v1_tip_full": parent_full,
        "lineage_base": LINEAGE_BASE,
        "lineage_base_full": base_full,
    }


def diff_vs_base(base: str) -> Dict[str, Any]:
    stat = _git("diff", "--stat", f"{base}..HEAD")
    names = _git("diff", "--name-only", f"{base}..HEAD")
    return {
        "base": base,
        "base_full": LINEAGE_BASE_FULL,
        "stat": stat,
        "files": [line for line in names.splitlines() if line],
    }


def enrich_result(base: Mapping[str, Any], projection: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    row = dict(base)
    markets = (projection or {}).get("markets") if isinstance(projection, dict) else None
    if not isinstance(markets, dict):
        row.update(
            {
                "home_win_prob": None,
                "away_win_prob": None,
                "fair_home_ml": None,
                "fair_away_ml": None,
                "ml_source": None,
                "ml_null_reason": "IF markets block missing; not imputed",
            }
        )
        return row
    row.update(
        {
            "home_win_prob": markets.get("home_win_prob"),
            "away_win_prob": markets.get("away_win_prob"),
            "fair_home_ml": markets.get("fair_home_ml"),
            "fair_away_ml": markets.get("fair_away_ml"),
            "total_mean": markets.get("total_mean"),
            "ml_source": (
                "simulate_nfl_game_independent_fair.markets "
                "(IF blend=0; not sportsbook/Odds)"
            ),
            "ml_null_reason": None,
        }
    )
    return row


def invoke_diagnostic_v2(req: Any) -> Dict[str, Any]:
    if req.mode != CALLER_MODE_DRY_RUN:
        raise EvalW8Reject("E1_LABEL_FORBIDDEN", "v2 eval is DIAGNOSTIC only")
    verify_source_pin()
    verify_asof_module()
    enforce_asof_and_history(req)
    inputs = build_contract_inputs(req)
    projection = simulate_nfl_game_independent_fair(
        inputs,
        simulations=req.simulations,
        seed=req.seed,
        market_spread_home=None,
        market_total=None,
    )
    blend = projection["independent_fair"]["market_blend"]
    if blend != 0:
        raise EvalW8Reject("BLEND_NOT_ZERO", f"blend {blend} != 0")
    margin_mu, total_mu = independent_fair_mus(projection)
    row = {
        "game_id": req.game_id,
        "forecast_class": "DIAGNOSTIC",
        "e1": False,
        "e1_admissible": False,
        "e1_label": None,
        "scoring_admissible": False,
        "scoring_admissible_now": False,
        "public_delivery": False,
        "independent_fair_invoked": True,
        "market_blend": 0,
        "rating_week": RATING_WEEK,
        "target_week": TARGET_WEEK,
        "simulations": req.simulations,
        "seed": req.seed,
        "margin_mu": margin_mu,
        "total_mu": total_mu,
        "sigma": float(projection["independent_fair"]["sigma"]),
        "spread_home": round(-margin_mu, 2),
        "note": (
            "EVAL_ONLY diagnostic v2. Not an admissible E1 forecast. "
            "IF-derived win-prob/ML are model outputs, not Odds."
        ),
    }
    return enrich_result(row, projection)


def evidence_gaps(eligibility: Sequence[Mapping[str, Any]]) -> List[Dict[str, str]]:
    gaps = [
        {
            "id": "THROUGH_W8_DATA_ACCEPT",
            "class": "EVIDENCE_GAP",
            "detail": (
                "through-W8 DATA ACCEPT absent — DATA_PARTIAL preserved; "
                "operational E1 path remains BLOCKED"
            ),
        },
        {
            "id": "COHERENCE_JOINT_ST_ML",
            "class": "EVIDENCE_GAP",
            "detail": (
                "#4 joint ST/ML coherence packet INSUFFICIENT — IF mus+win-prob "
                "present; not a PASS_RO coherence seal; do not infer remaining "
                "prices are valid"
            ),
        },
        {
            "id": "MARKET_BEAT",
            "class": "EVIDENCE_GAP",
            "detail": "#5/#7 market-beat INSUFFICIENT — Odds HOLD; no market evidence invented",
        },
        {
            "id": "FREE_PUBLIC",
            "class": "EVIDENCE_GAP",
            "detail": (
                "FREE_PUBLIC not CLEARed — publication controls refuse delivery "
                "(Coming Soon ON, CERT=0)"
            ),
        },
        {
            "id": "REST_DAYS_VERIFY_AT_CONSUME",
            "class": "CONDITIONAL",
            "detail": "rest_days VERIFY_AT_CONSUME — UTC DOW heuristic; bye rest not added",
        },
    ]
    for row in eligibility:
        rest = row.get("rest") or {}
        if row.get("status") == "SUPPORTED" and rest.get("utc_et_dow_mismatch"):
            gaps.append(
                {
                    "id": f"REST_MISMATCH_{row['game_id']}",
                    "class": "CONDITIONAL",
                    "detail": (
                        f"{row['game_id']} rest={rest['rest_days_home']} "
                        f"dow_utc={rest['dow_utc']} dow_et={rest['dow_et']} UTC/ET mismatch"
                    ),
                }
            )
    return gaps


def build_unresolved(
    invocation: Sequence[Mapping[str, Any]],
    eligibility: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    return {
        "invocation_failures": list(invocation),
        "evidence_gaps": evidence_gaps(eligibility),
        "scoring_admissible_now": False,
        "e1_admissible": False,
    }


def render_unresolved_md(doc: Mapping[str, Any]) -> str:
    lines = [
        "# Unresolved t4850u v2",
        "",
        "## Invocation failures",
        "None." if not doc.get("invocation_failures") else "",
    ]
    for item in doc.get("invocation_failures") or []:
        lines.append(f"- `{item.get('game_id')}` `{item.get('code')}` {item.get('message', '')}")
    lines.extend(["", "## Evidence / decision gaps (not invocation failures)", ""])
    for item in doc.get("evidence_gaps") or []:
        lines.append(f"- **{item['id']}** ({item['class']}): {item['detail']}")
    lines.extend(
        [
            "",
            f"scoring_admissible_now=`{doc.get('scoring_admissible_now')}` · "
            f"e1_admissible=`{doc.get('e1_admissible')}`",
            "",
            "≠FREE_PUBLIC ≠BETTING. NFL NO-GO · CERT=0.",
            "",
        ]
    )
    return "\n".join(lines)


def test_6_1_missing_field() -> Dict[str, Any]:
    """Induced missing required field → REJECT, never impute."""
    panel = load_panel()
    schedule = load_schedule()
    history = history_w1_w7(schedule)
    by_id = {str(g["game_id"]): g for g in schedule.get("games") or []}
    req, _ = build_eval_request(
        game_id=SUPPORTED_GAMES[0],
        schedule_game=by_id[SUPPORTED_GAMES[0]],
        panel=panel,
        history=history,
    )
    efficiency = dict(req.efficiency)
    del efficiency["home_off_epa_5g"]
    req.efficiency = efficiency
    try:
        build_contract_inputs(req)
        return {
            "test": "6.1",
            "passed": False,
            "exit_code": 1,
            "code": None,
            "message": "missing field was imputed or accepted",
            "imputed": True,
        }
    except OfflineIfCallerReject as exc:
        passed = exc.code == REJECT_INPUTS and "home_off_epa_5g" in exc.message
        return {
            "test": "6.1",
            "passed": passed,
            "exit_code": 2 if passed else 1,
            "code": exc.code,
            "message": exc.message,
            "imputed": False,
            "field": "home_off_epa_5g",
            "contract": "b41f4b43 §3/§7",
        }


def test_6_3_pin_mismatch() -> Dict[str, Any]:
    """Source pin or as-of mismatch must fail closed (non-zero exit)."""
    results: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="t4850u-v2-6-3-") as tmp:
        fake_sim = Path(tmp) / "tmp_fake_simulator.py"
        fake_sim.write_text("not-the-source-pin\n", encoding="utf-8")
        try:
            verify_source_pin(simulator_path=fake_sim)
            results.append({"kind": "source_pin", "rejected": False})
        except OfflineIfCallerReject as exc:
            results.append(
                {
                    "kind": "source_pin",
                    "rejected": True,
                    "code": exc.code,
                    "message": exc.message,
                    "expected": REJECT_SOURCE_PIN,
                }
            )
        fake_asof = Path(tmp) / "tmp_fake_asof.py"
        fake_asof.write_text("not-the-asof-module\n", encoding="utf-8")
        try:
            verify_asof_module(asof_path=fake_asof)
            results.append({"kind": "asof_module", "rejected": False})
        except OfflineIfCallerReject as exc:
            results.append(
                {
                    "kind": "asof_module",
                    "rejected": True,
                    "code": exc.code,
                    "message": exc.message,
                    "expected": REJECT_ASOF,
                }
            )
    passed = all(item.get("rejected") for item in results) and len(results) == 2
    return {
        "test": "6.3",
        "passed": passed,
        "exit_code": 3 if passed else 1,
        "cases": results,
        "expected_pins": {
            "source_only": IF_SOURCE_PIN_SHA256,
            "asof_module": ASOF_MODULE_SHA256,
        },
    }


def capture_cli(flag: str) -> Dict[str, Any]:
    script = REPO_ROOT / CLI_REL
    env = os.environ.copy()
    ms = str(REPO_ROOT / "services" / "model-service")
    env["PYTHONPATH"] = ms + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(
        [sys.executable, str(script), flag],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return {
        "cmd": f"PYTHONPATH=services/model-service python3 {CLI_REL} {flag}",
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_eval_slate_v2(*, write: bool = False, tip_override: Optional[str] = None) -> Dict[str, Any]:
    run_id = (
        f"eval-w8-t4850u-v2-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{uuid4().hex[:8]}"
    )
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    audit = CallAudit()
    commits = resolve_commits()
    with audit, redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        print(f"RUN_ID={run_id}", flush=True)
        print(f"CMD={CMD}", flush=True)
        print(f"HEAD={commits['head']}", flush=True)
        print(f"PARENT_V1_TIP={PARENT_TIP} ({PARENT_TIP_FULL})", flush=True)
        print(f"LINEAGE_BASE={LINEAGE_BASE} ({LINEAGE_BASE_FULL})", flush=True)
        print(f"PR=667 DRAFT", flush=True)
        artifacts = run_eval_slate(write=False)
        panel = load_panel()
        schedule = load_schedule()
        history = history_w1_w7(schedule)
        by_id = {str(g["game_id"]): g for g in schedule.get("games") or []}
        v2_results: List[Dict[str, Any]] = []
        for game_id in SUPPORTED_GAMES:
            req, _ = build_eval_request(
                game_id=game_id,
                schedule_game=by_id[game_id],
                panel=panel,
                history=history,
            )
            print(f"INVOKE {game_id} seed={req.seed} sims={req.simulations}", flush=True)
            v2_results.append(invoke_diagnostic_v2(req))
        print(f"INVOKED={len(v2_results)}", flush=True)

    stdout_text = stdout_buf.getvalue()
    stderr_text = stderr_buf.getvalue()
    if audit.forbidden_hits:
        raise EvalW8Reject("FORBIDDEN_CALL", f"forbidden calls: {audit.forbidden_hits}")

    test_61 = test_6_1_missing_field()
    test_63 = test_6_3_pin_mismatch()
    cli_61: Dict[str, Any] = {}
    cli_63: Dict[str, Any] = {}
    if write:
        cli_61 = capture_cli("--test-6-1-missing-field")
        cli_63 = capture_cli("--test-6-3-pin-mismatch")
        test_61 = {**test_61, "cli": cli_61}
        test_63 = {**test_63, "cli": cli_63}
        if cli_61.get("exit_code") != 2:
            raise EvalW8Reject("TEST_6_1_EXIT", f"expected exit 2, got {cli_61.get('exit_code')}")
        if cli_63.get("exit_code") != 3:
            raise EvalW8Reject("TEST_6_3_EXIT", f"expected exit 3, got {cli_63.get('exit_code')}")

    unresolved = build_unresolved([], artifacts["eligibility"])
    tip = tip_override or commits["head"]
    tip_short = tip[:8]
    manifest = {
        "run_id": run_id,
        "agent_bc": AGENT_BC,
        "pr": PR_NUMBER,
        "label": "DIAGNOSTIC / EVAL_ONLY",
        "public_delivery": False,
        "e1_admissible": False,
        "scoring_admissible_now": False,
        "cmd": CMD,
        "test_6_1_cmd": TEST_6_1_CMD,
        "test_6_3_cmd": TEST_6_3_CMD,
        "pr_head": commits["head"],
        "pr_head_short": commits["head_short"],
        "packet_tip": tip,
        "packet_tip_short": tip_short,
        "parent_v1_tip": PARENT_TIP,
        "parent_v1_tip_full": commits["parent_v1_tip_full"],
        "lineage_base": LINEAGE_BASE,
        "lineage_base_full": commits["lineage_base_full"],
        "diff_vs_b6d019b0": diff_vs_base(LINEAGE_BASE),
        "commits_in_packet": [PARENT_TIP, PARENT_TIP_FULL, tip, tip_short, LINEAGE_BASE],
        "alex_ro_blocked": ALEX_RO_BLOCKED,
        "owner_clear": OWNER_CLEAR,
        "owner_clear_sha8": OWNER_CLEAR_SHA,
        "v1_dir_untouched": True,
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
            "sportsbook": False,
            "hl": False,
            "odds": False,
            "c10": False,
            "railway": False,
        },
    }
    pins = eval_pins()
    pins["eval"]["caller_tip"] = LINEAGE_BASE
    pins["eval"]["parent_v1_tip"] = PARENT_TIP
    pins["eval"]["parent_v1_tip_full"] = PARENT_TIP_FULL
    pins["eval"]["packet_tip"] = tip
    pins["eval"]["packet_tip_short"] = tip_short
    pins["eval"]["pr"] = PR_NUMBER
    pins["eval"]["run_id"] = run_id
    packet = dict(artifacts["packet"])
    packet.update(
        {
            "packet_version": "t4850u_v2",
            "run_id": run_id,
            "pr": PR_NUMBER,
            "packet_tip": tip,
            "packet_tip_short": tip_short,
            "parent_v1_tip": PARENT_TIP,
            "parent_v1_tip_full": PARENT_TIP_FULL,
            "lineage_base": LINEAGE_BASE,
            "cmd": CMD,
            "scoring_admissible_now": False,
            "e1_admissible": False,
            "pins": pins,
        }
    )
    findings = dict(artifacts["findings"])
    findings["readiness_1_wired_admissible_run"]["fact"] = (
        f"13/13 remaining W8 games invoked Independent Fair (blend=0, rating_week=7, "
        f"through-W7 {THROUGH_W7_ACCEPT}). Packet tip {tip_short} on #667 DRAFT "
        f"(parent v1 {PARENT_TIP} / {PARENT_TIP_FULL}, lineage {LINEAGE_BASE}). "
        "DIAGNOSTIC, not E1."
    )
    findings["readiness_6_fail_closed"]["fact"] = (
        "TNF CAR@GB rejected; operational invoke still THROUGH_W8_DATA_ACCEPT_MISSING; "
        "#6.1 induced-missing-field REJECT (exit 2); #6.3 pin/as-of mismatch "
        "non-zero exit (exit 3); publication controls refuse FREE_PUBLIC/BETTING."
    )
    findings["test_6_1"] = {
        "passed": test_61.get("passed"),
        "exit_code": (test_61.get("cli") or {}).get("exit_code", test_61.get("exit_code")),
    }
    findings["test_6_3"] = {
        "passed": test_63.get("passed"),
        "exit_code": (test_63.get("cli") or {}).get("exit_code", test_63.get("exit_code")),
    }
    out = {
        "manifest": manifest,
        "eligibility": artifacts["eligibility"],
        "results": v2_results,
        "unresolved": unresolved,
        "findings": findings,
        "publication_controls": artifacts["publication_controls"],
        "packet": packet,
        "call_audit": audit.report(),
        "logs": {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "note": "Captured around v2 slate invoke. Network connect is patched closed.",
        },
        "pins": pins,
        "test_6_1": test_61,
        "test_6_3": test_63,
    }
    refuse_public_delivery(packet)
    if write:
        _write_v2(out)
    return out


def _copy_v1_inputs() -> None:
    src = V1_DIR / "inputs"
    dest = V2_DIR / "inputs"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("team_efficiency_current_through_w7.json", "ACCEPT.json"):
        dest.joinpath(name).write_bytes(src.joinpath(name).read_bytes())


def _write_v2(artifacts: Mapping[str, Any]) -> None:
    V2_DIR.mkdir(parents=True, exist_ok=True)
    _copy_v1_inputs()
    mapping = {
        "MANIFEST.json": artifacts["manifest"],
        "CONFIG.json": artifacts["manifest"]["config"],
        "ELIGIBILITY.json": artifacts["eligibility"],
        "RESULTS.json": artifacts["results"],
        "UNRESOLVED.json": artifacts["unresolved"],
        "FINDINGS.json": artifacts["findings"],
        "PUBLICATION_CONTROLS.json": artifacts["publication_controls"],
        "DIAGNOSTIC_PACKET.json": artifacts["packet"],
        "PINS.json": artifacts["pins"],
        "CALL_AUDIT.json": artifacts["call_audit"],
        "INVOKE_LOG.json": artifacts["logs"],
        "TEST_6_1.json": artifacts["test_6_1"],
        "TEST_6_3.json": artifacts["test_6_3"],
    }
    for name, payload in mapping.items():
        (V2_DIR / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
    (V2_DIR / "UNRESOLVED.md").write_text(
        render_unresolved_md(artifacts["unresolved"]), encoding="utf-8"
    )
    (V2_DIR / "DIAGNOSTIC_PACKET.md").write_text(_render_packet_md(artifacts), encoding="utf-8")
    (V2_DIR / "FINDINGS.md").write_text(_render_findings_md(artifacts), encoding="utf-8")
    (V2_DIR / "MANIFEST.md").write_text(_render_manifest_md(artifacts), encoding="utf-8")
    (V2_DIR / "RESULTS.md").write_text(_render_results_md(artifacts["results"]), encoding="utf-8")
    (V2_DIR / "INVOKE_STDOUT.txt").write_text(artifacts["logs"]["stdout"], encoding="utf-8")
    (V2_DIR / "INVOKE_STDERR.txt").write_text(artifacts["logs"]["stderr"] or "", encoding="utf-8")
    _write_test_sidecar("TEST_6_1", artifacts["test_6_1"])
    _write_test_sidecar("TEST_6_3", artifacts["test_6_3"])
    _write_sha256sums()


def _write_test_sidecar(stem: str, doc: Mapping[str, Any]) -> None:
    cli = doc.get("cli") if isinstance(doc.get("cli"), dict) else {}
    exit_code = cli.get("exit_code", doc.get("exit_code"))
    stdout = cli.get("stdout", json.dumps(doc, indent=2, sort_keys=True))
    stderr = cli.get("stderr", "")
    (V2_DIR / f"{stem}_EXIT.txt").write_text(f"{exit_code}\n", encoding="utf-8")
    (V2_DIR / f"{stem}_STDOUT.txt").write_text(str(stdout), encoding="utf-8")
    (V2_DIR / f"{stem}_STDERR.txt").write_text(str(stderr or ""), encoding="utf-8")
    (V2_DIR / f"{stem}.md").write_text(
        "\n".join(
            [
                f"# {stem} fail-closed evidence",
                "",
                f"- cmd: `{cli.get('cmd') or doc.get('test')}`",
                f"- exit: `{exit_code}`",
                f"- passed: `{doc.get('passed')}`",
                f"- imputed: `{doc.get('imputed', False)}`",
                "",
                "## stdout",
                "",
                "```",
                str(stdout).rstrip(),
                "```",
                "",
                "## stderr",
                "",
                "```",
                str(stderr or "").rstrip(),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_sha256sums() -> None:
    lines = []
    for path in sorted(V2_DIR.rglob("*")):
        if not path.is_file() or path.name in {
            "SHA256SUMS",
            "tmp_fake_simulator.py",
            "tmp_fake_asof.py",
        }:
            continue
        rel = path.relative_to(V2_DIR).as_posix()
        lines.append(f"{sha256_file(path)}  {rel}")
    (V2_DIR / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def stamp_tip(tip: str) -> None:
    manifest_path = V2_DIR / "MANIFEST.json"
    packet_path = V2_DIR / "DIAGNOSTIC_PACKET.json"
    pins_path = V2_DIR / "PINS.json"
    md_path = V2_DIR / "DIAGNOSTIC_PACKET.md"
    manifest_md = V2_DIR / "MANIFEST.md"
    findings_path = V2_DIR / "FINDINGS.json"
    findings_md = V2_DIR / "FINDINGS.md"
    diff = diff_vs_base(LINEAGE_BASE)
    for path in (manifest_path, packet_path, pins_path, findings_path):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if path.name == "PINS.json":
            doc.setdefault("eval", {})
            doc["eval"]["packet_tip"] = tip
            doc["eval"]["packet_tip_short"] = tip[:8]
            doc["eval"]["parent_v1_tip"] = PARENT_TIP
            doc["eval"]["parent_v1_tip_full"] = PARENT_TIP_FULL
        elif path.name == "MANIFEST.json":
            doc["packet_tip"] = tip
            doc["packet_tip_short"] = tip[:8]
            doc["pr_head"] = tip
            doc["pr_head_short"] = tip[:8]
            doc["parent_v1_tip"] = PARENT_TIP
            doc["parent_v1_tip_full"] = PARENT_TIP_FULL
            doc["diff_vs_b6d019b0"] = diff
            doc["commits_in_packet"] = [
                PARENT_TIP,
                PARENT_TIP_FULL,
                tip,
                tip[:8],
                LINEAGE_BASE,
            ]
        elif path.name == "FINDINGS.json":
            fact = doc.get("readiness_1_wired_admissible_run", {}).get("fact", "")
            if fact:
                doc["readiness_1_wired_admissible_run"]["fact"] = (
                    f"13/13 remaining W8 games invoked Independent Fair (blend=0, "
                    f"rating_week=7, through-W7 {THROUGH_W7_ACCEPT}). Packet tip "
                    f"{tip[:8]} on #667 DRAFT (parent v1 {PARENT_TIP} / "
                    f"{PARENT_TIP_FULL}, lineage {LINEAGE_BASE}). DIAGNOSTIC, not E1."
                )
        else:
            doc["packet_tip"] = tip
            doc["packet_tip_short"] = tip[:8]
            doc["parent_v1_tip"] = PARENT_TIP
            doc["parent_v1_tip_full"] = PARENT_TIP_FULL
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for md in (md_path, manifest_md, findings_md):
        if not md.exists():
            continue
        text = md.read_text(encoding="utf-8")
        stamped = []
        replaced = False
        for line in text.splitlines():
            if line.startswith("- #667"):
                stamped.append(
                    f"- #667 DRAFT commit `{tip[:8]}` (`{tip}`) · "
                    f"parent v1 `{PARENT_TIP}` (`{PARENT_TIP_FULL}`) · "
                    f"lineage `{LINEAGE_BASE}`"
                )
                replaced = True
            else:
                stamped.append(line)
        if not replaced:
            stamped.insert(
                4,
                f"- #667 DRAFT commit `{tip[:8]}` (`{tip}`) · parent v1 `{PARENT_TIP}`",
            )
        md.write_text("\n".join(stamped) + "\n", encoding="utf-8")
    _write_sha256sums()


def _render_manifest_md(artifacts: Mapping[str, Any]) -> str:
    m = artifacts["manifest"]
    diff = m.get("diff_vs_b6d019b0") or {}
    return "\n".join(
        [
            "# MANIFEST t4850u v2",
            "",
            f"- run_id `{m['run_id']}`",
            f"- agent `{AGENT_BC}`",
            f"- label `{m['label']}`",
            f"- #667 DRAFT commit `{m['packet_tip_short']}` (`{m['packet_tip']}`)",
            f"- parent v1 tip `{PARENT_TIP}` (`{PARENT_TIP_FULL}`)",
            f"- lineage / diff base `{LINEAGE_BASE}` (`{LINEAGE_BASE_FULL}`)",
            f"- cmd `{CMD}`",
            f"- test 6.1 cmd `{TEST_6_1_CMD}` (expect exit 2)",
            f"- test 6.3 cmd `{TEST_6_3_CMD}` (expect exit 3)",
            f"- public_delivery `{m['public_delivery']}` · scoring_admissible_now false · e1_admissible false",
            "",
            "## config",
            "",
            "```json",
            json.dumps(m["config"], indent=2, sort_keys=True),
            "```",
            "",
            "## diff vs b6d019b0",
            "",
            "```",
            str(diff.get("stat") or ""),
            "```",
            "",
        ]
    )


def _render_results_md(results: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# RESULTS t4850u v2 — IF ST / total / ML (not Odds)",
        "",
        "| game_id | spread_home | total_mu | home_win_prob | away_win_prob | fair_home_ml | fair_away_ml | ml_null_reason |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in results:
        lines.append(
            "| {game_id} | {spread_home} | {total_mu} | {home_win_prob} | {away_win_prob} | {fair_home_ml} | {fair_away_ml} | {ml_null_reason} |".format(
                game_id=row.get("game_id"),
                spread_home=row.get("spread_home"),
                total_mu=row.get("total_mu"),
                home_win_prob=row.get("home_win_prob"),
                away_win_prob=row.get("away_win_prob"),
                fair_home_ml=row.get("fair_home_ml"),
                fair_away_ml=row.get("fair_away_ml"),
                ml_null_reason=row.get("ml_null_reason") or "",
            )
        )
    lines.extend(
        [
            "",
            "ml_source = simulate_nfl_game_independent_fair.markets (IF blend=0).",
            "If a cell is null, ml_null_reason is required and values are not imputed.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_packet_md(artifacts: Mapping[str, Any]) -> str:
    packet = artifacts["packet"]
    m = artifacts["manifest"]
    return "\n".join(
        [
            "# DIAGNOSTIC PACKET t4850u v2 — EVAL_ONLY W8",
            "",
            f"**Status:** `{packet.get('status')}`",
            f"**run_id:** `{m['run_id']}`",
            f"**label:** DIAGNOSTIC / EVAL_ONLY",
            f"- #667 DRAFT commit `{packet.get('packet_tip_short')}` (`{packet.get('packet_tip')}`) · parent v1 `{PARENT_TIP}` (`{PARENT_TIP_FULL}`) · lineage `{LINEAGE_BASE}`",
            f"- cmd `{CMD}`",
            f"- agent `{AGENT_BC}`",
            f"**Invoked:** {packet.get('n_invoked')}/13 · TNF excluded `{TNF_GAME_ID}`",
            f"**e1_admissible:** false · **scoring_admissible_now:** false · **public_delivery:** false",
            "",
            "IF blend=0 · rating_week=7 · through-W7 c674da77 · panel 340a06dd.",
            "≠FREE_PUBLIC ≠BETTING ≠E1 ≠merge. NFL NO-GO · CERT=0 · Coming Soon ON.",
            "",
        ]
    )


def _render_findings_md(artifacts: Mapping[str, Any]) -> str:
    findings = artifacts["findings"]
    return "\n".join(
        [
            "# Engineering findings t4850u v2 (facts only)",
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
