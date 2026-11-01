"""t5119u R2-B DEV numerical E2E — one DEV_RESEARCH record. Not EVAL.

Pins: DEV REG 437 ``92b91585``; WC 6 ``f81d381e`` excluded.
Path: metadata eligibility freeze → first eligible DEV game (pin order) →
pinned IF + fixed 0.5/0.5 candidate → market join if available → numerical
error. Target scoring outcomes load only after that freeze+pick.

No fit, no candidate selection, no probability invention, no EVAL feedback,
no one-run claim. Missing market is labeled MISSING. CERT=0.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .builder import CHALLENGER_WEIGHT, challenger_margin
from .evaluator import (
    EvalRefuse,
    home_margin_from_handicap,
    select_market_quotes,
    signed_abs_loss,
)
from .metric_cohorts import WILDCARD_2020_W18, cohort_sha256, pin_metric_cohorts
from .outcome_gate import (
    OutcomeGateRefuse,
    ScoringOutcomeLoader,
    invoke_after_gates,
    refuse_both_preload_and_loader,
    refuse_preserved_t5116u_path,
)
from .q2 import T5107U_DEV_SEASONS

SCHEMA = "nfl-t5119u-dev-research-v1"
LABEL = "DEV_RESEARCH"
CERT_CANDIDATE = 0
DEV_REG_N = 437
DEV_REG_SHA256 = "92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49"
NON_REG_WILDCARD_N = 6
NON_REG_WILDCARD_SHA256 = "f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722"
SELECTION_RULE = "first_eligible_after_metadata_freeze_dev_reg_pin_order"
HALF = CHALLENGER_WEIGHT  # frozen 0.5; no weight search

METADATA_FIELDS = (
    "game_id",
    "season",
    "week",
    "season_type",
    "home",
    "away",
    "kickoff_utc",
    "m_if",
    "m_q2",
    "m_challenger",
)

OUTPUT_CONTRACT = (
    "schema_version",
    "label",
    "cert_candidate",
    "eval",
    "scoring",
    "look",
    "exec_scoring",
    "one_run_claim",
    "dev_reg_n",
    "dev_reg_sha256",
    "wildcard_n",
    "wildcard_sha256",
    "wildcard_excluded",
    "selection_rule",
    "game_id",
    "input",
    "if_pinned",
    "candidate",
    "market",
    "outcome",
    "numerical_error",
    "r2a_coverage",
    "target_join_phase",
    "notes",
    "record_sha256",
)

_PKG_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_FREEZE = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"
DEFAULT_SCHEDULE = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2020_2023.csv"
DEFAULT_RECORD = _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5119u_R2B.json"
R2A_COVERAGE_CANDIDATES = (
    _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u/OWNED_COVERAGE_t5119u.json",
    _PKG_ROOT / "data/ops/nfl-forecast-builder-t5107u/R2A_COVERAGE_MANIFEST.json",
)


class DevResearchRefuse(ValueError):
    """Fail-closed DEV_RESEARCH diagnostic. Never an EVAL look."""


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def kickoff_has_tz_contract(kickoff: Any) -> bool:
    text = str(kickoff or "").strip()
    if not text:
        return False
    if text.endswith("Z") or text.endswith("z"):
        return True
    if len(text) >= 20 and ("+" in text[10:] or text[-6:-5] == "-"):
        return True
    return False


def metadata_eligibility(row: Mapping[str, Any]) -> dict[str, Any]:
    """Identity / kickoff / pinned-margin metadata only. No outcomes. No quotes."""
    missing = [name for name in METADATA_FIELDS if row.get(name) in (None, "")]
    gid = str(row.get("game_id") or "")
    season = int(row.get("season") or 0)
    reasons: list[str] = []
    if missing:
        reasons.append("missing_metadata:" + ",".join(missing))
    if season not in T5107U_DEV_SEASONS:
        reasons.append("not_dev_season")
    if str(row.get("season_type") or "").upper() != "REG":
        reasons.append("not_reg")
    if gid in set(WILDCARD_2020_W18):
        reasons.append("non_reg_wildcard")
    if not kickoff_has_tz_contract(row.get("kickoff_utc")):
        reasons.append("kickoff_tz_undocumented")
    if not all(_finite(row.get(k)) for k in ("m_if", "m_q2", "m_challenger")):
        reasons.append("nonfinite_or_missing_margin")
    eligible = not reasons
    return {
        "game_id": gid,
        "eligible": eligible,
        "reasons": reasons,
        "phase": "SOURCE_READ",
    }


def freeze_dev_metadata_eligibility(
    forecasts: Sequence[Mapping[str, Any]],
    *,
    require_dev_reg_pin: bool = True,
) -> dict[str, Any]:
    """Seal DEV REG metadata eligibility before any target outcome load."""
    if require_dev_reg_pin:
        pins = pin_metric_cohorts(forecasts)
        if pins["dev_reg"]["n"] != DEV_REG_N:
            raise DevResearchRefuse(f"DEV REG n {pins['dev_reg']['n']} != {DEV_REG_N}")
        if pins["dev_reg"]["cohort_sha256"] != DEV_REG_SHA256:
            raise DevResearchRefuse("DEV REG pin mismatch vs 92b91585")
        if pins["non_reg_wildcard"]["n"] != NON_REG_WILDCARD_N:
            raise DevResearchRefuse("NON_REG_WILDCARD n mismatch vs 6")
        if pins["non_reg_wildcard"]["cohort_sha256"] != NON_REG_WILDCARD_SHA256:
            raise DevResearchRefuse("NON_REG_WILDCARD pin mismatch vs f81d381e")
    else:
        # Synthetic fixtures: preserve caller order; still drop WC 6.
        dev_reg_ids = [
            str(r["game_id"])
            for r in forecasts
            if int(r.get("season") or 0) in T5107U_DEV_SEASONS
            and str(r["game_id"]) not in set(WILDCARD_2020_W18)
        ]
        wc_ids = [str(r["game_id"]) for r in forecasts if str(r["game_id"]) in set(WILDCARD_2020_W18)]
        pins = {
            "dev_reg": {
                "n": len(dev_reg_ids),
                "game_ids": dev_reg_ids,
                "cohort_sha256": cohort_sha256(dev_reg_ids),
            },
            "non_reg_wildcard": {
                "n": len(wc_ids),
                "cohort_sha256": cohort_sha256(wc_ids),
            },
        }
    by_id = {str(r["game_id"]): dict(r) for r in forecasts}
    rows = []
    for gid in pins["dev_reg"]["game_ids"]:
        row = by_id.get(gid)
        if row is None:
            rows.append({"game_id": gid, "eligible": False, "reasons": ["missing_from_forecasts"]})
            continue
        rows.append(metadata_eligibility(row))
    eligible_ids = [r["game_id"] for r in rows if r["eligible"]]
    body = {
        "schema_version": "nfl-t5119u-dev-metadata-eligibility-v1",
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "dev_reg_n": pins["dev_reg"]["n"],
        "dev_reg_sha256": pins["dev_reg"]["cohort_sha256"],
        "wildcard_n": pins["non_reg_wildcard"]["n"],
        "wildcard_sha256": pins["non_reg_wildcard"]["cohort_sha256"],
        "wildcard_excluded": True,
        "eligible_game_ids": eligible_ids,
        "eligible_n": len(eligible_ids),
        "rows": rows,
        "sealed_before_outcome_join": True,
        "phase": "SOURCE_READ",
        "eval": None,
        "scoring": None,
    }
    body["eligibility_sha256"] = hashlib.sha256(
        json.dumps(
            {"eligible_game_ids": eligible_ids, "dev_reg_sha256": body["dev_reg_sha256"]},
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return body


def first_eligible_dev_game(
    eligibility: Mapping[str, Any],
    forecasts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Deterministic: first metadata-eligible id in frozen DEV REG pin order."""
    if not eligibility.get("sealed_before_outcome_join"):
        raise DevResearchRefuse("metadata eligibility was not sealed before pick")
    ids = list(eligibility.get("eligible_game_ids") or [])
    if not ids:
        raise DevResearchRefuse("no metadata-eligible DEV REG game")
    gid = ids[0]
    if gid in set(WILDCARD_2020_W18):
        raise DevResearchRefuse("selection landed on excluded NON_REG_WILDCARD")
    row = next((dict(r) for r in forecasts if str(r.get("game_id")) == gid), None)
    if row is None:
        raise DevResearchRefuse(f"selected {gid} missing from forecasts")
    return row


