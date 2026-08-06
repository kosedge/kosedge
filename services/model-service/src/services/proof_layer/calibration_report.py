"""Historical calibration reports from the unified proof-layer JSONL lake.

Reproducible backtest-style summaries: ATS / O/U / SU record, average error,
CLV, and bias slices (favorite/dog, home/away pick, early season).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.proof_layer.core import (
    LAKE_DIR,
    ProjectionLog,
    _record_rate,
    performance_summary,
)
from src.services.proof_layer.proof_lake import ProofLakeError, get_lake

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORT_DIR = _SERVICE_ROOT / "data" / "ops" / "calibration_reports"

THIN_SAMPLE_THRESHOLD = 30
ADEQUATE_SAMPLE_THRESHOLD = 100


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _in_date_range(
    projected_at: Optional[str],
    *,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> bool:
    ts = _parse_ts(projected_at)
    if ts is None:
        return from_ts is None and to_ts is None
    start = _parse_ts(from_ts)
    end = _parse_ts(to_ts)
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True


def load_filtered_projections(
    *,
    sport: Optional[str] = None,
    engine_version: Optional[str] = None,
    season: Optional[int] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> List[ProjectionLog]:
    """Load all lake rows matching sport / version / season / projected_at window."""
    rows = get_lake(lake_dir=lake_dir).list_records(
        sport=sport,
        engine_version=engine_version,
        season=season,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=5000,
    )
    rows.sort(key=lambda r: (r.projected_at or "", r.game_key or ""))
    return rows


def _grade_is_win(grade: Optional[str]) -> bool:
    if not grade:
        return False
    return grade == "win" or str(grade).endswith("_win")


def _grade_is_loss(grade: Optional[str]) -> bool:
    if not grade:
        return False
    return grade == "loss" or str(grade).endswith("_loss")


def _grade_is_push(grade: Optional[str]) -> bool:
    return grade == "push"


def _normalize_ats_grade(grade: Optional[str]) -> Optional[str]:
    if grade is None:
        return None
    if grade in {"win", "loss", "push"}:
        return grade
    if grade.startswith("home_"):
        tail = grade[5:]
        if tail in {"win", "loss", "push"}:
            return tail
    if grade.startswith("neutral_"):
        return None
    return None


def _model_ats_pick(record: ProjectionLog) -> Optional[str]:
    """Return ``home`` or ``away`` for the model's ATS side, if any."""
    close_spread = record.close_spread_home
    model_spread = record.model_spread_home
    ats_line = close_spread if close_spread is not None else model_spread
    if ats_line is None or model_spread is None:
        return None
    model_home_edge = float(ats_line) - float(model_spread)
    if abs(model_home_edge) < 0.5:
        return None
    return "home" if model_home_edge > 0 else "away"


def _spread_sign_bucket(model_spread_home: Optional[float]) -> Optional[str]:
    if model_spread_home is None:
        return None
    if model_spread_home < -0.01:
        return "home_favorite"
    if model_spread_home > 0.01:
        return "home_dog"
    return "pick_em"


