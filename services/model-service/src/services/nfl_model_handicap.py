"""NFL model_* (research fair) vs handicap_* (KEI product line) helpers.

Architecture (NFL, 2026):
  model_*     = pre-market-blend Monte Carlo fair (research snapshot)
  handicap_*  = published product line (post-blend + totals calibration + overlays)
  spread_home / total_mean columns = handicap aliases for one release

Honesty limits:
  - Model spread/total diverge from KEI only when diagnostics.market_blend
    recorded a pre_blend_* mean (spread_applied / total_applied).
  - Win probs and fair MLs are post-blend only today → Model ML = KEI (identity).
  - Injury report cadence may reprice KEI via line_role=handicap while freezing
    stamped model_markets (see nfl_injury_kei_cadence). Full research re-sims
    still stamp line_role=model.
  - If blend was not applied, Model = KEI (identity). Do not invent deltas.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


_MODEL_MARKET_KEYS = (
    "home_win_prob",
    "away_win_prob",
    "total_mean",
    "spread_home",
    "fair_home_ml",
    "fair_away_ml",
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


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None  # NaN check


def pre_blend_model_markets_from_diagnostics(
    projection: Dict[str, Any],
    *,
    handicap_markets: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Derive research Model markets from diagnostics.market_blend pre_blend_*.

    Returns None when no pre-blend signal exists (caller should identity-fallback).
    """
    markets = handicap_markets
    if not isinstance(markets, dict):
        markets = projection.get("markets") if isinstance(projection.get("markets"), dict) else {}
    if not isinstance(markets, dict) or not markets:
        return None

    diagnostics = projection.get("diagnostics")
    blend = (
        diagnostics.get("market_blend")
        if isinstance(diagnostics, dict)
        else None
    )
    if not isinstance(blend, dict):
        return None

    model = snapshot_markets(markets)
    diverged = False

    if blend.get("spread_applied"):
        pre_margin = _to_float(blend.get("pre_blend_margin_mean"))
        if pre_margin is not None:
            # Home spread convention: negative = home favored (same as published).
            model["spread_home"] = round(-pre_margin, 2)
            diverged = True

    if blend.get("total_applied"):
        pre_total = _to_float(blend.get("pre_blend_total_mean"))
        if pre_total is not None:
            model["total_mean"] = round(pre_total, 2)
            diverged = True

    return model if diverged else None


