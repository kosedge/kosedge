"""2026 live open diagnostic — research fair vs owned opens. Report only.

Does not blend. Does not write KEI. ``used_in_spread`` stays false.
Closes are out of scope (n_closes=0). No hist backfill.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.cfb_warehouse.market_diagnostic import conference_tier
from src.services.cfb_warehouse.odds_lake import PREFER_BOOKS
from src.services.cfb_warehouse.walkforward import _f, wilson_interval

USED_IN_SPREAD = False
DIAGNOSTIC_ID = "cfb-live-open-diagnostic-v0.15.1-20260815"
SLICE_MIN_N = 15
PRIOR_DESIGN_MIN_N = 25
PICKEM_EPS = 0.5
HIST_W0_1_MEAN = 4.13
HIST_OVERALL_MEAN = 2.04


def open_abs_bucket(open_sp: Any) -> Optional[str]:
    val = _f(open_sp)
    if val is None:
        return None
    mag = abs(val)
    if mag < 3.0:
        return "pickem_lt3"
    if mag < 7.0:
        return "mid_3_7"
    if mag < 14.0:
        return "large_7_14"
    return "blowout_14plus"


def week_label(week: Any) -> str:
    w = int(week or 0)
    if w <= 0:
        return "w0"
    if w == 1:
        return "w1"
    return "w2_plus"


def model_more_favorite(model: Any, open_sp: Any) -> Optional[bool]:
    """True if the model lays more points on the open favorite than the open.

    Pick'em (|open| < 0.5) → None. Home-spread: negative = home favorite.
    """
    m = _f(model)
    o = _f(open_sp)
    if m is None or o is None:
        return None
    if abs(o) < PICKEM_EPS:
        return None
    if o < 0:
        return m < o
    return m > o


def _error_stats(values: Sequence[float]) -> Dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "mae": None, "median_ae": None}
    srt = sorted(abs(v) for v in values)
    return {
        "n": len(values),
        "mean": round(sum(values) / len(values), 3),
        "mae": round(sum(abs(v) for v in values) / len(values), 3),
        "median_ae": round(srt[len(srt) // 2], 3),
    }


def _rate(flags: Sequence[Optional[bool]]) -> Dict[str, Any]:
    known = [x for x in flags if x is not None]
    n = len(known)
    hits = sum(1 for x in known if x)
    ci = wilson_interval(hits, n) if n else None
    return {
        "n": n,
        "hits": hits,
        "rate": round(hits / n, 4) if n else None,
        "ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
    }


def slice_opens(
    rows: Sequence[Mapping[str, Any]], *, hide_thin: bool = True
) -> Dict[str, Any]:
    errs: List[float] = []
    tot_errs: List[float] = []
    more_fav: List[Optional[bool]] = []
    home_fav_flags: List[bool] = []
    for row in rows:
        model = _f(row.get("model_spread_home"))
        open_sp = _f(row.get("open_spread_home"))
        if model is None or open_sp is None:
            continue
        errs.append(model - open_sp)
        more_fav.append(model_more_favorite(model, open_sp))
        home_fav_flags.append(open_sp < 0)
        mt = _f(row.get("model_total"))
        ot = _f(row.get("open_total"))
        if mt is not None and ot is not None:
            tot_errs.append(mt - ot)
    n = len(errs)
    thin = n < SLICE_MIN_N
    out: Dict[str, Any] = {
        "n": n,
        "thin": thin,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
    }
    if hide_thin and thin:
        out["note"] = f"thin (n={n} < {SLICE_MIN_N}) — listed, not a prior input"
        return out
    out.update(
        {
            "vs_open": _error_stats(errs),
            "model_more_favorite": _rate(more_fav),
            "short_favorite": _rate([None if x is None else (not x) for x in more_fav]),
            "n_home_fav_open": sum(1 for x in home_fav_flags if x),
            "n_home_dog_open": sum(1 for x in home_fav_flags if not x),
            "vs_open_total": _error_stats(tot_errs) if tot_errs else {"n": 0},
        }
    )
    return out


def _group(rows: Sequence[Mapping[str, Any]], key_fn) -> Dict[str, Dict[str, Any]]:
    buckets: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(key_fn(row))].append(row)
    return {k: slice_opens(v) for k, v in sorted(buckets.items())}


def bias_call(vs_open: Mapping[str, Any], *, n_matched: int) -> str:
    if n_matched < PRIOR_DESIGN_MIN_N:
        return "insufficient"
    mean = vs_open.get("mean")
    if mean is None:
        return "insufficient"
    # Hist cold / short-favorite: mean(model − market) > 0 (model less favorite).
    if mean >= 1.5:
        return "cold"
    if mean <= -1.5:
        return "hot"
    return "mixed"


def prior_design_gate(
    *,
    n_matched: int,
    n_opens: int,
    n_closes: int,
    bias: str,
) -> Dict[str, Any]:
    reasons: List[str] = []
    if n_matched < PRIOR_DESIGN_MIN_N:
        reasons.append(f"n_matched {n_matched} < {PRIOR_DESIGN_MIN_N}")
    if n_closes == 0:
        reasons.append("n_closes=0 — no held-out close / CLV")
    if n_matched < n_opens:
        reasons.append(f"join dropped {n_opens - n_matched} of {n_opens} opens")
    reasons.append("Week 3+ hold still in force (scaffold checklist)")
    reasons.append("not a release gate")
    go = False  # scaffold checklist: closes + more weeks + held-out plan
    return {
        "ready_for_kei_design_brief": go,
        "ready_to_sketch_open_line_prior": go and bias in {"cold", "hot"} and n_matched >= 40,
        "recommendation": (
            "hold_through_week_3"
            if n_closes == 0
            else "re_pull_when_more_books_post"
            if n_matched < PRIOR_DESIGN_MIN_N
            else "hold_through_week_3"
        ),
        "reasons": reasons,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
    }


def diagnose_opens(
    rows: Sequence[Mapping[str, Any]],
    *,
    n_opens: int,
    n_closes: int = 0,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    matched = [
        r
        for r in rows
        if _f(r.get("model_spread_home")) is not None and _f(r.get("open_spread_home")) is not None
    ]
    n_matched = len(matched)
    overall_full = slice_opens(matched, hide_thin=False)
    vs = overall_full.get("vs_open") or {}
    bias = bias_call(vs, n_matched=n_matched)
    match_rate = round(n_matched / n_opens, 4) if n_opens else None
    payload: Dict[str, Any] = {
        "diagnostic_id": DIAGNOSTIC_ID,
        "season": 2026,
        "status": "ok" if n_matched else "insufficient_market_rows",
        "n_opens": int(n_opens),
        "n_closes": int(n_closes),
        "n_matched": n_matched,
        "match_rate": match_rate,
        "book_rule": (
            f"open = first pre-kick snap; prefer {', '.join(PREFER_BOOKS)}; "
            "then any other book. Not consensus. Not lock."
        ),
        "bias": bias,
        "bias_one_liner": _one_liner(bias, vs, n_matched),
        "overall": overall_full,
        "by_week": _group(matched, lambda r: week_label(r.get("week"))),
        "by_open_abs_bucket": _group(
            [r for r in matched if open_abs_bucket(r.get("open_spread_home"))],
            lambda r: open_abs_bucket(r.get("open_spread_home")),
        ),
        "by_favorite_home": _group(
            [r for r in matched if _f(r.get("open_spread_home")) is not None],
            lambda r: "home_fav" if float(r["open_spread_home"]) < 0 else "home_dog",
        ),
        "by_conference_tier": _group(
            matched,
            lambda r: conference_tier(
                str(r.get("home_team_id") or ""),
                str(r.get("away_team_id") or ""),
            ),
        ),
        "hist_compare": {
            "hist_w0_1_mean_vs_close": HIST_W0_1_MEAN,
            "hist_overall_mean_vs_close": HIST_OVERALL_MEAN,
            "live_mean_vs_open": vs.get("mean"),
            "same_sign_as_hist_cold": (
                vs.get("mean") is not None and float(vs["mean"]) > 0
            ),
            "note": (
                "Hist is vs close on 2020–25 program-prior walk-forward. "
                "Live is v0.15 project-game vs 2026 opens. Same sign ≠ same engine."
            ),
        },
        "gate": prior_design_gate(
            n_matched=n_matched,
            n_opens=n_opens,
            n_closes=n_closes,
            bias=bias,
        ),
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "blend": False,
        "read_only": True,
        "not_a_release_gate": True,
        "cli": "scripts/cfb/cfb live-open",
        "ops": "data/ops/cfb-live-open-diagnostic-20260815.md",
    }
    if extra:
        payload.update(dict(extra))
    return payload


def _one_liner(bias: str, vs: Mapping[str, Any], n: int) -> str:
    mean = vs.get("mean")
    mae = vs.get("mae")
    if bias == "insufficient":
        return (
            f"Insufficient for prior design (n={n} < {PRIOR_DESIGN_MIN_N}). "
            "Re-pull when more books post. Not KEI."
        )
    if bias == "cold":
        return (
            f"Bias persists vs 2026 open: cold / short-favorite "
            f"(mean {mean:+.2f}, MAE {mae}). Same sign as hist. Not KEI."
        )
    if bias == "hot":
        return (
            f"Bias flips vs 2026 open: hot vs books "
            f"(mean {mean:+.2f}, MAE {mae}). Do not overfit. Not KEI."
        )
    return (
        f"Mixed vs 2026 open (mean {mean:+.2f}, MAE {mae}). "
        "Do not overfit one weekend. Not KEI."
    )


def documentation() -> Dict[str, Any]:
    return {
        "id": DIAGNOSTIC_ID,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "blend": False,
        "read_only": True,
        "not_a_release_gate": True,
        "ops": "data/ops/cfb-live-open-diagnostic-20260815.md",
        "cli": "scripts/cfb/cfb live-open",
        "slice_min_n": SLICE_MIN_N,
        "prior_design_min_n": PRIOR_DESIGN_MIN_N,
    }
