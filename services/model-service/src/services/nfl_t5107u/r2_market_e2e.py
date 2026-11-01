"""R2-B market join E2E — consume sealed R2-A quotes. Not EVAL.

Reads ``R2B_CONSUME.json`` + ``ADMISSIBLE_QUOTES.jsonl`` + coverage
manifest from #694 tip ``3821941d``. Does not rewrite those files.
Does not call ``run_eval_score`` / ``run_eval_score_r2``.

G5 / KO−60 / ≤24h / DK-FD unchanged. CERT=0. No claim.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Callable, Mapping, Sequence

from .dev_research import DEFAULT_FREEZE, DEFAULT_SCHEDULE
from .dev_research_cohort import load_dev_reg_outcomes_from_schedule
from .eval_result_contract import EVAL_RESULT_CONTRACT_KEYS, validate_eval_result_contract
from .evaluator import (
    BENCHMARK_BOOKS,
    BOOT_B,
    BOOT_SEED,
    CUTOFF_MINUTES,
    MAX_QUOTE_AGE_HOURS,
    EvalRefuse,
    home_margin_from_handicap,
    run_paired_margin_eval,
)
from .metric_cohorts import EVAL_METRIC_SPLIT
from .outcome_gate import (
    OutcomeGateRefuse,
    ScoringOutcomeLoader,
    invoke_after_gates,
    refuse_overwrite_first_case_record,
    refuse_preloaded_scoring_outcomes,
    refuse_preserved_t5116u_path,
)

SCHEMA = "nfl-t5119u-r2b-market-e2e-v1"
LABEL = "MARKET_E2E"
CERT_CANDIDATE = 0
READY_FOR_R2B_DEV_E2E = "READY_FOR_R2B_DEV_E2E"

_PKG_ROOT = Path(__file__).resolve().parents[5]
R2A_DIR = _PKG_ROOT / "data/ops/nfl-t5119u-r2-owned-coverage"
CONSUME_PATH = R2A_DIR / "R2B_CONSUME.json"
MANIFEST_PATH = R2A_DIR / "COVERAGE_MANIFEST.json"
QUOTES_PATH = R2A_DIR / "ADMISSIBLE_QUOTES.jsonl"
CONFLICTS_PATH = R2A_DIR / "DUPLICATE_CONFLICTS.json"
COHORTS_PATH = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u/METRIC_COHORTS_t5115u.json"
DEFAULT_DEST = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u/MARKET_E2E_R2B_CONSUME.json"

SEALED_QUOTES_SHA256 = "75c0b14c7391252dd5ca790c09d9d65071916ef4f39a20c81c88c57229917fb9"
SEALED_MANIFEST_SHA256 = "bfcf8ff4b3c9dd933c6edb381a76d6bbb7abd6a1723120941d810425942e00d8"
SEALED_CONSUME_SHA256 = "09c3b86f14ea7d03888c3d99c3c70144bd30760ab247aa7274ae68075db6b92e"
SEALED_TIP = "3821941d758feb7ba05e680da6ecec283291dd2a"

FORBIDDEN_DEST_NAMES = frozenset(
    {
        "ONE_RUN.json",
        "ONE_EXEC_RESULT_t5116u.json",
        "CURSOR_ONE_EXEC_RESULT_t5116u.md",
        "DEV_RESEARCH_t5119u_R2B.json",
        "DEV_RESEARCH_t5125u_R2B2_437.json",
        "R2B_CONSUME.json",
        "ADMISSIBLE_QUOTES.jsonl",
        "COVERAGE_MANIFEST.json",
        "OWNED_COVERAGE_t5119u.json",
        "R2A_COVERAGE_MANIFEST.json",
    }
)


class MarketE2ERefuse(ValueError):
    """Fail-closed market join. Not an EVAL look. Not a claim."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _refuse_dest(path: Path) -> None:
    if path.name in FORBIDDEN_DEST_NAMES:
        raise MarketE2ERefuse(f"refusing write to preserved / R2-A file {path.name}")
    resolved = path.resolve()
    if resolved.parent.resolve() == R2A_DIR.resolve():
        raise MarketE2ERefuse("refusing rewrite of R2-A coverage directory")
    try:
        refuse_preserved_t5116u_path(path)
        refuse_overwrite_first_case_record(path)
    except OutcomeGateRefuse as exc:
        raise MarketE2ERefuse(str(exc)) from exc


