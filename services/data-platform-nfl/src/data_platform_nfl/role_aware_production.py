"""Role-aware player production shape (enterprise fix 2026-08-13).

Replaces the v1.23 ~1,380-yard RB magnet that:
- compressed Cook / Henry / Charbonnet / Swift / Bijan into a ~10-pt blob
- skipped low-rush-team RB1s (Gibbs, JT) because team_rush * 0.58 < 1,350
- treated "whoever currently has the most rush yards" as RB1

Team pass/rush totals stay conserved (within-team realloc only).
League rush pool stays whatever the incoming board summed to (64k after lift).
Dual-threat QB rush yards/TDs come from RB3 / backup leftovers, not RB1.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from data_platform_nfl.offensive_production_stack import (
    PRIOR_YEAR_ALPHA_VOLUME,
    _f,
    _norm_player_name,
    _team_rush_map,
    prior_alpha_lookup,
)

# Depth from published keys: DET-RB1-JahmyrGibbs / LA-WR1-PukaNacua
_KEY_DEPTH_RE = re.compile(
    r"^[A-Z]{2,3}-(QB|RB|WR|TE|K|DST)(\d+)-",
    re.IGNORECASE,
)

# Feature vs committee (share of team RB rush, excluding QB).
FEATURE_RB_SHARES = (0.66, 0.24, 0.10)
COMMITTEE_RB_SHARES = (0.54, 0.38, 0.08)
COMMITTEE_RB2_MIN = 0.28
COMMITTEE_GAP_MAX = 0.14

# Non-alpha RB1 cannot be pinned to the old 1,380 magnet.
# Plurality, not a 1,400-yard default — SoT RB1 without a rush prior.
NON_ALPHA_RB_SHARES = (0.46, 0.36, 0.18)
NON_ALPHA_RB1_SHARE_CAP = NON_ALPHA_RB_SHARES[0]

# Three-down back receiving (share of team pass yards).
THREE_DOWN_RB_TGT = 0.13

# Dual-threat QB share of *team* rush (yards / TDs). Taken from RB3+ first.
QB_RUSH_TIER_BY_NAME: Dict[str, str] = {
    "lamarjackson": "designed_run_heavy",
    "jalenhurts": "designed_run_heavy",
    "joshallen": "dual_threat",
    "jaydendaniels": "dual_threat",
    "kylermurray": "dual_threat",
    "calebwilliams": "dual_threat",
    "bonix": "dual_threat",
    "drakemaye": "dual_threat",
}
QB_RUSH_SHARE = {
    "designed_run_heavy": 0.17,
    "dual_threat": 0.12,
    "light_scramble": 0.07,
    "pocket": 0.04,
}
QB_RUSH_TD_SHARE = {
    "designed_run_heavy": 0.38,
    "dual_threat": 0.32,
    "light_scramble": 0.10,
    "pocket": 0.05,
}

# Feature RB1 share of team *RB* rush TDs (QB dual-threat carved out first).
FEATURE_RB1_TD_SHARE = 0.72
COMMITTEE_RB1_TD_SHARE = 0.55
# Depth-chart RB1 without a rush prior cannot keep Henry-class TDs.
NON_ALPHA_RB1_TD_SHARE = 0.38


def depth_from_player_key(player_key: str) -> Optional[int]:
    match = _KEY_DEPTH_RE.match(str(player_key or ""))
    if not match:
        return None
    try:
        return int(match.group(2))
    except (TypeError, ValueError):
        return None


def _is_rush_alpha(player_name: str) -> bool:
    prior = prior_alpha_lookup(player_name) or PRIOR_YEAR_ALPHA_VOLUME.get(
        _norm_player_name(player_name)
    )
    if not prior:
        return False
    if prior.get("top5_rush") or prior.get("three_down"):
        return True
    return float(prior.get("rush_yards") or 0.0) >= 1_200.0


def _is_rec_alpha(player_name: str) -> bool:
    prior = prior_alpha_lookup(player_name)
    if not prior:
        return False
    return bool(
        prior.get("top5_rec")
        or prior.get("top5_tgt")
        or float(prior.get("rec_yards") or 0.0) >= 1_150.0
    )


def _is_three_down(player_name: str) -> bool:
    prior = prior_alpha_lookup(player_name) or {}
    if prior.get("three_down"):
        return True
    # Gibbs / CMC-class: high rush prior + pass-game role.
    return _is_rush_alpha(player_name) and float(prior.get("rec_yards") or 0.0) >= 400.0


def _qb_tier(player_name: str) -> str:
    return QB_RUSH_TIER_BY_NAME.get(_norm_player_name(player_name), "pocket")


def _sort_rbs(rbs: Sequence[MutableMapping[str, Any]]) -> List[MutableMapping[str, Any]]:
    def key(row: Mapping[str, Any]) -> Tuple[int, float, str]:
        depth = depth_from_player_key(str(row.get("player_key") or "")) or 99
        rush = -_f(row, "rush_yards_total", "rush_yards_mean")
        return (depth, rush, str(row.get("player_name") or ""))

    return sorted(rbs, key=key)


def _is_committee(rbs: Sequence[Mapping[str, Any]]) -> bool:
    if len(rbs) < 2:
        return False
    pool = sum(_f(r, "rush_yards_total", "rush_yards_mean") for r in rbs) or 1.0
    ordered = _sort_rbs(list(rbs))
    s1 = _f(ordered[0], "rush_yards_total", "rush_yards_mean") / pool
    s2 = _f(ordered[1], "rush_yards_total", "rush_yards_mean") / pool
    return s2 >= COMMITTEE_RB2_MIN and (s1 - s2) <= COMMITTEE_GAP_MAX


def apply_role_aware_player_shape(
    rows: Sequence[Mapping[str, Any]],
    *,
    teams: Optional[Sequence[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Reallocate rush/rec/TDs inside each team by depth role + talent.

    Does not reshuffle locked team pass yards. Conserves each team's rush
    total and the league rush pool (when ``teams`` is None). Pass ``teams``
    to reshape only touched franchises after a SoT identity move.
    """
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    team_rush_before = _team_rush_map(work)
    league_before = sum(team_rush_before.values())
    notes: List[str] = []
    only = {str(t).strip().upper() for t in teams} if teams else None

    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in work:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    for team, team_rows in by_team.items():
        if only is not None and str(team).strip().upper() not in only:
            continue
        team_rush = float(team_rush_before.get(team, 0.0))
        if team_rush <= 1.0:
            continue
        rbs = [r for r in team_rows if str(r.get("position") or "").upper() == "RB"]
        qbs = [r for r in team_rows if str(r.get("position") or "").upper() == "QB"]
        skill = [
            r
            for r in team_rows
            if str(r.get("position") or "").upper() in {"WR", "TE", "RB"}
        ]
        if not rbs:
            continue

        qb1 = min(
            qbs,
            key=lambda r: depth_from_player_key(str(r.get("player_key") or "")) or 99,
            default=None,
        )
        tier = _qb_tier(str(qb1.get("player_name") or "")) if qb1 else "pocket"
        qb_rush_share = QB_RUSH_SHARE.get(tier, 0.04)
        qb_td_share = QB_RUSH_TD_SHARE.get(tier, 0.04)

        # Carve dual-threat / designed-run QB rush from the team pool first.
        qb_rush_target = team_rush * qb_rush_share if qb1 else 0.0
        rb_pool = max(team_rush - qb_rush_target, 0.0)
        ordered = _sort_rbs(rbs)
        committee = _is_committee(ordered)
        shares = COMMITTEE_RB_SHARES if committee else FEATURE_RB_SHARES
        rb1_name = str(ordered[0].get("player_name") or "")
        alpha = _is_rush_alpha(rb1_name)
        if not alpha and not committee:
            shares = NON_ALPHA_RB_SHARES

        # Pad / trim share tuple to n RBs.
        n = len(ordered)
        use = list(shares[:n])
        if len(use) < n:
            rem = max(0.0, 1.0 - sum(use))
            extra = rem / (n - len(use))
            use.extend([extra] * (n - len(use)))
        total_share = sum(use) or 1.0
        use = [s / total_share for s in use]

        three_down = _is_three_down(rb1_name)
        rush_cap = 0.78 if three_down else 0.72
        if alpha:
            # Bell-cow: give RB1 the max of role share vs 85% of prior, capped.
            prior = prior_alpha_lookup(rb1_name) or {}
            prior_rush = float(prior.get("rush_yards") or 0.0)
            prior_share = (
                min(rush_cap, prior_rush * 0.88 / rb_pool) if prior_rush and rb_pool else 0.0
            )
            use[0] = min(rush_cap, max(use[0], prior_share))
            rem = max(0.0, 1.0 - use[0])
            tail = sum(use[1:]) or 1.0
            for i in range(1, n):
                use[i] = rem * (use[i] / tail)

        for row, share in zip(ordered, use):
            old = _f(row, "rush_yards_total", "rush_yards_mean")
            row["rush_yards_total"] = rb_pool * share
            if abs(row["rush_yards_total"] - old) >= 8:
                notes.append(
                    f"{row.get('player_name')}:{team}:rush {old:.0f}→{row['rush_yards_total']:.0f}"
                )

        # Assign QB rush (QB2/3 keep a tiny residual, rest to QB1).
        if qb1 is not None:
            others = [q for q in qbs if q is not qb1]
            leftover = team_rush * 0.015
            qb1["rush_yards_total"] = max(qb_rush_target - leftover, 0.0)
            if others:
                each = leftover / len(others)
                for q in others:
                    q["rush_yards_total"] = each
            else:
                qb1["rush_yards_total"] = qb_rush_target

        # Exact team rush conservation (WR/TE rush untouched → scale RB+QB).
        movers = rbs + qbs
        cur = sum(_f(r, "rush_yards_total") for r in movers) or 1.0
        # Incoming team total also includes WR/TE rush; keep those, scale movers
        # so team matches team_rush.
        wr_te_rush = sum(
            _f(r, "rush_yards_total")
            for r in team_rows
            if str(r.get("position") or "").upper() in {"WR", "TE"}
        )
        need = team_rush - wr_te_rush
        if need > 1e-9:
            scale = need / cur
            for r in movers:
                r["rush_yards_total"] = _f(r, "rush_yards_total") * scale

        # Rush TDs: carve QB dual-threat, then concentrate remainder on RB1.
        team_rush_td = sum(_f(r, "rush_tds_total", "rush_tds_mean") for r in team_rows)
        if team_rush_td > 1e-9:
            qb_td = team_rush_td * qb_td_share if qb1 else 0.0
            rb_td_pool = max(team_rush_td - qb_td, 0.0)
            rb1_td_share = COMMITTEE_RB1_TD_SHARE if committee else FEATURE_RB1_TD_SHARE
            if not alpha:
                rb1_td_share = min(rb1_td_share, NON_ALPHA_RB1_TD_SHARE)
            if qb1 is not None:
                qb1["rush_tds_total"] = qb_td
                for q in qbs:
                    if q is not qb1:
                        q["rush_tds_total"] = 0.0
            if ordered:
                ordered[0]["rush_tds_total"] = rb_td_pool * rb1_td_share
                tail_td = rb_td_pool * (1.0 - rb1_td_share)
                tail_rush = sum(_f(r, "rush_yards_total") for r in ordered[1:]) or 1.0
                for r in ordered[1:]:
                    r["rush_tds_total"] = tail_td * (
                        _f(r, "rush_yards_total") / tail_rush
                    )

        # Three-down receiving: pin Gibbs/CMC-class to a real target share.
        team_pass = sum(
            _f(r, "pass_yards_total", "pass_yards_mean")
            for r in team_rows
            if str(r.get("position") or "").upper() == "QB"
        )
        if ordered and _is_three_down(rb1_name) and team_pass > 1.0:
            rb1 = ordered[0]
            want = team_pass * THREE_DOWN_RB_TGT
            cur_rec = _f(rb1, "receiving_yards_total", "rec_yards_mean")
            if want > cur_rec + 15:
                delta = want - cur_rec
                donors = [
                    r
                    for r in skill
                    if r is not rb1
                    and str(r.get("position") or "").upper() in {"WR", "TE"}
                    and (depth_from_player_key(str(r.get("player_key") or "")) or 99)
                    >= 2
                    and _f(r, "receiving_yards_total") > 80
                    and not _is_rec_alpha(str(r.get("player_name") or ""))
                ]
                donor_sum = sum(_f(r, "receiving_yards_total") for r in donors)
                if donor_sum > 1.0:
                    take = min(delta, donor_sum * 0.35)
                    for r in donors:
                        part = take * (_f(r, "receiving_yards_total") / donor_sum)
                        r["receiving_yards_total"] = max(
                            0.0, _f(r, "receiving_yards_total") - part
                        )
                        recs = _f(r, "receptions_total")
                        if recs > 0 and _f(r, "receiving_yards_total") + part > 0:
                            r["receptions_total"] = recs * (
                                _f(r, "receiving_yards_total")
                                / (_f(r, "receiving_yards_total") + part)
                            )
                    rb1["receiving_yards_total"] = cur_rec + take
                    ypr = 8.2
                    rb1["receptions_total"] = rb1["receiving_yards_total"] / ypr
                    notes.append(
                        f"{rb1_name}:{team}:rec {cur_rec:.0f}→{rb1['receiving_yards_total']:.0f}"
                    )

        # WR alpha pin: top5 prior WRs get at least 30% of team pass (cap 40%).
        wr_alphas = [
            r
            for r in team_rows
            if str(r.get("position") or "").upper() == "WR"
            and _is_rec_alpha(str(r.get("player_name") or ""))
        ]
        if wr_alphas and team_pass > 1.0:
            wr1 = max(
                wr_alphas, key=lambda r: _f(r, "receiving_yards_total", "rec_yards_mean")
            )
            want = min(team_pass * 0.34, max(1_450.0, team_pass * 0.30))
            cur_rec = _f(wr1, "receiving_yards_total")
            if want > cur_rec + 20:
                delta = want - cur_rec
                donors = [
                    r
                    for r in skill
                    if r is not wr1
                    and not _is_rec_alpha(str(r.get("player_name") or ""))
                    and _f(r, "receiving_yards_total") > 100
                    and (
                        str(r.get("position") or "").upper() != "RB"
                        or (
                            depth_from_player_key(str(r.get("player_key") or "")) or 99
                        )
                        >= 2
                    )
                ]
                donor_sum = sum(_f(r, "receiving_yards_total") for r in donors)
                if donor_sum > 1.0:
                    take = min(delta, donor_sum * 0.40)
                    for r in donors:
                        part = take * (_f(r, "receiving_yards_total") / donor_sum)
                        r["receiving_yards_total"] = max(
                            0.0, _f(r, "receiving_yards_total") - part
                        )
                    wr1["receiving_yards_total"] = cur_rec + take
                    wr1["receptions_total"] = wr1["receiving_yards_total"] / 11.8
                    notes.append(
                        f"{wr1.get('player_name')}:{team}:wr_alpha "
                        f"{cur_rec:.0f}→{wr1['receiving_yards_total']:.0f}"
                    )

        # Rec TDs follow receiving yards within team (pass TDs stay on QBs).
        rec_td_pool = sum(
            _f(r, "rec_tds_total", "rec_tds_mean")
            for r in skill
        )
        rec_yd_sum = sum(_f(r, "receiving_yards_total") for r in skill) or 1.0
        if rec_td_pool > 1e-9:
            for r in skill:
                r["rec_tds_total"] = rec_td_pool * (
                    _f(r, "receiving_yards_total") / rec_yd_sum
                )

        for r in team_rows:
            if team_rush > 1e-9 and str(r.get("position") or "").upper() in {
                "RB",
                "QB",
            }:
                r["carry_share"] = round(_f(r, "rush_yards_total") / team_rush, 4)

    league_after = sum(_team_rush_map(work).values())
    if only is None and abs(league_after - league_before) > 0.5 and league_after > 1e-9:
        scale = league_before / league_after
        for r in work:
            r["rush_yards_total"] = _f(r, "rush_yards_total") * scale

    return work, {
        "applied": True,
        "method": "role_aware_player_shape_v1",
        "adjustments": notes[:60],
        "n_notes": len(notes),
        "rush_pool": round(sum(_team_rush_map(work).values()), 1),
    }


