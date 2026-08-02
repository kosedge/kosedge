"""MLB model_* (pure sim) vs handicap_* (KEI product line) helpers.

Architecture:
  model_*     = pure sim / research fair (snapshotted at first write)
  handicap_*  = KEI product line (nowcast / lineup / weather / future blend)
  fair_fg_*   = handicap alias for one release
  If handicap missing → handicap = model (identity)
"""

from __future__ import annotations

from typing import Any, Dict, Optional


_MODEL_MARKET_KEYS = (
    "f5_home_win_prob",
    "fg_home_win_prob",
    "f5_total_mean",
    "fg_total_mean",
    "fair_f5_home_ml",
    "fair_fg_home_ml",
    "fair_f5_total",
    "fair_fg_total",
    "fair_fg_spread_home",
    "fair_f5_spread_home",
    "fg_home_cover_prob_run_line",
    "f5_home_cover_prob_run_line",
    "fg_margin_mean",
    "f5_margin_mean",
)


def snapshot_markets(markets: Dict[str, Any]) -> Dict[str, Any]:
    """Copy the market keys used for model/handicap identity."""
    out: Dict[str, Any] = {}
    for key in _MODEL_MARKET_KEYS:
        if key in markets:
            out[key] = markets[key]
    return out


def _coerce_model_markets(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict) or not raw:
        return None
    snap = snapshot_markets(raw)
    return snap or None


