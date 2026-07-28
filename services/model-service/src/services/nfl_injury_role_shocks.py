"""Same-week injury → role-share shocks for QB / RB / WR / TE rooms.

Enterprise failure mode: a designated starter stays OUT/DNP/IR on the injury
report while their trailing rush/target/snap share still projects full volume,
minting fake props and inflating team totals. This module:

1. Maps report + practice status → availability in [0, 1].
2. Zeroes (or heavily discounts) usage for players below a hard-out threshold.
3. Redistributes freed rush / target / QB starter share to healthy teammates
   in the same position pool, preserving team totals (~sum-to-1 rooms).

Pure functions; callers supply one team's rows for one week.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def availability_from_injury_statuses(
    report_status: Optional[str],
    practice_status: Optional[str] = None,
) -> float:
    """Blend report + practice into availability_confidence ∈ [0.05, 0.98]."""
    report = str(report_status or "").strip().lower()
    practice = str(practice_status or "").strip().lower()

    if report in {"out", "doubtful"} or "injured reserve" in report or report == "ir":
        report_av = 0.12 if report == "doubtful" else 0.08
    elif "questionable" in report:
        report_av = 0.52
    elif "probable" in report or "limited" in report:
        report_av = 0.82
    elif report in {"healthy", ""}:
        report_av = 0.95
    else:
        report_av = 0.88

    if "did not participate" in practice or practice == "dnp":
        practice_av = 0.15
    elif "limited" in practice:
        practice_av = 0.62
    elif "full" in practice:
        practice_av = 0.96
    else:
        practice_av = 0.90

    # Report status dominates; practice can only pull down hard.
    blended = (0.72 * report_av) + (0.28 * practice_av)
    if report_av <= 0.12:
        blended = min(blended, report_av + 0.04)
    if practice_av <= 0.15 and report_av <= 0.55:
        blended = min(blended, 0.22)
    return _clamp(blended, 0.05, 0.98)


HARD_OUT_AVAILABILITY = 0.28
"""Below this, player is treated as non-participant for volume allocation."""


def _pool_for_position(position: str) -> Optional[str]:
    pos = str(position or "").upper()
    if pos == "QB":
        return "QB"
    if pos in {"RB", "HB", "FB"}:
        return "RB"
    if pos == "WR":
        return "WR"
    if pos == "TE":
        return "TE"
    return None


def redistribute_team_usage_for_injuries(
    rows: Sequence[Mapping[str, Any]],
    *,
    hard_out_threshold: float = HARD_OUT_AVAILABILITY,
) -> Dict[str, Dict[str, float]]:
    """Return {player_id: {availability, rush_share, target_proxy, qb_starter_share, injury_shock}}.

    Input rows need: player_id, position, availability (or report/practice),
    and optionally rush_share / target_proxy / qb_starter_share.
    """
    prepared: List[Dict[str, Any]] = []
    for row in rows:
        pid = str(row.get("player_id") or "")
        if not pid:
            continue
        if "availability" in row and row.get("availability") is not None:
            avail = _clamp(float(row["availability"]), 0.05, 0.98)
        else:
            avail = availability_from_injury_statuses(
                row.get("report_status"),
                row.get("practice_status"),
            )
        prepared.append(
            {
                "player_id": pid,
                "position": str(row.get("position") or "").upper(),
                "availability": avail,
                "rush_share": max(0.0, float(row.get("rush_share") or 0.0)),
                "target_proxy": max(0.0, float(row.get("target_proxy") or 0.0)),
                "qb_starter_share": max(0.0, float(row.get("qb_starter_share") or 0.0)),
            }
        )

    out: Dict[str, Dict[str, float]] = {
        r["player_id"]: {
            "availability": float(r["availability"]),
            "rush_share": float(r["rush_share"]),
            "target_proxy": float(r["target_proxy"]),
            "qb_starter_share": float(r["qb_starter_share"]),
            "injury_shock": 0.0,
        }
        for r in prepared
    }

    for pool_name, share_key in (
        ("QB", "qb_starter_share"),
        ("RB", "rush_share"),
        ("WR", "target_proxy"),
        ("TE", "target_proxy"),
    ):
        pool = [r for r in prepared if _pool_for_position(r["position"]) == pool_name]
        if len(pool) < 2:
            continue
        hard_out = [r for r in pool if float(r["availability"]) < hard_out_threshold]
        healthy = [r for r in pool if float(r["availability"]) >= hard_out_threshold]
        if not hard_out or not healthy:
            continue

        freed = 0.0
        for r in hard_out:
            pid = r["player_id"]
            before = float(out[pid][share_key])
            # Keep a tiny residual so backups still have a nonzero line if they
            # sneak into a game; primary volume moves to healthy roommates.
            residual = before * 0.04
            freed += max(0.0, before - residual)
            out[pid][share_key] = residual
            out[pid]["injury_shock"] = max(out[pid]["injury_shock"], before - residual)

        healthy_weight = sum(max(0.05, float(r["availability"])) for r in healthy)
        if healthy_weight <= 0.0 or freed <= 0.0:
            continue
        for r in healthy:
            pid = r["player_id"]
            w = max(0.05, float(r["availability"])) / healthy_weight
            out[pid][share_key] = float(out[pid][share_key]) + (freed * w)

        # Renormalize QB / RB pools to ~1.0; WR/TE target shares need not sum to 1.
        if pool_name in {"QB", "RB"}:
            total = sum(float(out[r["player_id"]][share_key]) for r in pool)
            if total > 0.0:
                for r in pool:
                    pid = r["player_id"]
                    out[pid][share_key] = float(out[pid][share_key]) / total

    return out


def load_team_injury_availability(
    session: Any,
    *,
    season: int,
    week: int,
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Load {(team, player_id|player_name_key): injury fields} for a week."""
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT
              team,
              COALESCE(NULLIF(player_id, ''), player_key) AS player_id,
              player_name,
              player_key,
              report_status,
              practice_status
            FROM nfl_dp_injuries
            WHERE season = :season
              AND week = :week
            """
        ),
        {"season": int(season), "week": int(week)},
    ).fetchall()
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        team = str(row.team or "")
        avail = availability_from_injury_statuses(row.report_status, row.practice_status)
        payload = {
            "report_status": row.report_status,
            "practice_status": row.practice_status,
            "availability": avail,
            "player_name": row.player_name,
        }
        for key in (str(row.player_id or ""), str(row.player_key or ""), str(row.player_name or "")):
            if key:
                out[(team, key)] = payload
    return out
