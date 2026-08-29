"""NFL public-surface integrity helpers (fantasy / projections / survivor).

Invariants (product SoT):
1. Season pass TD leaders share yards↔TD rate (~115 yards / TD).
2. Season rec TD leaders share yards↔TD rate (~100 yards / TD).
3. Depth-pack IR/out → games_projected ≈ 0, volume zeroed, risk flags.
4. Survivor week win% overlays fair-lines KEI win% for the same matchup.
5. No PLAY tag when stake_eligible is false.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from src.services.nfl_snap_share_prior import is_out_row

# Shared yards↔TD rates (same constants as nfl_player_projection_engine).
PASS_TD_YARDS_PER = 115.0
REC_TD_YARDS_PER = 100.0
# Soft IR games floor (fractional availability can leave a sliver; hard outs → 0).
IR_GAMES_CAP = 0.0

_VOLUME_KEYS = (
    "pass_yards_total",
    "rush_yards_total",
    "receiving_yards_total",
    "receptions_total",
    "pass_tds_total",
    "rush_tds_total",
    "rec_tds_total",
    "pass_yards_floor",
    "rush_yards_floor",
    "receiving_yards_floor",
    "receptions_floor",
    "pass_yards_ceiling",
    "rush_yards_ceiling",
    "receiving_yards_ceiling",
    "receptions_ceiling",
    "total_points",
    "floor_points",
    "median_points",
    "ceiling_points",
    "replacement_points",
    "value_over_replacement",
)

# Season-engine / CSV alternate keys
_VOLUME_KEY_ALIASES = {
    "pass_yards": "pass_yards_total",
    "rush_yards": "rush_yards_total",
    "rec_yards": "receiving_yards_total",
    "receiving_yards": "receiving_yards_total",
    "pass_tds": "pass_tds_total",
    "rush_tds": "rush_tds_total",
    "rec_tds": "rec_tds_total",
    "games_projected": "games_projected",
    "games_mean": "games_projected",
}


def _norm_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "", str(name or "").lower())
    return re.sub(r"(jr|sr|ii|iii|iv)$", "", cleaned)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def pass_tds_from_yards(pass_yards: float) -> float:
    """Yards-coupled pass TD mean (season or per-game — same rate)."""
    return max(0.0, _safe_float(pass_yards) / PASS_TD_YARDS_PER)


def rec_tds_from_yards(receiving_yards: float) -> float:
    """Yards-coupled receiving TD mean."""
    return max(0.0, _safe_float(receiving_yards) / REC_TD_YARDS_PER)


def recouple_player_tds_to_yards(row: MutableMapping[str, Any]) -> Dict[str, Any]:
    """Rewrite pass/rec TDs from yards so every surface shares one rate.

    Does not invent yards. Leaves rush TDs untouched. Returns audit dict.
    """
    audit: Dict[str, Any] = {"recoupled": False}

    # Prefer *_total keys; fall back to season-engine short names.
    pass_yd = row.get("pass_yards_total")
    if pass_yd is None:
        pass_yd = row.get("pass_yards")
    rec_yd = row.get("receiving_yards_total")
    if rec_yd is None:
        rec_yd = row.get("rec_yards", row.get("receiving_yards"))

    pass_yd_f = _safe_float(pass_yd)
    rec_yd_f = _safe_float(rec_yd)

    if pass_yd_f > 1.0:
        new_pass = round(pass_tds_from_yards(pass_yd_f), 4)
        for key in ("pass_tds_total", "pass_tds"):
            if key in row or key == "pass_tds_total":
                row[key] = new_pass
        audit["pass_tds"] = new_pass
        audit["recoupled"] = True

    if rec_yd_f > 1.0:
        new_rec = round(rec_tds_from_yards(rec_yd_f), 4)
        for key in ("rec_tds_total", "rec_tds"):
            if key in row or key == "rec_tds_total":
                row[key] = new_rec
        audit["rec_tds"] = new_rec
        audit["recoupled"] = True
    elif rec_yd_f <= 1.0 and _safe_float(row.get("rec_tds_total", row.get("rec_tds"))) > 0:
        # No yards ⇒ no receiving TDs (illegal 0-yard TD ghosts).
        for key in ("rec_tds_total", "rec_tds"):
            if key in row:
                row[key] = 0.0
        audit["rec_tds"] = 0.0
        audit["recoupled"] = True

    return audit


def build_pack_injury_index(
    pack_rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    """Index pack rows by (team, player_id) and (team, normalized_name)."""
    index: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for row in pack_rows:
        if not isinstance(row, Mapping):
            continue
        team = str(row.get("team") or "").strip().upper()
        if not team:
            continue
        pid = str(row.get("player_id") or "").strip()
        name = _norm_name(str(row.get("player_name") or ""))
        if pid:
            index[(team, pid)] = row
        if name:
            index[(team, name)] = row
    return index


def lookup_pack_row(
    index: Mapping[Tuple[str, str], Mapping[str, Any]],
    *,
    team: str,
    player_id: Optional[str] = None,
    player_name: Optional[str] = None,
) -> Optional[Mapping[str, Any]]:
    team_n = str(team or "").strip().upper()
    if not team_n:
        return None
    if player_id:
        hit = index.get((team_n, str(player_id).strip()))
        if hit is not None:
            return hit
    if player_name:
        hit = index.get((team_n, _norm_name(player_name)))
        if hit is not None:
            return hit
    return None


def zero_player_volume_for_injury(
    row: MutableMapping[str, Any],
    *,
    injury_status: str,
    games_cap: float = IR_GAMES_CAP,
) -> Dict[str, Any]:
    """Zero games + volume for pack IR/out; stamp risk metadata."""
    status = str(injury_status or "").strip().lower()
    row["games_projected"] = float(games_cap)
    if "games_mean" in row:
        row["games_mean"] = float(games_cap)
    for key in _VOLUME_KEYS:
        if key in row:
            row[key] = 0.0
    # Season-engine short names
    for short, total in _VOLUME_KEY_ALIASES.items():
        if short in row and short != "games_projected" and short != "games_mean":
            row[short] = 0.0
        if total in row and total.startswith(("pass_", "rush_", "rec_", "receiving_")):
            row[total] = 0.0

    flags = list(row.get("risk_flags") or [])
    flag = {
        "kind": "availability",
        "label": status.upper() if status else "OUT",
        "detail": f"Depth pack injury_status={status or 'out'} — season volume zeroed.",
    }
    if not any(isinstance(f, Mapping) and f.get("kind") == "availability" for f in flags):
        flags.insert(0, flag)
    row["risk_flags"] = flags[:4]
    row["pack_injury_status"] = status or "out"
    payload = row.get("projection_payload")
    if isinstance(payload, dict):
        payload = dict(payload)
        payload["pack_injury_status"] = status or "out"
        payload["risk_flags"] = row["risk_flags"]
        row["projection_payload"] = payload
    return {"zeroed": True, "injury_status": status or "out", "games_projected": games_cap}


def apply_pack_injury_to_fantasy_rows(
    rows: Sequence[MutableMapping[str, Any]],
    pack_rows: Sequence[Mapping[str, Any]],
    *,
    recouple_tds: bool = True,
) -> Dict[str, Any]:
    """Apply depth-pack IR/out to fantasy/projection rows; optional TD recouple.

    Mutates rows in place. Returns audit summary.
    """
    index = build_pack_injury_index(pack_rows)
    zeroed: List[str] = []
    recoupled = 0
    for row in rows:
        team = str(row.get("team") or "")
        pid = str(row.get("player_id") or "") or None
        name = str(row.get("player_name") or "") or None
        pack = lookup_pack_row(index, team=team, player_id=pid, player_name=name)
        if pack is not None and is_out_row(pack):
            status = str(pack.get("injury_status") or "out")
            zero_player_volume_for_injury(row, injury_status=status)
            zeroed.append(name or pid or "?")
            continue
        if recouple_tds:
            audit = recouple_player_tds_to_yards(row)
            if audit.get("recoupled"):
                recoupled += 1
    return {
        "pack_injury_zeroed": len(zeroed),
        "zeroed_players": zeroed[:20],
        "tds_recoupled": recoupled,
        "method": "pack_injury_fantasy_overlay_v1",
    }


def overlay_survivor_kei_win_probs(
    survivor_payload: MutableMapping[str, Any],
    kei_by_team: Mapping[str, float],
) -> Dict[str, Any]:
    """Replace survivor win_prob/win_rate with KEI fair-lines win% by team.

    ``kei_by_team`` maps team abbr → P(team wins this week). Rows for teams
    without a KEI entry are left unchanged (honest gap).
    """
    updated = 0
    missing: List[str] = []

    def _apply(rows: Any) -> None:
        nonlocal updated
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, MutableMapping):
                continue
            team = str(row.get("team") or "").strip().upper()
            if not team:
                continue
            if team not in kei_by_team:
                missing.append(team)
                continue
            wp = float(kei_by_team[team])
            row["win_prob"] = round(wp, 4)
            row["win_rate"] = round(wp, 4)
            row["win_prob_source"] = "kei_fair_lines"
            # Preserve sim count diagnostics but mark override.
            row["sim_win_rate_before_kei"] = row.get("wins_in_sims")
            updated += 1

    _apply(survivor_payload.get("ranked_picks"))
    _apply(survivor_payload.get("all_teams_week"))
    # Planner open-week blobs
    for key in ("open_weeks", "weeks", "recommendations"):
        blob = survivor_payload.get(key)
        if isinstance(blob, list):
            for item in blob:
                if isinstance(item, Mapping):
                    _apply(item.get("ranked_picks") or item.get("picks") or item.get("teams"))

    return {
        "overlay": "kei_fair_lines",
        "teams_updated": updated,
        "teams_missing_kei": sorted(set(missing))[:32],
    }


def build_kei_win_prob_map_from_fair_lines(
    lines: Sequence[Mapping[str, Any]],
    *,
    week: Optional[int] = None,
) -> Dict[str, float]:
    """Build {team_abbr: win_prob} from fair-lines rows for a target week."""
    out: Dict[str, float] = {}
    for line in lines:
        if not isinstance(line, Mapping):
            continue
        if week is not None:
            try:
                if int(line.get("week") or 0) != int(week):
                    continue
            except (TypeError, ValueError):
                continue
        home = str(line.get("home_abbr") or line.get("home_team") or "").strip().upper()
        away = str(line.get("away_abbr") or line.get("away_team") or "").strip().upper()
        if home in {"LA", "STL"}:
            home = "LAR"
        if away in {"LA", "STL"}:
            away = "LAR"
        # Prefer handicap/KEI fields; fall back to home_win_prob.
        home_wp = line.get("handicap_home_win_prob")
        if home_wp is None:
            home_wp = line.get("home_win_prob")
        away_wp = line.get("handicap_away_win_prob")
        if away_wp is None:
            away_wp = line.get("away_win_prob")
        if home_wp is None and away_wp is None:
            continue
        home_f = _safe_float(home_wp) if home_wp is not None else None
        away_f = _safe_float(away_wp) if away_wp is not None else None
        if home_f is None and away_f is not None:
            home_f = max(0.0, min(1.0, 1.0 - away_f))
        if away_f is None and home_f is not None:
            away_f = max(0.0, min(1.0, 1.0 - home_f))
        # Canonicalize long names if abbr missing — caller should pass abbrs.
        if len(home) <= 3 and home_f is not None:
            out[home] = float(home_f)
        if len(away) <= 3 and away_f is not None:
            out[away] = float(away_f)
    return out


def enforce_no_play_without_stake(
    tag: Optional[str],
    stake_eligible: bool,
) -> Tuple[Optional[str], bool, str]:
    """Invariant 5: never emit PLAY when stake_eligible is false."""
    if str(tag or "").upper() == "PLAY" and not stake_eligible:
        return "WATCH", False, "play_requires_stake_eligible"
    return tag, bool(stake_eligible), "ok"