def resolve_model_markets(
    markets: Dict[str, Any],
    *,
    prior_model_markets: Optional[Dict[str, Any]] = None,
    existing_model_markets: Optional[Dict[str, Any]] = None,
    projection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefer existing/prior stamped model; else pre-blend; else identity."""
    for candidate in (existing_model_markets, prior_model_markets):
        snap = _coerce_model_markets(candidate)
        if snap is not None:
            return snap

    if isinstance(projection, dict):
        from_blend = pre_blend_model_markets_from_diagnostics(
            projection,
            handicap_markets=markets,
        )
        if from_blend is not None:
            return from_blend

    return snapshot_markets(markets)


def annotate_projection_model_handicap(
    projection: Dict[str, Any],
    *,
    prior_model_markets: Optional[Dict[str, Any]] = None,
    line_role: str = "model",
) -> Dict[str, Any]:
    """Stamp model_markets + handicap_markets onto a projection dict in place.

    line_role:
      - "model": full research re-sim → Model from pre-blend (or identity);
        handicap = current published markets.
      - "handicap": later product-only reprice → preserve prior/existing Model;
        handicap = current published markets.
    """
    markets = projection.get("markets")
    if not isinstance(markets, dict):
        return projection

    existing = projection.get("model_markets")
    if line_role == "handicap":
        model_markets = resolve_model_markets(
            markets,
            prior_model_markets=prior_model_markets,
            existing_model_markets=_coerce_model_markets(existing),
            # Do not re-derive from current blend when preserving handicap role.
            projection=None,
        )
    else:
        # Fresh research write: prefer already-stamped existing, else pre-blend.
        model_markets = resolve_model_markets(
            markets,
            existing_model_markets=_coerce_model_markets(existing),
            projection=projection,
        )

    handicap_markets = snapshot_markets(markets)
    projection["model_markets"] = model_markets
    projection["handicap_markets"] = handicap_markets
    projection["line_role"] = line_role

    # Top-level convenience aliases for fair-lines consumers.
    projection["model_spread_home"] = model_markets.get("spread_home")
    projection["model_total_mean"] = model_markets.get("total_mean")
    projection["model_home_win_prob"] = model_markets.get("home_win_prob")
    projection["model_away_win_prob"] = model_markets.get("away_win_prob")
    projection["model_fair_home_ml"] = model_markets.get("fair_home_ml")
    projection["model_fair_away_ml"] = model_markets.get("fair_away_ml")
    projection["handicap_spread_home"] = handicap_markets.get("spread_home")
    projection["handicap_total_mean"] = handicap_markets.get("total_mean")
    projection["handicap_home_win_prob"] = handicap_markets.get("home_win_prob")
    projection["handicap_away_win_prob"] = handicap_markets.get("away_win_prob")
    projection["handicap_fair_home_ml"] = handicap_markets.get("fair_home_ml")
    projection["handicap_fair_away_ml"] = handicap_markets.get("fair_away_ml")
    return projection


def extract_model_markets_from_projection(
    projection: Any,
) -> Optional[Dict[str, Any]]:
    """Pull model_markets from projection JSON (stamped or pre-blend fallback)."""
    if isinstance(projection, str):
        try:
            import json

            projection = json.loads(projection)
        except Exception:
            return None
    if not isinstance(projection, dict):
        return None

    stamped = _coerce_model_markets(projection.get("model_markets"))
    if stamped is not None:
        return stamped

    markets = projection.get("markets")
    if not isinstance(markets, dict):
        markets = {}
    return pre_blend_model_markets_from_diagnostics(
        projection,
        handicap_markets=markets,
    )


def extract_handicap_markets_from_projection(
    projection: Any,
    *,
    fallback_spread: Any = None,
    fallback_total: Any = None,
    fallback_home_win_prob: Any = None,
    fallback_away_win_prob: Any = None,
    fallback_fair_home_ml: Any = None,
    fallback_fair_away_ml: Any = None,
) -> Dict[str, Any]:
    """Handicap = stamped handicap_markets, else published markets/columns."""
    if isinstance(projection, str):
        try:
            import json

            projection = json.loads(projection)
        except Exception:
            projection = None

    if isinstance(projection, dict):
        stamped = _coerce_model_markets(projection.get("handicap_markets"))
        if stamped is not None:
            return stamped
        markets = projection.get("markets")
        if isinstance(markets, dict) and markets:
            return snapshot_markets(markets)

    out: Dict[str, Any] = {}
    if fallback_spread is not None:
        out["spread_home"] = fallback_spread
    if fallback_total is not None:
        out["total_mean"] = fallback_total
    if fallback_home_win_prob is not None:
        out["home_win_prob"] = fallback_home_win_prob
    if fallback_away_win_prob is not None:
        out["away_win_prob"] = fallback_away_win_prob
    if fallback_fair_home_ml is not None:
        out["fair_home_ml"] = fallback_fair_home_ml
    if fallback_fair_away_ml is not None:
        out["fair_away_ml"] = fallback_fair_away_ml
    return out


def resolve_model_and_handicap(
    *,
    projection: Any = None,
    spread_home: Any = None,
    total_mean: Any = None,
    home_win_prob: Any = None,
    away_win_prob: Any = None,
    fair_home_ml: Any = None,
    fair_away_ml: Any = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve (model, handicap) with identity fallback for fair-lines rows."""
    handicap = extract_handicap_markets_from_projection(
        projection,
        fallback_spread=spread_home,
        fallback_total=total_mean,
        fallback_home_win_prob=home_win_prob,
        fallback_away_win_prob=away_win_prob,
        fallback_fair_home_ml=fair_home_ml,
        fallback_fair_away_ml=fair_away_ml,
    )
    # Prefer published columns when present (authoritative product line).
    if spread_home is not None:
        handicap["spread_home"] = spread_home
    if total_mean is not None:
        handicap["total_mean"] = total_mean
    if home_win_prob is not None:
        handicap["home_win_prob"] = home_win_prob
    if away_win_prob is not None:
        handicap["away_win_prob"] = away_win_prob
    if fair_home_ml is not None:
        handicap["fair_home_ml"] = fair_home_ml
    if fair_away_ml is not None:
        handicap["fair_away_ml"] = fair_away_ml

    model = extract_model_markets_from_projection(projection)
    if model is None:
        model = dict(handicap)
    else:
        # Identity-fill ML/win when Model has only spread/total divergence.
        for key in _MODEL_MARKET_KEYS:
            if key not in model and key in handicap:
                model[key] = handicap[key]
    return model, handicap


def fair_lines_model_handicap_fields(
    *,
    model: Dict[str, Any],
    handicap: Dict[str, Any],
) -> Dict[str, Any]:
    """Extra fair-lines payload fields (model_* + handicap_* + blend meta)."""
    h_spread = handicap.get("spread_home")
    h_total = handicap.get("total_mean")
    m_spread = model.get("spread_home", h_spread)
    m_total = model.get("total_mean", h_total)

    return {
        "handicap_spread_home": h_spread,
        "handicap_total_mean": h_total,
        "handicap_home_win_prob": handicap.get("home_win_prob"),
        "handicap_away_win_prob": handicap.get("away_win_prob"),
        "handicap_fair_home_ml": handicap.get("fair_home_ml"),
        "handicap_fair_away_ml": handicap.get("fair_away_ml"),
        "model_spread_home": m_spread,
        "model_total_mean": m_total,
        "model_home_win_prob": model.get("home_win_prob", handicap.get("home_win_prob")),
        "model_away_win_prob": model.get("away_win_prob", handicap.get("away_win_prob")),
        "model_fair_home_ml": model.get("fair_home_ml", handicap.get("fair_home_ml")),
        "model_fair_away_ml": model.get("fair_away_ml", handicap.get("fair_away_ml")),
        "model_equals_kei": (
            _to_float(m_spread) == _to_float(h_spread)
            and _to_float(m_total) == _to_float(h_total)
        ),
    }


def extract_prior_model_markets(row: Any) -> Optional[Dict[str, Any]]:
    """Pull model_markets from a prior nfl projection row / mapping.

    Used by injury→KEI handicap reprices so Model research fair stays frozen.
    """
    if row is None:
        return None
    mapping = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    proj = mapping.get("projection")
    if isinstance(proj, str):
        try:
            import json

            proj = json.loads(proj)
        except Exception:
            proj = None
    if isinstance(proj, dict):
        stamped = extract_model_markets_from_projection(proj)
        if stamped is not None:
            return stamped
    # Direct model_markets on the row itself (fixture / in-memory).
    direct = _coerce_model_markets(mapping.get("model_markets"))
    if direct is not None:
        return direct
    if isinstance(mapping.get("markets"), dict):
        return extract_model_markets_from_projection(mapping)
    return None