def load_r2b_consume(path: Path | None = None) -> dict[str, Any]:
    dest = Path(path) if path else CONSUME_PATH
    if not dest.is_file():
        raise MarketE2ERefuse(f"R2B_CONSUME missing: {dest}")
    live = sha256_file(dest)
    if dest.resolve() == CONSUME_PATH.resolve() and live != SEALED_CONSUME_SHA256:
        raise MarketE2ERefuse("R2B_CONSUME hash mismatch vs sealed 09c3b86f")
    body = json.loads(dest.read_text(encoding="utf-8"))
    if body.get("market_e2e") != READY_FOR_R2B_DEV_E2E:
        raise MarketE2ERefuse(
            f"R2B_CONSUME.market_e2e is {body.get('market_e2e')!r} — not {READY_FOR_R2B_DEV_E2E}"
        )
    if body.get("g5_loosened") or body.get("time_rule_loosened") or body.get("book_rule_loosened"):
        raise MarketE2ERefuse("R2-A consume loosened G5/time/book — refuse")
    rules = body.get("rules") or {}
    if set(rules.get("books") or []) != set(BENCHMARK_BOOKS):
        raise MarketE2ERefuse("consume books ≠ DK/FD")
    if int(rules.get("cutoff_minutes_before_kickoff") or 0) != CUTOFF_MINUTES:
        raise MarketE2ERefuse("consume cutoff ≠ KO−60")
    if float(rules.get("max_quote_age_hours") or 0) != MAX_QUOTE_AGE_HOURS:
        raise MarketE2ERefuse("consume max age ≠ 24h")
    body["_path"] = str(dest)
    body["_file_sha256"] = live
    return body


def load_sealed_quotes(path: Path | None = None, *, expect_sha256: str | None = None) -> list[dict[str, Any]]:
    dest = Path(path) if path else QUOTES_PATH
    if not dest.is_file():
        raise MarketE2ERefuse(f"ADMISSIBLE_QUOTES missing: {dest}")
    live = sha256_file(dest)
    expect = expect_sha256 or SEALED_QUOTES_SHA256
    if dest.resolve() == QUOTES_PATH.resolve() and live != expect:
        raise MarketE2ERefuse("ADMISSIBLE_QUOTES hash mismatch vs sealed 75c0b14c")
    rows: list[dict[str, Any]] = []
    for line in dest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def load_conflicts(path: Path | None = None) -> list[dict[str, Any]]:
    dest = Path(path) if path else CONFLICTS_PATH
    if not dest.is_file():
        raise MarketE2ERefuse(f"DUPLICATE_CONFLICTS missing: {dest}")
    return json.loads(dest.read_text(encoding="utf-8"))


def load_eligible_ids(split: str = EVAL_METRIC_SPLIT) -> list[str]:
    if not COHORTS_PATH.is_file():
        raise MarketE2ERefuse(f"metric cohorts missing: {COHORTS_PATH}")
    body = json.loads(COHORTS_PATH.read_text(encoding="utf-8"))
    key = "eval" if str(split).upper() in {EVAL_METRIC_SPLIT, "EVAL"} else "dev_reg"
    cohort = body.get(key) or {}
    ids = [str(g) for g in (cohort.get("game_ids") or [])]
    if not ids:
        raise MarketE2ERefuse(f"eligible cohort {split} empty")
    return ids


def _conflict_keys(conflicts: Sequence[Mapping[str, Any]]) -> set[tuple[str, str, str, str]]:
    return {
        (
            str(row.get("game_id") or ""),
            str(row.get("book") or ""),
            str(row.get("market") or ""),
            str(row.get("captured_at") or ""),
        )
        for row in conflicts
    }