def _slice_metrics(records: Sequence[ProjectionLog]) -> Dict[str, Any]:
    with_result = [r for r in records if r.home_score is not None and r.away_score is not None]
    with_close = [
        r for r in records if r.close_spread_home is not None or r.close_total is not None
    ]
    spread_clvs = [r.spread_clv for r in records if r.spread_clv is not None]
    total_clvs = [r.total_clv for r in records if r.total_clv is not None]

    spread_errors: List[float] = []
    total_errors: List[float] = []
    margin_errors: List[float] = []
    for r in with_result:
        actual_margin = float(r.home_score) - float(r.away_score)  # type: ignore[arg-type]
        actual_total = float(r.home_score) + float(r.away_score)  # type: ignore[arg-type]
        if r.model_spread_home is not None:
            model_margin = -float(r.model_spread_home)
            err = abs(model_margin - actual_margin)
            spread_errors.append(err)
            margin_errors.append(model_margin - actual_margin)
        if r.model_total is not None:
            total_errors.append(abs(float(r.model_total) - actual_total))

    ats_grades = [_normalize_ats_grade(r.grade_ats) for r in with_result]
    ou_grades = [r.grade_ou for r in with_result if r.grade_ou]
    su_grades = [r.grade_su for r in with_result if r.grade_su]

    avg_margin_bias = (
        round(sum(margin_errors) / len(margin_errors), 3) if margin_errors else None
    )

    return {
        "n_logged": len(records),
        "n_with_close": len(with_close),
        "n_with_result": len(with_result),
        "ats": _record_rate(ats_grades),
        "ou": _record_rate(ou_grades),
        "su": _record_rate(su_grades),
        "clv": {
            "n_spread": len(spread_clvs),
            "avg_spread_clv": round(sum(spread_clvs) / len(spread_clvs), 4)
            if spread_clvs
            else None,
            "spread_clv_positive_rate": round(
                sum(1 for c in spread_clvs if c > 0) / len(spread_clvs), 4
            )
            if spread_clvs
            else None,
            "n_total": len(total_clvs),
            "avg_total_clv": round(sum(total_clvs) / len(total_clvs), 4)
            if total_clvs
            else None,
        },
        "avg_error": {
            "avg_abs_margin_error": round(sum(spread_errors) / len(spread_errors), 3)
            if spread_errors
            else None,
            "avg_abs_total_error": round(sum(total_errors) / len(total_errors), 3)
            if total_errors
            else None,
            "avg_margin_bias": avg_margin_bias,
            "n_margin": len(spread_errors),
            "n_total": len(total_errors),
        },
    }


def _bias_slices(records: Sequence[ProjectionLog]) -> Dict[str, Any]:
    buckets: Dict[str, List[ProjectionLog]] = {
        "home_favorite": [],
        "home_dog": [],
        "pick_em": [],
        "model_pick_home": [],
        "model_pick_away": [],
        "early_season_week_le_4": [],
        "mid_late_season_week_gt_4": [],
    }
    for r in records:
        sign = _spread_sign_bucket(r.model_spread_home)
        if sign == "home_favorite":
            buckets["home_favorite"].append(r)
        elif sign == "home_dog":
            buckets["home_dog"].append(r)
        elif sign == "pick_em":
            buckets["pick_em"].append(r)

        pick = _model_ats_pick(r)
        if pick == "home":
            buckets["model_pick_home"].append(r)
        elif pick == "away":
            buckets["model_pick_away"].append(r)

        if int(r.week or 0) <= 4:
            buckets["early_season_week_le_4"].append(r)
        else:
            buckets["mid_late_season_week_gt_4"].append(r)

    out: Dict[str, Any] = {}
    for name, subset in buckets.items():
        metrics = _slice_metrics(subset)
        metrics["thin_sample"] = metrics["n_with_result"] < THIN_SAMPLE_THRESHOLD
        out[name] = metrics
    return out


def _honesty_flags(metrics: Mapping[str, Any]) -> List[str]:
    flags: List[str] = []
    n_result = int(metrics.get("n_with_result") or 0)
    n_close = int(metrics.get("n_with_close") or 0)
    n_logged = int(metrics.get("n_logged") or 0)

    if n_logged == 0:
        flags.append("no_projections")
    if n_result < THIN_SAMPLE_THRESHOLD:
        flags.append("thin_sample")
    elif n_result < ADEQUATE_SAMPLE_THRESHOLD:
        flags.append("moderate_sample")
    if n_close == 0 and n_logged > 0:
        flags.append("no_closes")
    elif n_close < THIN_SAMPLE_THRESHOLD and n_logged >= THIN_SAMPLE_THRESHOLD:
        flags.append("thin_close_sample")

    clv = metrics.get("clv") or {}
    if int(clv.get("n_spread") or 0) == 0 and n_close > 0:
        flags.append("clv_spread_unavailable")
    if int(clv.get("n_spread") or 0) > 0 and int(clv.get("n_spread") or 0) < THIN_SAMPLE_THRESHOLD:
        flags.append("thin_clv_sample")

    avg_err = metrics.get("avg_error") or {}
    bias = avg_err.get("avg_margin_bias")
    if bias is not None and abs(float(bias)) >= 2.0 and n_result >= 10:
        flags.append("margin_bias_detected")

    return flags