def resolve_model_markets(
    markets: Dict[str, Any],
    *,
    prior_model_markets: Optional[Dict[str, Any]] = None,
    existing_model_markets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefer existing/prior model snapshot; else identity with current markets."""
    for candidate in (existing_model_markets, prior_model_markets):
        snap = _coerce_model_markets(candidate)
        if snap is not None:
            return snap
    return snapshot_markets(markets)


def annotate_projection_model_handicap(
    projection: Dict[str, Any],
    *,
    prior_model_markets: Optional[Dict[str, Any]] = None,
    line_role: str = "handicap",
) -> Dict[str, Any]:
    """Stamp model_markets + handicap_markets onto a projection dict in place.

    line_role:
      - "model": current markets are pure sim (daily/first write) → model=handicap
      - "handicap": current markets are KEI product (nowcast) → preserve prior model
    """
    markets = projection.get("markets")
    if not isinstance(markets, dict):
        return projection

    existing = projection.get("model_markets")
    if line_role == "model":
        model_markets = resolve_model_markets(
            markets,
            existing_model_markets=_coerce_model_markets(existing),
        )
    else:
        model_markets = resolve_model_markets(
            markets,
            prior_model_markets=prior_model_markets,
            existing_model_markets=_coerce_model_markets(existing),
        )

    handicap_markets = snapshot_markets(markets)
    projection["model_markets"] = model_markets
    projection["handicap_markets"] = handicap_markets
    projection["line_role"] = line_role
    # Top-level convenience aliases for fair-lines consumers.
    projection["model_fg_home_win_prob"] = model_markets.get("fg_home_win_prob")
    projection["model_fair_fg_home_ml"] = model_markets.get("fair_fg_home_ml")
    projection["model_fair_fg_total"] = model_markets.get("fair_fg_total")
    projection["model_fg_total_mean"] = model_markets.get("fg_total_mean")
    projection["model_fair_fg_spread_home"] = model_markets.get("fair_fg_spread_home")
    projection["handicap_fg_home_win_prob"] = handicap_markets.get("fg_home_win_prob")
    projection["handicap_fair_fg_home_ml"] = handicap_markets.get("fair_fg_home_ml")
    projection["handicap_fair_fg_total"] = handicap_markets.get("fair_fg_total")
    projection["handicap_fg_total_mean"] = handicap_markets.get("fg_total_mean")
    projection["handicap_fair_fg_spread_home"] = handicap_markets.get(
        "fair_fg_spread_home"
    )
    return projection


def extract_prior_model_markets(row: Any) -> Optional[Dict[str, Any]]:
    """Pull model_markets from a prior mlb_market_projections row mapping/dict."""
    if row is None:
        return None
    mapping = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    # Dedicated columns first (post-048).
    col_snap = {
        "fg_home_win_prob": mapping.get("model_fg_home_win_prob"),
        "fg_total_mean": mapping.get("model_fg_total_mean"),
        "fair_fg_home_ml": mapping.get("model_fair_fg_home_ml"),
        "fair_fg_total": mapping.get("model_fair_fg_total"),
        "fair_fg_spread_home": mapping.get("model_fair_fg_spread_home"),
    }
    if any(v is not None for v in col_snap.values()):
        return {k: v for k, v in col_snap.items() if v is not None}

    proj = mapping.get("projection")
    if isinstance(proj, str):
        try:
            import json

            proj = json.loads(proj)
        except Exception:
            proj = None
    if isinstance(proj, dict):
        snap = _coerce_model_markets(proj.get("model_markets"))
        if snap is not None:
            return snap
        # Legacy rows: treat published markets as the model snapshot.
        markets = proj.get("markets")
        if isinstance(markets, dict):
            return snapshot_markets(markets)
    return None


def fair_lines_payload_from_row(
    *,
    game_id: Any,
    game_date: Any,
    start_time: Any,
    home_team: Any,
    away_team: Any,
    fg_home_win_prob: Any,
    fair_fg_home_ml: Any,
    fg_total_mean: Any,
    fair_fg_total: Any,
    fair_fg_spread_home: Any,
    fg_home_cover_prob_run_line: Any,
    fg_margin_mean: Any,
    projected_at: Any,
    model_markets: Optional[Dict[str, Any]] = None,
    handicap_markets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build fair-lines API row with model_*, handicap_*, and fair_fg_* alias."""
    handicap = handicap_markets or {}
    model = model_markets or {}

    # Published columns are handicap; JSON snapshots fill gaps.
    h_win = handicap.get("fg_home_win_prob", fg_home_win_prob)
    h_ml = handicap.get("fair_fg_home_ml", fair_fg_home_ml)
    h_total_mean = handicap.get("fg_total_mean", fg_total_mean)
    h_total = handicap.get("fair_fg_total", fair_fg_total)
    h_spread = handicap.get("fair_fg_spread_home", fair_fg_spread_home)

    # Identity fallback: model = handicap when model missing.
    m_win = model.get("fg_home_win_prob", h_win)
    m_ml = model.get("fair_fg_home_ml", h_ml)
    m_total_mean = model.get("fg_total_mean", h_total_mean)
    m_total = model.get("fair_fg_total", h_total)
    m_spread = model.get("fair_fg_spread_home", h_spread)

    return {
        "game_id": game_id,
        "game_date": game_date,
        "start_time": start_time,
        "home_team": home_team,
        "away_team": away_team,
        # Handicap = KEI (fair_fg_* alias for one release)
        "fg_home_win_prob": h_win,
        "fair_fg_home_ml": h_ml,
        "fg_total_mean": h_total_mean,
        "fair_fg_total": h_total,
        "fair_fg_spread_home": h_spread,
        "fg_home_cover_prob_run_line": fg_home_cover_prob_run_line,
        "fg_margin_mean": fg_margin_mean,
        "handicap_fg_home_win_prob": h_win,
        "handicap_fair_fg_home_ml": h_ml,
        "handicap_fg_total_mean": h_total_mean,
        "handicap_fair_fg_total": h_total,
        "handicap_fair_fg_spread_home": h_spread,
        # Model = pure sim / research
        "model_fg_home_win_prob": m_win,
        "model_fair_fg_home_ml": m_ml,
        "model_fg_total_mean": m_total_mean,
        "model_fair_fg_total": m_total,
        "model_fair_fg_spread_home": m_spread,
        "projected_at": projected_at,
    }