def join_market_points(
    eligible_ids: Sequence[str],
    quotes: Sequence[Mapping[str, Any]],
    *,
    conflicts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Join sealed admissible quotes onto the eligible cohort. No outcomes."""
    conflict_fp = _conflict_keys(conflicts or [])
    by_game: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for quote in quotes:
        gid = str(quote.get("game_id") or "")
        key = (
            gid,
            str(quote.get("book") or ""),
            str(quote.get("market") or ""),
            str(quote.get("captured_at") or ""),
        )
        if key in conflict_fp:
            raise MarketE2ERefuse(
                f"admissible quote collides with refused conflict {key} — fail-closed"
            )
        book = str(quote.get("book") or "")
        if book and book not in BENCHMARK_BOOKS:
            raise MarketE2ERefuse(f"non-benchmark book in admissible quotes: {book}")
        age = quote.get("age_hours")
        if age is not None and float(age) > MAX_QUOTE_AGE_HOURS:
            raise MarketE2ERefuse(
                f"admissible quote age {age} > {MAX_QUOTE_AGE_HOURS}h — time rule broken"
            )
        by_game[gid].append(quote)

    points: list[dict[str, Any]] = []
    missing: list[str] = []
    for gid in eligible_ids:
        rows = by_game.get(gid, [])
        spreads = [
            q
            for q in rows
            if str(q.get("market") or "") == "spread" and q.get("spread_home") is not None
        ]
        if not spreads:
            missing.append(gid)
            continue
        books = sorted({str(q.get("book")) for q in spreads})
        margins = [home_margin_from_handicap(float(q["spread_home"])) for q in spreads]
        points.append(
            {
                "game_id": gid,
                "season": int(spreads[0].get("season") or 0),
                "week": int(spreads[0].get("week") or 0),
                "market_margin": float(median(margins)),
                "spread_home": float(median(float(q["spread_home"]) for q in spreads)),
                "books_used": books,
                "book_count": len(books),
                "quote_n": len(spreads),
                "cutoff_minutes": CUTOFF_MINUTES,
                "max_quote_age_hours": MAX_QUOTE_AGE_HOURS,
            }
        )
    return {
        "points": points,
        "missing_game_ids": missing,
        "eligible_n": len(list(eligible_ids)),
        "joined_n": len(points),
        "missing_n": len(missing),
        "bind_ready": bool(eligible_ids) and len(missing) == 0,
    }


def _forecasts_for(ids: Sequence[str], freeze_path: Path | None = None) -> list[dict[str, Any]]:
    dest = Path(freeze_path) if freeze_path else DEFAULT_FREEZE
    freeze = json.loads(dest.read_text(encoding="utf-8"))
    want = set(ids)
    return [row for row in (freeze.get("forecasts") or []) if str(row.get("game_id")) in want]


def emit_market_contract_fields(
    join: Mapping[str, Any],
    *,
    forecasts: Sequence[Mapping[str, Any]] | None = None,
    outcomes: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Market-side EVAL contract fields for the **joined** set. Not an EVAL look."""
    out: dict[str, Any] = {
        "mae_market": None,
        "rmse_market": None,
        "bias_market": None,
        "delta_mae_vs_market": None,
        "mean_signed_diff_vs_market": None,
        "bootstrap_game_vs_market": None,
        "bootstrap_season_week_vs_market": None,
        "eval_result_contract_complete": False,
        "eval_result_contract_missing": list(EVAL_RESULT_CONTRACT_KEYS),
    }
    if not forecasts or outcomes is None or not join.get("points"):
        return out
    try:
        scored = run_paired_margin_eval(
            forecasts,
            outcomes,
            eligible_game_ids=[p["game_id"] for p in join["points"]],
            market_points=list(join["points"]),
            bootstrap_b=BOOT_B,
            bootstrap_seed=BOOT_SEED,
        )
    except EvalRefuse as exc:
        raise MarketE2ERefuse(str(exc)) from exc
    for key in (
        "mae_market",
        "rmse_market",
        "bias_market",
        "delta_mae_vs_market",
        "mean_signed_diff_vs_market",
        "bootstrap_game_vs_market",
        "bootstrap_season_week_vs_market",
        "mae_if",
        "rmse_if",
        "bias_if",
        "mae_challenger",
        "rmse_challenger",
        "bias_challenger",
        "mean_signed_diff_vs_if",
        "bootstrap_game",
        "bootstrap_season_week",
        "per_season",
        "n_by_season",
        "n",
    ):
        if key in scored:
            out[key] = scored[key]
    try:
        validate_eval_result_contract(scored)
        out["eval_result_contract_complete"] = True
        out["eval_result_contract_missing"] = []
    except Exception as exc:
        out["eval_result_contract_complete"] = False
        out["eval_result_contract_missing"] = [
            k for k in EVAL_RESULT_CONTRACT_KEYS if k not in scored or scored.get(k) is None
        ]
        out["eval_result_contract_refuse"] = str(exc)
    return out


def run_market_e2e(
    *,
    split: str = EVAL_METRIC_SPLIT,
    eligible_ids: Sequence[str] | None = None,
    outcomes: Mapping[str, Mapping[str, Any]] | None = None,
    outcome_loader: ScoringOutcomeLoader | Callable[[], Mapping[str, Mapping[str, Any]]] | None = None,
    dest: Path | None = None,
    consume_path: Path | None = None,
    quotes_path: Path | None = None,
    freeze_path: Path | None = None,
    emit_metrics: bool = True,
) -> dict[str, Any]:
    """Join sealed quotes to the eligible cohort. Stop before EVAL."""
    try:
        refuse_preloaded_scoring_outcomes(outcomes)
    except OutcomeGateRefuse as exc:
        raise MarketE2ERefuse(str(exc)) from exc
    consume = load_r2b_consume(consume_path)
    manifest = Path(consume.get("coverage_manifest") or MANIFEST_PATH)
    if not Path(manifest).is_file():
        manifest = MANIFEST_PATH
    if not Path(manifest).is_file():
        raise MarketE2ERefuse("coverage manifest missing")
    if Path(manifest).resolve() == MANIFEST_PATH.resolve():
        live_manifest = sha256_file(Path(manifest))
        if live_manifest != SEALED_MANIFEST_SHA256:
            raise MarketE2ERefuse("coverage manifest hash mismatch vs sealed bfcf8ff4")
    else:
        live_manifest = sha256_file(Path(manifest))
    quotes = load_sealed_quotes(quotes_path, expect_sha256=consume.get("admissible_quotes_sha256"))
    conflicts = load_conflicts()
    ids = list(eligible_ids) if eligible_ids is not None else load_eligible_ids(split)
    join = join_market_points(ids, quotes, conflicts=conflicts)
    forecasts = _forecasts_for([p["game_id"] for p in join["points"]], freeze_path)
    loaded: Mapping[str, Mapping[str, Any]] | None = None
    if emit_metrics and outcome_loader is not None:
        loaded = invoke_after_gates(None, outcome_loader)
    elif emit_metrics and outcome_loader is None:
        outcome_loader = None
    market_fields = emit_market_contract_fields(
        join,
        forecasts=forecasts if loaded is not None else None,
        outcomes=loaded,
    )
    record = {
        "schema_version": SCHEMA,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "eval": None,
        "scoring": None,
        "look": None,
        "exec_scoring": "REFUSED_MARKET_E2E_NOT_EVAL",
        "one_run_claim": False,
        "eval_invoked": False,
        "r2_eval_called": False,
        "g5_loosened": False,
        "time_rule_loosened": False,
        "book_rule_loosened": False,
        "r2a_tip": SEALED_TIP,
        "r2b_consume": {
            "market_e2e": consume.get("market_e2e"),
            "path": consume.get("_path"),
            "file_sha256": consume.get("_file_sha256"),
            "admissible_quotes_sha256": consume.get("admissible_quotes_sha256"),
            "coverage_manifest_sha256": live_manifest,
            "eval_r2_matched_n": consume.get("eval_r2_matched_n"),
            "dev_r2_matched_n": consume.get("dev_r2_matched_n"),
        },
        "r2a_coverage": {
            "status": consume.get("market_e2e"),
            "path": consume.get("_path"),
            "market_e2e": consume.get("market_e2e"),
            "admissible_quotes_sha256": consume.get("admissible_quotes_sha256"),
        },
        "split": split,
        "eligible_n": join["eligible_n"],
        "joined_n": join["joined_n"],
        "missing_n": join["missing_n"],
        "missing_game_ids": list(join["missing_game_ids"]),
        "bind_ready": join["bind_ready"],
        "bind_ready_reason": (
            "all eligible games have sealed market_margin"
            if join["bind_ready"]
            else (
                f"eligible {join['eligible_n']} incomplete "
                f"({join['joined_n']} joined, {join['missing_n']} missing) — not EVAL-bind ready"
            )
        ),
        "market_points": join["points"],
        "market_contract": market_fields,
        "target_join_phase": (
            "AFTER_MARKET_JOIN" if loaded is not None else "MARKET_JOIN_ONLY_NO_OUTCOMES"
        ),
        "notes": [
            "Consumed sealed R2-A ADMISSIBLE_QUOTES + manifest. Coverage files not rewritten.",
            "G5 / KO−60 / ≤24h / DK-FD unchanged. Conflicts fail-closed.",
            "EVAL was not invoked. one_run_claim=false. CERT=0.",
        ],
    }
    if dest is not None:
        dest_p = Path(dest)
        _refuse_dest(dest_p)
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        if dest_p.exists():
            raise MarketE2ERefuse(f"exclusive create refused — {dest_p.name} exists")
        dest_p.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        record["_path"] = str(dest_p)
    return record


def default_outcome_loader(game_ids: Sequence[str]) -> ScoringOutcomeLoader:
    ids = list(game_ids)

    def _load() -> dict[str, dict[str, Any]]:
        return load_dev_reg_outcomes_from_schedule(ids, DEFAULT_SCHEDULE)

    return ScoringOutcomeLoader(_load)