def _slug_name(name: str) -> str:
    return "".join(ch for ch in str(name) if ch.isalnum())


def _key_team(team: str) -> str:
    token = str(team or "").strip().upper()
    if token == "LAR":
        return "LA"
    return token


def _csv_team_from_pack(pack_team: str, csv_teams: set[str]) -> str:
    token = str(pack_team or "").strip().upper()
    if token == "LA" and "LAR" in csv_teams:
        return "LAR"
    if token == "LAR":
        return "LAR"
    return token


def _rebuild_player_key(team: str, pos: str, depth: int, name: str) -> str:
    return f"{_key_team(team)}-{pos}{int(depth)}-{_slug_name(name)}"


def _scale_team_field(rows: Sequence[MutableMapping[str, Any]], field: str, target: float) -> None:
    cur = sum(_f(r, field) for r in rows)
    if cur <= 1e-9 or abs(cur - target) < 0.5:
        return
    factor = target / cur
    for row in rows:
        row[field] = _f(row, field) * factor


def align_skill_identities_to_depth_sot(
    rows: Sequence[Mapping[str, Any]],
    pack_rows: Sequence[Mapping[str, Any]],
    *,
    positions: Sequence[str] = ("RB", "WR", "TE"),
    only_names: Optional[Sequence[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Move skill identities onto the depth-pack team/slot; keep franchise budgets.

    Yards travel with the *team* they were simulated on, not with the name.
    After relabeling, each team's rush/rec/TD totals are scaled back to the
    pre-move snapshot, then the caller should run ``apply_role_aware_player_shape``.
    """
    work: List[Dict[str, Any]] = [dict(r) for r in rows]
    csv_teams = {str(r.get("team") or "").strip().upper() for r in work}
    pos_set = {p.upper() for p in positions}

    pack_by_name: Dict[Tuple[str, str], Tuple[str, int]] = {}
    allow = None
    if only_names:
        allow = {_norm_player_name(n) for n in only_names if n}
    for prow in pack_rows:
        pos = str(prow.get("position") or "").upper()
        if pos not in pos_set:
            continue
        name = _norm_player_name(str(prow.get("player_name") or ""))
        if not name:
            continue
        try:
            depth = int(prow.get("depth_order") or 99)
        except (TypeError, ValueError):
            continue
        team = _csv_team_from_pack(str(prow.get("team") or ""), csv_teams)
        pack_by_name[(name, pos)] = (team, depth)

    snap_rush = _team_rush_map(work)
    snap_rush_td: Dict[str, float] = {}
    snap_rec: Dict[str, float] = {}
    snap_rec_td: Dict[str, float] = {}
    snap_recp: Dict[str, float] = {}
    for row in work:
        team = str(row.get("team") or "")
        snap_rush_td[team] = snap_rush_td.get(team, 0.0) + _f(
            row, "rush_tds_total", "rush_tds_mean"
        )
        snap_rec[team] = snap_rec.get(team, 0.0) + _f(row, "receiving_yards_total")
        snap_rec_td[team] = snap_rec_td.get(team, 0.0) + _f(
            row, "rec_tds_total", "rec_tds_mean"
        )
        snap_recp[team] = snap_recp.get(team, 0.0) + _f(row, "receptions_total")

    moves: List[str] = []
    for row in work:
        pos = str(row.get("position") or "").upper()
        if pos not in pos_set:
            continue
        name = _norm_player_name(str(row.get("player_name") or ""))
        if allow is not None and name not in allow:
            continue
        hit = pack_by_name.get((name, pos))
        if not hit:
            continue
        pack_team, pack_depth = hit
        csv_team = str(row.get("team") or "").strip().upper()
        old_depth = depth_from_player_key(str(row.get("player_key") or "")) or 99
        if csv_team == pack_team.upper() and old_depth == pack_depth:
            continue
        old_team = str(row.get("team") or "")
        row["team"] = pack_team
        row["player_key"] = _rebuild_player_key(
            pack_team, pos, pack_depth, str(row.get("player_name") or "")
        )
        moves.append(
            f"{row.get('player_name')}:{old_team}-d{old_depth}→{pack_team}-d{pack_depth}"
        )

    used: Dict[str, int] = {}
    for row in work:
        key = str(row.get("player_key") or "")
        if not key:
            continue
        if key not in used:
            used[key] = 1
            continue
        pos = str(row.get("position") or "RB").upper()
        team = str(row.get("team") or "")
        depth = (depth_from_player_key(key) or 3) + used.get(key, 1)
        used[key] = used.get(key, 1) + 1
        row["player_key"] = _rebuild_player_key(
            team, pos, depth, str(row.get("player_name") or "")
        )

    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in work:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)
    all_teams = set(by_team) | set(snap_rush)
    for team in all_teams:
        team_rows = by_team.get(team) or []
        if not team_rows:
            continue
        _scale_team_field(team_rows, "rush_yards_total", float(snap_rush.get(team, 0.0)))
        _scale_team_field(team_rows, "rush_tds_total", float(snap_rush_td.get(team, 0.0)))
        _scale_team_field(team_rows, "receiving_yards_total", float(snap_rec.get(team, 0.0)))
        _scale_team_field(team_rows, "rec_tds_total", float(snap_rec_td.get(team, 0.0)))
        _scale_team_field(team_rows, "receptions_total", float(snap_recp.get(team, 0.0)))

    return work, {
        "applied": True,
        "method": "align_skill_identities_to_depth_sot",
        "moves": moves,
        "n_moves": len(moves),
        "rush_pool": round(sum(_team_rush_map(work).values()), 1),
    }
