"""CFB independent KEI — model stays research-fair; KEI is the published line.

Doctrine (2026 + later seasons)
-------------------------------
- Model = pure research fair. This module never mutates model_* fields.
- KEI = model + versioned handicap menu + measured bias guard.
- Market is information only. |KEI − open| ≥ threshold → INVESTIGATE, never
  auto-move KEI to the open.
- Edge / Tag = KEI vs best market only.
- Early season (calendar weeks 0–2): elevated PLAY threshold; PASS default.

Handicap menu
-------------
QB / trench / returning production / coaching / HFA already live inside the
frozen model compose. They are logged as ``in_model`` — not restacked.
Rest / travel / current outs: apply only when a current-path fact exists.
Bias guard is the only default numeric KEI delta.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KEI_VERSION = "cfb-kei-v1.0-2026w0"
BIAS_GUARD_VERSION = "cfb-bias-guard-v1-histcal-20260805"
KEI_RULES_DOC = "data/ops/cfb-kei-rules-2026.md"

EARLY_WEEKS = frozenset({0, 1, 2})

# Elevated early-season thresholds (stricter than NFL steady-state ~2–2.5).
PLAY_EDGE_PTS_EARLY = 4.0
LEAN_EDGE_PTS_EARLY = 2.5
PLAY_EDGE_PTS_STEADY = 2.5
LEAN_EDGE_PTS_STEADY = 1.5

# Hist-cal 2026-08-05: home favorites ~+6.8 pts too soft vs close; home dogs
# too bullish. We do NOT copy the close. Guard takes a capped slice of that
# residual, then shrinks remaining short favorites so we do not fire thin favs.
HOME_FAV_CORRECTION = -1.20  # more home favorite (spread more negative)
HOME_DOG_CORRECTION = 1.00  # more home dog (spread more positive)
CORRECTION_CAP = 1.50
SHORT_FAV_ABS_MIN = 1.00
SHORT_FAV_ABS_MAX = 7.50
SHORT_FAV_SHRINK = 0.12
SHORT_FAV_SHRINK_CAP = 1.25

INVESTIGATE_ABS = 6.0
FCS_SIGMA_MULT = 1.35


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _round(v: Optional[float], nd: int = 2) -> Optional[float]:
    if v is None or not math.isfinite(v):
        return None
    return round(float(v), nd)


def early_season(week: Optional[int]) -> bool:
    try:
        return int(week) in EARLY_WEEKS
    except (TypeError, ValueError):
        return True


def tag_thresholds(week: Optional[int]) -> Tuple[float, float]:
    if early_season(week):
        return PLAY_EDGE_PTS_EARLY, LEAN_EDGE_PTS_EARLY
    return PLAY_EDGE_PTS_STEADY, LEAN_EDGE_PTS_STEADY


def _wp_from_spread(spread_home: float, margin_sd: float) -> float:
    # spread_home = away - home; home margin = -spread
    sd = max(float(margin_sd or 15.2), 6.0)
    z = (-float(spread_home)) / sd
    return max(0.02, min(0.98, 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))))


def _menu_in_model(proj: Mapping[str, Any]) -> List[Dict[str, Any]]:
    drivers = proj.get("drivers") if isinstance(proj.get("drivers"), Mapping) else {}
    primary = drivers.get("primary_signals") if isinstance(drivers, Mapping) else {}
    primary = primary if isinstance(primary, Mapping) else {}
    matchup = drivers.get("matchup") if isinstance(drivers, Mapping) else {}
    matchup = matchup if isinstance(matchup, Mapping) else {}
    home_qb = primary.get("home_qb_situation_index")
    away_qb = primary.get("away_qb_situation_index")
    home_ol = (primary.get("home_unit_grades") or {}).get("ol") if isinstance(primary.get("home_unit_grades"), Mapping) else None
    away_ol = (primary.get("away_unit_grades") or {}).get("ol") if isinstance(primary.get("away_unit_grades"), Mapping) else None
    return [
        {
            "factor": "qb_situation",
            "applied": False,
            "in_model": True,
            "reason": f"QB situation in model compose (home idx {home_qb}, away idx {away_qb}) — not restacked",
        },
        {
            "factor": "trench_ol",
            "applied": False,
            "in_model": True,
            "reason": f"OL / trench proxy in model units (home OL {home_ol}, away OL {away_ol}) — not restacked",
        },
        {
            "factor": "returning_production",
            "applied": False,
            "in_model": True,
            "reason": "Returning production / portal / experience in roster_strength — not restacked",
        },
        {
            "factor": "coaching",
            "applied": False,
            "in_model": True,
            "reason": (
                f"Coaching continuity in model (home adj {matchup.get('home_coaching_adj')}, "
                f"away adj {matchup.get('away_coaching_adj')}) — not restacked"
            ),
        },
        {
            "factor": "hfa",
            "applied": False,
            "in_model": True,
            "reason": (
                f"Variable HFA in model (hfa={matchup.get('hfa')}, "
                f"neutral={matchup.get('neutral_site')}) — not restacked"
            ),
        },
        {
            "factor": "rest_travel",
            "applied": False,
            "in_model": False,
            "reason": "rest / travel not in stack (no current-path fact)",
        },
        {
            "factor": "injury_current",
            "applied": False,
            "in_model": False,
            "reason": "current outs not in stack — packaged depth only, not a live injury feed",
        },
    ]


def apply_bias_guard(
    model_spread: float,
    *,
    week: Optional[int],
) -> Tuple[float, List[Dict[str, Any]]]:
    """Return (kei_spread, driver entries). Model spread is not mutated."""
    entries: List[Dict[str, Any]] = []
    kei = float(model_spread)
    if not early_season(week):
        entries.append(
            {
                "factor": "bias_guard",
                "applied": False,
                "version": BIAS_GUARD_VERSION,
                "reason": "bias guard not applied after early window (weeks 0–2)",
            }
        )
        return kei, entries

    raw = float(model_spread)
    if raw < 0:
        delta = max(-CORRECTION_CAP, HOME_FAV_CORRECTION)
        kei = raw + delta
        entries.append(
            {
                "factor": "bias_guard_home_fav",
                "applied": True,
                "version": BIAS_GUARD_VERSION,
                "spread_pts": delta,
                "reason": (
                    f"home-favorite correction {delta:+.2f} "
                    f"(hist-cal residual ~+6.8 vs close; {BIAS_GUARD_VERSION} takes a capped slice, not the close)"
                ),
            }
        )
    elif raw > 0:
        delta = min(CORRECTION_CAP, HOME_DOG_CORRECTION)
        kei = raw + delta
        entries.append(
            {
                "factor": "bias_guard_home_dog",
                "applied": True,
                "version": BIAS_GUARD_VERSION,
                "spread_pts": delta,
                "reason": (
                    f"home-dog correction {delta:+.2f} "
                    f"(hist-cal home dogs too bullish; capped slice, not market copy)"
                ),
            }
        )
    else:
        entries.append(
            {
                "factor": "bias_guard",
                "applied": False,
                "version": BIAS_GUARD_VERSION,
                "reason": "pick'em — no favorite-side correction",
            }
        )

    mag = abs(kei)
    if SHORT_FAV_ABS_MIN <= mag <= SHORT_FAV_ABS_MAX:
        shrink = min(SHORT_FAV_SHRINK_CAP, mag * SHORT_FAV_SHRINK)
        if kei < 0:
            kei = kei + shrink  # toward pick'em
        else:
            kei = kei - shrink
        entries.append(
            {
                "factor": "short_favorite_shrink",
                "applied": True,
                "version": BIAS_GUARD_VERSION,
                "spread_pts": shrink if raw < 0 else -shrink,
                "reason": (
                    f"short-favorite shrink {shrink:.2f} toward pick'em "
                    f"(|KEI| {mag:.1f} in {SHORT_FAV_ABS_MIN}-{SHORT_FAV_ABS_MAX}) — do not fire thin favs"
                ),
            }
        )
    return kei, entries


def tag_from_edge(
    edge_pts: Optional[float],
    *,
    week: Optional[int],
    fbs_vs_fbs: bool,
) -> str:
    if not fbs_vs_fbs:
        return "PASS"
    if edge_pts is None or not math.isfinite(edge_pts):
        return "PASS"
    play, lean = tag_thresholds(week)
    mag = abs(float(edge_pts))
    if mag >= play:
        return "PLAY"
    if mag >= lean:
        return "LEAN"
    return "PASS"


def apply_cfb_kei(
    proj: Mapping[str, Any],
    *,
    market_spread_home: Optional[float] = None,
    fbs_vs_fbs: bool = True,
    fcs_home: bool = False,
    fcs_away: bool = False,
    current_factors: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build KEI payload from a project-game dict. Model fields are copied, not edited."""
    week = proj.get("week")
    model_spread = _f(proj.get("model_spread_home") if proj.get("model_spread_home") is not None else proj.get("spread_home"))
    model_total = _f(proj.get("model_total") if proj.get("model_total") is not None else proj.get("expected_total"))
    model_wp = _f(proj.get("model_home_win_prob") if proj.get("model_home_win_prob") is not None else proj.get("home_win_prob"))
    margin_sd = _f(proj.get("margin_sd")) or 15.2
    if fcs_home or fcs_away:
        margin_sd = margin_sd * FCS_SIGMA_MULT

    drivers: List[Dict[str, Any]] = list(_menu_in_model(proj))
    for extra in current_factors or []:
        if isinstance(extra, Mapping):
            drivers.append(dict(extra))

    kei_spread = model_spread
    if model_spread is None:
        drivers.append(
            {
                "factor": "bias_guard",
                "applied": False,
                "reason": "model spread missing — KEI identity skipped",
            }
        )
    else:
        kei_spread, guard = apply_bias_guard(model_spread, week=week)
        drivers.extend(guard)
        kei_spread = _round(kei_spread)

    investigate = False
    mkt = _f(market_spread_home)
    if kei_spread is not None and mkt is not None and abs(kei_spread - mkt) >= INVESTIGATE_ABS:
        investigate = True
        drivers.append(
            {
                "factor": "market_disagreement",
                "applied": False,
                "reason": (
                    f"INVESTIGATE |KEI {kei_spread:+.1f} − open {mkt:+.1f}| "
                    f"≥ {INVESTIGATE_ABS} — KEI not moved to open"
                ),
            }
        )

    kei_wp = _round(_wp_from_spread(kei_spread, margin_sd), 4) if kei_spread is not None else model_wp
    edge_pts = None
    if kei_spread is not None and mkt is not None:
        # Home-spread convention: KEI − market. Positive ⇒ KEI likes home more than books.
        edge_pts = _round(mkt - kei_spread)
    tag = tag_from_edge(edge_pts, week=week, fbs_vs_fbs=fbs_vs_fbs and not (fcs_home or fcs_away))

    out = {
        "kei_version": KEI_VERSION,
        "bias_guard_version": BIAS_GUARD_VERSION,
        "used_in_spread": True,
        "model_used_in_spread": False,
        "model_spread_home": _round(model_spread),
        "model_total": _round(model_total),
        "model_home_win_prob": _round(model_wp, 4),
        "model_sigma": _round(margin_sd, 3),
        "kei_spread_home": kei_spread,
        "kei_total": _round(model_total),
        "kei_home_win_prob": kei_wp,
        "market_spread_home": _round(mkt),
        "edge_pts": edge_pts,
        "tag": tag,
        "investigate": investigate,
        "early_season": early_season(week),
        "fbs_vs_fbs": bool(fbs_vs_fbs) and not (fcs_home or fcs_away),
        "fcs_opener": bool(fcs_home or fcs_away),
        "play_threshold": tag_thresholds(week)[0],
        "lean_threshold": tag_thresholds(week)[1],
        "drivers": drivers,
        "rules_doc": KEI_RULES_DOC,
    }
    assert_kei_not_tail(out)
    return out


