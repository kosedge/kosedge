"""Market info_overlap MVP on KEI / game card.

Fields (v1):
  - ``kei_situation_flags`` — applied KEI factor labels from the reprice log
  - ``market_line`` — current market spread (home convention)
  - ``market_as_of`` — market snapshot timestamp
  - ``info_overlap`` — ``unknown`` | ``kei_ahead`` | ``market_ahead`` | ``aligned``

v1 rules (no auto-bet, no KEI juice from market_ahead):
  - After last pack commit, market moved ≥ threshold toward the **same side**
    as KEI's spread delta → ``market_ahead`` (informational only)
  - Pack committed and market flat (|move| < threshold) → ``kei_ahead``
  - Pack committed, market moved, signs agree and |move| near |kei| → ``aligned``
  - Missing market / pack_as_of / kei delta → ``unknown``

No accepts. No ingest rewrites. Does not change remat means when market_ahead.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

INFO_OVERLAP_VERSION = "info_overlap_v1"
INFO_OVERLAP_VALUES = frozenset({"unknown", "kei_ahead", "market_ahead", "aligned"})

# Home-spread points: market must move at least this much to count as a move.
MARKET_MOVE_THRESHOLD = 0.5
# |market_move - kei_delta| within this → aligned (same side already required).
ALIGNED_BAND = 0.75


def _f(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:
        return None
    return out


def _sign(value: float) -> int:
    if value > 1e-9:
        return 1
    if value < -1e-9:
        return -1
    return 0


def extract_kei_situation_flags(kei_log: Mapping[str, Any]) -> List[str]:
    """Compact labels from applied KEI factors (no means rewrite)."""
    flags: List[str] = []
    for entry in kei_log.get("applied_factors") or []:
        if not isinstance(entry, Mapping):
            continue
        if not entry.get("applied", True):
            continue
        factor = str(entry.get("factor") or "").strip()
        if not factor or factor == "injury_net":
            continue
        if factor not in flags:
            flags.append(factor)
    return flags


def classify_info_overlap(
    *,
    kei_spread_delta: Any,
    market_line: Any,
    market_line_at_pack: Any,
    pack_as_of: Any = None,
    market_as_of: Any = None,
    threshold: float = MARKET_MOVE_THRESHOLD,
) -> str:
    """Return unknown|kei_ahead|market_ahead|aligned."""
    kei_d = _f(kei_spread_delta)
    m_now = _f(market_line)
    m_pack = _f(market_line_at_pack)
    if kei_d is None or m_now is None or m_pack is None:
        return "unknown"
    if not pack_as_of:
        return "unknown"

    market_move = m_now - m_pack
    kei_s = _sign(kei_d)
    mkt_s = _sign(market_move)

    if abs(market_move) < float(threshold):
        # Pack committed; market flat → model/KEI still ahead of market.
        return "kei_ahead"

    if kei_s == 0:
        # KEI did not move the number; market did → unknown (not claiming edge).
        return "unknown"

    if mkt_s != kei_s:
        # Market moved opposite KEI — not "ahead" on the same side.
        return "unknown"

    # Same side. market_ahead when market moved enough after pack commit.
    # aligned when market move magnitude is near KEI delta.
    if abs(market_move - kei_d) <= ALIGNED_BAND:
        return "aligned"
    return "market_ahead"


def build_info_overlap_card(
    *,
    kei_log: Mapping[str, Any],
    market_line: Any = None,
    market_line_at_pack: Any = None,
    market_as_of: Any = None,
    pack_as_of: Any = None,
) -> Dict[str, Any]:
    """Attach info_overlap fields to a KEI/game card view. No juice."""
    flags = extract_kei_situation_flags(kei_log)
    kei_delta = kei_log.get("spread_delta")
    pack_ts = pack_as_of or kei_log.get("pack_as_of") or ""
    overlap = classify_info_overlap(
        kei_spread_delta=kei_delta,
        market_line=market_line,
        market_line_at_pack=market_line_at_pack,
        pack_as_of=pack_ts,
        market_as_of=market_as_of,
    )
    return {
        "kei_situation_flags": flags,
        "market_line": _f(market_line),
        "market_as_of": str(market_as_of or "") or None,
        "info_overlap": overlap,
        "pack_as_of": str(pack_ts or "") or None,
        "market_line_at_pack": _f(market_line_at_pack),
        "kei_spread_delta": _f(kei_delta),
        "version": INFO_OVERLAP_VERSION,
        # Explicit: market_ahead never adds KEI points.
        "market_ahead_adds_kei_juice": False,
    }


def attach_info_overlap_to_kei_log(
    kei_log: Mapping[str, Any],
    *,
    market_line: Any = None,
    market_line_at_pack: Any = None,
    market_as_of: Any = None,
    pack_as_of: Any = None,
) -> Dict[str, Any]:
    """Return a copy of kei_log with info_overlap card fields. Means unchanged."""
    out = dict(kei_log)
    card = build_info_overlap_card(
        kei_log=out,
        market_line=market_line,
        market_line_at_pack=market_line_at_pack,
        market_as_of=market_as_of,
        pack_as_of=pack_as_of or out.get("pack_as_of"),
    )
    out["kei_situation_flags"] = card["kei_situation_flags"]
    out["market_line"] = card["market_line"]
    out["market_as_of"] = card["market_as_of"]
    out["info_overlap"] = card["info_overlap"]
    out["info_overlap_card"] = card
    return out