def _summary_lines(
    *,
    sport: str,
    metrics: Mapping[str, Any],
    bias: Mapping[str, Any],
    honesty: Sequence[str],
    filters: Mapping[str, Any],
) -> str:
    lines: List[str] = []
    title_sport = sport.upper()
    lines.append(f"# Historical Calibration — {title_sport}")
    lines.append("")
    lines.append("## Filters")
    for key, val in filters.items():
        if val is not None:
            lines.append(f"- **{key}**: {val}")
    lines.append("")

    n_result = int(metrics.get("n_with_result") or 0)
    n_logged = int(metrics.get("n_logged") or 0)
    lines.append("## Sample")
    lines.append(
        f"- Logged: **{n_logged}** | With close: **{metrics.get('n_with_close', 0)}** | "
        f"With result: **{n_result}**"
    )
    if "thin_sample" in honesty:
        lines.append(
            f"- ⚠️ **Thin sample** (n_with_result < {THIN_SAMPLE_THRESHOLD}) — treat metrics as directional only."
        )
    if "no_closes" in honesty:
        lines.append("- ⚠️ **No closes captured** — CLV unavailable.")
    lines.append("")

    ats = metrics.get("ats") or {}
    ou = metrics.get("ou") or {}
    su = metrics.get("su") or {}
    lines.append("## Record (graded projections)")
    if n_result == 0:
        lines.append("- No graded games yet.")
    else:
        lines.append(
            f"- **ATS**: {ats.get('record', 'n/a')} "
            f"({ats.get('win_pct') if ats.get('win_pct') is not None else 'n/a'} win rate, n={ats.get('n', 0)})"
        )
        lines.append(
            f"- **O/U**: {ou.get('record', 'n/a')} "
            f"(n={ou.get('n', 0)})"
        )
        lines.append(
            f"- **SU**: {su.get('record', 'n/a')} "
            f"(n={su.get('n', 0)})"
        )
    lines.append("")

    avg_err = metrics.get("avg_error") or {}
    lines.append("## Average error")
    lines.append(
        f"- Margin MAE: **{avg_err.get('avg_abs_margin_error', 'n/a')}** "
        f"(bias {avg_err.get('avg_margin_bias', 'n/a')}, n={avg_err.get('n_margin', 0)})"
    )
    lines.append(
        f"- Total MAE: **{avg_err.get('avg_abs_total_error', 'n/a')}** "
        f"(n={avg_err.get('n_total', 0)})"
    )
    lines.append("")

    clv = metrics.get("clv") or {}
    lines.append("## CLV (requires closes)")
    if int(clv.get("n_spread") or 0) == 0:
        lines.append("- Spread CLV: not enough close lines.")
    else:
        lines.append(
            f"- Spread CLV avg: **{clv.get('avg_spread_clv')}** "
            f"(positive rate {clv.get('spread_clv_positive_rate')}, n={clv.get('n_spread')})"
        )
    if int(clv.get("n_total") or 0) == 0:
        lines.append("- Total CLV: not enough close totals.")
    else:
        lines.append(
            f"- Total CLV avg: **{clv.get('avg_total_clv')}** (n={clv.get('n_total')})"
        )
    lines.append("")

    lines.append("## Bias slices (honest caveats per slice)")
    slice_labels = {
        "home_favorite": "Home favorite (model_spread_home < 0)",
        "home_dog": "Home dog (model_spread_home > 0)",
        "model_pick_home": "Model ATS pick: home",
        "model_pick_away": "Model ATS pick: away",
        "early_season_week_le_4": "Early season (week ≤ 4)",
        "mid_late_season_week_gt_4": "Mid/late season (week > 4)",
    }
    for key, label in slice_labels.items():
        sl = bias.get(key) or {}
        nr = int(sl.get("n_with_result") or 0)
        if nr == 0:
            lines.append(f"- **{label}**: no graded games")
            continue
        ats_s = sl.get("ats") or {}
        caveat = " ⚠️ thin" if sl.get("thin_sample") else ""
        lines.append(
            f"- **{label}**: ATS {ats_s.get('record', 'n/a')} "
            f"(n={nr}){caveat}"
        )
    lines.append("")
    lines.append("---")
    lines.append(
        "*Generated from unified proof lake (Postgres or JSONL). Closes are never invented.*"
    )
    return "\n".join(lines)


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-") or "unknown"