def assert_kei_not_tail(kei_payload: Mapping[str, Any]) -> None:
    """Guard: published KEI line must not be E[wins] / natty% / playoff%.

    Raises AssertionError with KEI_EQUALS_TAIL if a publisher collapses tails
    into the KEI object.
    """
    forbidden = (
        "expected_wins",
        "e_wins",
        "mean_wins",
        "natty_pct",
        "cfp_make_pct",
        "playoff_pct",
        "title_pct",
    )
    keys = {str(k).lower() for k in kei_payload.keys()}
    hit = [k for k in forbidden if k in keys]
    if hit:
        raise AssertionError(f"KEI_EQUALS_TAIL: KEI payload contains {hit}")


def diagnostic_short_fav_sample() -> Dict[str, Any]:
    """Held diagnostic on the hist-cal short-favorite band (not live market copy).

    Pure model on 1–7.5 home favorites was the walk-forward failure mode
    (compressed vs close, then easy to mis-tag vs books). After the guard:
    signs stay favorite, move is capped, and a 3-pt book would not clear the
    early PLAY threshold — thin favorite fires drop.
    """
    model_spreads = [-2.0, -3.5, -5.0, -6.5, -1.5, -4.0, -7.0, -2.5]
    after = [apply_bias_guard(s, week=1)[0] for s in model_spreads]
    signs_ok = all((a < 0) == (m < 0) for a, m in zip(after, model_spreads))
    moves = [abs(a - m) for a, m in zip(after, model_spreads)]
    # Books hang a bigger favorite by 4.5 (hist-cal compression vs close).
    # Raw model vs that book clears the 4-pt PLAY bar; KEI should not.
    raw_play = 0
    kei_play = 0
    for model, kei in zip(model_spreads, after):
        book = model - 4.5 if model < 0 else model + 4.5
        if abs(book - model) >= PLAY_EDGE_PTS_EARLY:
            raw_play += 1
        if abs(book - kei) >= PLAY_EDGE_PTS_EARLY:
            kei_play += 1
    return {
        "version": BIAS_GUARD_VERSION,
        "n": len(model_spreads),
        "band": [SHORT_FAV_ABS_MIN, SHORT_FAV_ABS_MAX],
        "mean_abs_model": round(sum(abs(s) for s in model_spreads) / len(model_spreads), 3),
        "mean_abs_kei": round(sum(abs(s) for s in after) / len(after), 3),
        "mean_abs_move": round(sum(moves) / len(moves), 3),
        "max_abs_move": round(max(moves), 3),
        "signs_preserved": signs_ok,
        "capped": max(moves) <= (CORRECTION_CAP + SHORT_FAV_SHRINK_CAP + 1e-9),
        "raw_play_vs_3pt_book": raw_play,
        "kei_play_vs_3pt_book": kei_play,
        "improved": signs_ok and kei_play <= raw_play,
        "note": (
            "Favorite-side correction is a capped hist-cal slice, not the close. "
            "Early PLAY stays at 4 pts, so a 3-pt book disagreement does not fire. "
            "Not a long-run ATS profit claim."
        ),
    }