def fixed_half_half_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute 0.5/0.5. Refuse extra HFA / blend / weight search / invention."""
    recomputed = challenger_margin(row["m_if"], row["m_q2"], w=HALF, extra_hfa=0.0, market_blend=0.0)
    pinned = float(row["m_challenger"])
    if not math.isclose(recomputed, pinned, rel_tol=0.0, abs_tol=1e-9):
        raise DevResearchRefuse(
            f"pinned m_challenger {pinned} != fixed 0.5/0.5 recomputed {recomputed}"
        )
    return {
        "weight_if": HALF,
        "weight_q2": HALF,
        "m_if": float(row["m_if"]),
        "m_q2": float(row["m_q2"]),
        "m_challenger": pinned,
        "m_challenger_recomputed": recomputed,
        "match": True,
        "extra_hfa": 0.0,
        "market_blend": 0.0,
        "fit": False,
        "selection": False,
        "probability_invented": False,
    }


def join_market_if_available(
    row: Mapping[str, Any],
    quotes: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """SOURCE READ. Honest MISSING when quotes/coverage are absent."""
    if not quotes:
        return {
            "status": "MISSING",
            "market_margin": None,
            "spread_home": None,
            "p_home_fair": None,
            "p_compare": "unavailable",
            "books_used": [],
            "book_count": 0,
            "reason": "no_admissible_quotes_supplied",
        }
    game = {
        "game_id": row["game_id"],
        "event_id": str(row.get("event_id") or row["game_id"]),
        "season": int(row["season"]),
        "week": int(row["week"]),
        "home": row["home"],
        "away": row["away"],
        "home_team": row["home"],
        "away_team": row["away"],
        "game_date": str(row.get("game_date") or str(row.get("kickoff_utc") or "")[:10]),
        "kickoff": row["kickoff_utc"],
        "kickoff_utc": row["kickoff_utc"],
    }
    try:
        market = select_market_quotes(quotes, [game], forecasts=[row])
    except EvalRefuse as exc:
        return {
            "status": "MISSING",
            "market_margin": None,
            "spread_home": None,
            "p_home_fair": None,
            "p_compare": "unavailable",
            "books_used": [],
            "book_count": 0,
            "reason": f"market_join_refused:{exc}",
        }
    points = list(market.get("points") or [])
    point = points[0] if points else {}
    margin = point.get("market_margin")
    if margin is None:
        return {
            "status": "MISSING",
            "market_margin": None,
            "spread_home": point.get("spread_home"),
            "p_home_fair": point.get("p_home_fair"),
            "p_compare": point.get("p_compare") or "unavailable",
            "books_used": list(point.get("books_used") or []),
            "book_count": int(point.get("book_count") or 0),
            "reason": "no_eligible_dk_fd_spread_at_ko_minus_60",
            "excluded": list(market.get("excluded") or []),
        }
    return {
        "status": "JOINED",
        "market_margin": float(margin),
        "spread_home": point.get("spread_home"),
        "p_home_fair": point.get("p_home_fair"),
        "p_compare": point.get("p_compare") or "unavailable",
        "books_used": list(point.get("books_used") or []),
        "book_count": int(point.get("book_count") or 0),
        "reason": "admissible_dk_fd_median_home_margin",
        "home_margin_from_handicap": home_margin_from_handicap(point["spread_home"])
        if point.get("spread_home") is not None
        else float(margin),
    }


def numerical_error(
    candidate: Mapping[str, Any],
    outcome: Mapping[str, Any],
    market: Mapping[str, Any],
) -> dict[str, Any]:
    if str(outcome.get("status") or "") != "JOINED":
        return {
            "status": "MISSING",
            "err_challenger": None,
            "err_if": None,
            "L_challenger": None,
            "L_if": None,
            "signed_diff_vs_if": None,
            "err_market": None,
            "L_market": None,
            "signed_diff_vs_market": None,
            "actual_margin": None,
            "market_status": market.get("status"),
            "reason": str(outcome.get("reason") or "outcome_not_joined"),
        }
    actual = float(outcome["actual_margin"])
    m_c = float(candidate["m_challenger"])
    m_if = float(candidate["m_if"])
    err_c = m_c - actual
    err_if = m_if - actual
    out: dict[str, Any] = {
        "status": "COMPUTED",
        "actual_margin": actual,
        "err_challenger": err_c,
        "err_if": err_if,
        "L_challenger": signed_abs_loss(m_c, actual),
        "L_if": signed_abs_loss(m_if, actual),
        "signed_diff_vs_if": signed_abs_loss(m_c, actual) - signed_abs_loss(m_if, actual),
        "err_market": None,
        "L_market": None,
        "signed_diff_vs_market": None,
        "market_status": market.get("status"),
    }
    if market.get("status") == "JOINED" and market.get("market_margin") is not None:
        m_mkt = float(market["market_margin"])
        out["err_market"] = m_mkt - actual
        out["L_market"] = signed_abs_loss(m_mkt, actual)
        out["signed_diff_vs_market"] = out["L_challenger"] - out["L_market"]
    else:
        out["reason"] = str(market.get("reason") or "market_MISSING")
    return out


def r2a_coverage_status(explicit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if explicit:
        return dict(explicit)
    for path in R2A_COVERAGE_CANDIDATES:
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            return {
                "status": "present",
                "path": str(path),
                "pins": payload.get("pins") or payload.get("coverage_pins") or {},
            }
    return {
        "status": "not_ready",
        "path": None,
        "pins": None,
        "reason": "R2-A coverage manifest not present; existing admissible quotes only",
    }


def validate_dev_research_record(record: Mapping[str, Any]) -> None:
    missing = [k for k in OUTPUT_CONTRACT if k not in record]
    if missing:
        raise DevResearchRefuse(f"DEV_RESEARCH output contract incomplete: {missing}")
    if record.get("label") != LABEL:
        raise DevResearchRefuse("label must be DEV_RESEARCH")
    if record.get("eval") is not None:
        raise DevResearchRefuse("DEV_RESEARCH must not carry eval")
    if record.get("one_run_claim") is not False:
        raise DevResearchRefuse("DEV_RESEARCH must not claim a one-run")
    if record.get("cert_candidate") != 0:
        raise DevResearchRefuse("CERT must be 0")
    if record.get("dev_reg_n") != DEV_REG_N and record.get("synthetic") is not True:
        raise DevResearchRefuse("DEV REG n pin 437 required on non-synthetic records")


def _record_body(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body.pop("record_sha256", None)
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    body["record_sha256"] = digest
    return body


def run_dev_research_e2e(
    forecasts: Sequence[Mapping[str, Any]],
    *,
    quotes: Sequence[Mapping[str, Any]] | None = None,
    outcomes: Mapping[str, Mapping[str, Any]] | None = None,
    outcome_loader: ScoringOutcomeLoader | Callable[[], Mapping[str, Mapping[str, Any]]] | None = None,
    require_dev_reg_pin: bool = True,
    r2a_coverage: Mapping[str, Any] | None = None,
    dest: Path | None = None,
    synthetic: bool = False,
) -> dict[str, Any]:
    """One DEV_RESEARCH diagnostic. Outcome loader runs after freeze+pick only."""
    try:
        refuse_both_preload_and_loader(outcomes, outcome_loader)
    except OutcomeGateRefuse as exc:
        raise DevResearchRefuse(str(exc)) from exc
    eligibility = freeze_dev_metadata_eligibility(
        forecasts, require_dev_reg_pin=require_dev_reg_pin
    )
    row = first_eligible_dev_game(eligibility, forecasts)
    candidate = fixed_half_half_candidate(row)
    market = join_market_if_available(row, quotes)
    try:
        loaded = invoke_after_gates(outcomes, outcome_loader)
    except OutcomeGateRefuse as exc:
        raise DevResearchRefuse(str(exc)) from exc
    gid = str(row["game_id"])
    raw = (loaded or {}).get(gid)
    if not raw:
        outcome = {
            "status": "MISSING",
            "game_id": gid,
            "home_score": None,
            "away_score": None,
            "actual_margin": None,
            "reason": "selected_game_absent_from_target_loader",
        }
    else:
        hs, aws = raw.get("home_score"), raw.get("away_score")
        if hs in (None, "") or aws in (None, ""):
            outcome = {
                "status": "MISSING",
                "game_id": gid,
                "home_score": hs,
                "away_score": aws,
                "actual_margin": None,
                "reason": "scores_missing",
            }
        else:
            outcome = {
                "status": "JOINED",
                "game_id": gid,
                "season": int(raw.get("season") or row["season"]),
                "week": int(raw.get("week") or row["week"]),
                "home_score": float(hs),
                "away_score": float(aws),
                "actual_margin": float(hs) - float(aws),
                "reason": "target_join_after_metadata_freeze_and_pick",
            }
    error = numerical_error(candidate, outcome, market)
    record = _record_body(
        {
            "schema_version": SCHEMA,
            "label": LABEL,
            "cert_candidate": CERT_CANDIDATE,
            "eval": None,
            "scoring": None,
            "look": None,
            "exec_scoring": "REFUSED_DEV_RESEARCH_NOT_EVAL",
            "one_run_claim": False,
            "synthetic": synthetic,
            "dev_reg_n": eligibility["dev_reg_n"],
            "dev_reg_sha256": eligibility["dev_reg_sha256"],
            "wildcard_n": eligibility["wildcard_n"],
            "wildcard_sha256": eligibility["wildcard_sha256"],
            "wildcard_excluded": True,
            "selection_rule": SELECTION_RULE,
            "eligibility_sha256": eligibility["eligibility_sha256"],
            "eligible_n": eligibility["eligible_n"],
            "game_id": gid,
            "input": {k: row.get(k) for k in METADATA_FIELDS},
            "if_pinned": {
                "m_if": float(row["m_if"]),
                "if_status": row.get("if_status"),
                "if_label": row.get("if_label"),
                "source": "forecast_freeze_pin",
            },
            "candidate": candidate,
            "market": market,
            "outcome": outcome,
            "numerical_error": error,
            "r2a_coverage": r2a_coverage_status(r2a_coverage),
            "target_join_phase": "AFTER_METADATA_ELIGIBILITY_AND_PICK",
            "notes": [
                "SOURCE READ (forecasts/quotes/metadata) ≠ TARGET JOIN (scoring outcomes).",
                "t5116u loaded EVAL outcomes to memory pre-HOLD; R2 path does not.",
                "Fixed 0.5/0.5 candidate. No fit, no selection, no invented probabilities.",
                "Missing market labeled honestly. No EVAL EXEC. No one-run claim. CERT=0.",
                f"DEV REG pin 437/{DEV_REG_SHA256[:8]}; WC 6 excluded.",
            ],
        }
    )
    validate_dev_research_record(record)
    if dest is not None:
        write_dev_research_record(record, dest)
    return record


def write_dev_research_record(record: Mapping[str, Any], dest: Path) -> Path:
    refuse_preserved_t5116u_path(dest)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, indent=2, default=str) + "\n"
    flags = __import__("os").O_CREAT | __import__("os").O_EXCL | __import__("os").O_WRONLY
    try:
        fd = __import__("os").open(str(dest), flags, 0o644)
    except FileExistsError as exc:
        raise DevResearchRefuse(
            f"DEV_RESEARCH exclusive create refused — {dest.name} exists"
        ) from exc
    try:
        with __import__("os").fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        try:
            dest.unlink()
        except OSError:
            pass
        raise
    return dest


def load_single_game_outcome_from_schedule(
    game_id: str,
    schedule_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """TARGET JOIN helper: one selected DEV game from the prepared schedule."""
    path = Path(schedule_path) if schedule_path else DEFAULT_SCHEDULE
    if not path.is_file():
        raise DevResearchRefuse(f"schedule outcomes missing: {path}")
    with path.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            if str(raw.get("game_id")) != game_id:
                continue
            if str(raw.get("season_type") or "REG").upper() != "REG":
                continue
            return {
                game_id: {
                    "game_id": game_id,
                    "season": int(raw["season"]),
                    "week": int(raw["week"]),
                    "home_score": raw.get("home_score"),
                    "away_score": raw.get("away_score"),
                }
            }
    return {}


def materialize_pinned_dev_research(
    *,
    freeze_path: Path | None = None,
    schedule_path: Path | None = None,
    dest: Path | None = None,
    quotes: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the one authorized DEV_RESEARCH record from pinned freeze + schedule."""
    freeze_p = Path(freeze_path) if freeze_path else DEFAULT_FREEZE
    dest_p = Path(dest) if dest else DEFAULT_RECORD
    refuse_preserved_t5116u_path(dest_p)
    freeze = json.loads(freeze_p.read_text(encoding="utf-8"))
    forecasts = list(freeze.get("forecasts") or [])
    eligibility = freeze_dev_metadata_eligibility(forecasts, require_dev_reg_pin=True)
    row = first_eligible_dev_game(eligibility, forecasts)
    gid = str(row["game_id"])

    def _load() -> dict[str, dict[str, Any]]:
        return load_single_game_outcome_from_schedule(gid, schedule_path)

    loader = ScoringOutcomeLoader(_load)
    return run_dev_research_e2e(
        forecasts,
        quotes=quotes,
        outcome_loader=loader,
        require_dev_reg_pin=True,
        dest=dest_p,
        synthetic=False,
    )


def pinned_dev_reg_sha256(forecasts: Sequence[Mapping[str, Any]]) -> str:
    return cohort_sha256(
        [str(r["game_id"]) for r in forecasts if str(r["game_id"]) not in set(WILDCARD_2020_W18)
         and int(r.get("season") or 0) in T5107U_DEV_SEASONS]
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