def build_calibration_report(
    *,
    sport: str,
    engine_version: Optional[str] = None,
    season: Optional[int] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build structured calibration report + markdown summary."""
    sport_l = sport.strip().lower()
    try:
        rows = load_filtered_projections(
            sport=sport_l,
            engine_version=engine_version,
            season=season,
            from_ts=from_ts,
            to_ts=to_ts,
            lake_dir=lake_dir,
        )
    except ProofLakeError as exc:
        return {
            "ok": False,
            "error": f"proof lake unavailable: {exc}",
            "report_type": "historical_calibration",
        }
    metrics = _slice_metrics(rows)
    bias = _bias_slices(rows)
    honesty = _honesty_flags(metrics)

    versions = sorted({r.engine_version for r in rows})
    seasons = sorted({int(r.season) for r in rows if r.season})
    projected_range: Dict[str, Optional[str]] = {"from": None, "to": None}
    if rows:
        projected_range["from"] = rows[0].projected_at
        projected_range["to"] = rows[-1].projected_at

    filters = {
        "sport": sport_l,
        "engine_version": engine_version,
        "season": season,
        "from": from_ts,
        "to": to_ts,
    }

    summary_text = _summary_lines(
        sport=sport_l,
        metrics=metrics,
        bias=bias,
        honesty=honesty,
        filters=filters,
    )

    parity: Optional[Dict[str, Any]] = None
    if season is None and from_ts is None and to_ts is None:
        perf = performance_summary(
            sport=sport_l,
            engine_version=engine_version,
            limit=max(len(rows), 500),
            lake_dir=lake_dir,
        )
        parity = {
            "n_logged": perf.get("n_logged"),
            "n_with_close": perf.get("n_with_close"),
            "n_with_result": perf.get("n_with_result"),
            "note": "performance_summary uses limit cap; report uses full filtered lake",
        }

    return {
        "ok": True,
        "report_type": "historical_calibration",
        "generated_at": _utc_now(),
        "filters": filters,
        "inputs": {
            "lake_dir": str(lake_dir or get_lake(lake_dir=lake_dir).location),
            "backend": get_lake(lake_dir=lake_dir).backend_name,
            "projected_at_range": projected_range,
            "engine_versions_seen": versions,
            "seasons_seen": seasons,
        },
        "honesty_flags": honesty,
        "metrics": metrics,
        "bias_slices": bias,
        "summary_text": summary_text,
        "performance_summary_parity": parity,
    }


def write_report_artifact(
    report: Mapping[str, Any],
    *,
    report_dir: Optional[Path] = None,
) -> Path:
    """Persist JSON report under data/ops/calibration_reports/."""
    out_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    filters = report.get("filters") or {}
    sport = _slug(str(filters.get("sport") or "all"))
    engine = _slug(str(filters.get("engine_version") or "all-versions"))
    ts = str(report.get("generated_at") or _utc_now()).replace(":", "").replace("-", "")
    filename = f"{sport}_{engine}_{ts}.json"
    path = out_dir / filename
    path.write_text(json.dumps(dict(report), indent=2, default=str), encoding="utf-8")
    return path


def generate_calibration_report(
    *,
    sport: str,
    engine_version: Optional[str] = None,
    season: Optional[int] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    lake_dir: Optional[Path] = None,
    write_artifact: bool = False,
    report_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    report = build_calibration_report(
        sport=sport,
        engine_version=engine_version,
        season=season,
        from_ts=from_ts,
        to_ts=to_ts,
        lake_dir=lake_dir,
    )
    if write_artifact:
        artifact_path = write_report_artifact(report, report_dir=report_dir)
        report["artifact_path"] = str(artifact_path)
    return report
