#!/usr/bin/env python3
"""Phase 2.6C — holdout integrity closure + storage split plan (no scoring)."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "apps" / "web"), str(REPO / "apps" / "web" / "src")]

from ncaam_espn_schedule_map import map_espn_event_sides  # noqa: E402
from ncaam_identity import (  # noqa: E402
    _aliases,
    _omit,
    fold_ncaam_alias,
    odds_name_to_team_norm,
    resolve_team_id,
)
from ncaam_lab.holdout_2425.constants import (  # noqa: E402
    CANONICAL_PACK_PATH,
    HOLDOUT_ID,
    KENPOM_SNAPSHOT_DIR,
    ODDS_PARQUET,
    OUT_ROOT,
    PACKAGE_VERSION,
    RAW_ESPN_DIR,
    WINDOW_END,
    WINDOW_START,
)
from ncaam_lab.holdout_2425.io_util import write_json  # noqa: E402
from ncaam_lab.holdout_2425.phase26c.thresholds import (  # noqa: E402
    ABS_COVERAGE_GAP_PP_MATERIAL,
    ADJM_GAP_BINS,
    ADJT_BINS,
    ALLOWED_CONCLUSIONS,
    ESPN_REJECT_TAXONOMY,
    EXPECTED_DUPLICATE_CONFLICT_COUNT,
    EXPECTED_ESPN_REJECT_COUNT,
    EXPECTED_TIMESTAMP_DISHONEST_COUNT,
    POWER_CONF_SHORT,
    SMD_CLEARLY_MATERIAL,
    SMD_MATERIAL,
    SPREAD_MAG_BINS,
    SYNTHETIC_CLOSE_HOUR_UTC,
    THRESHOLD_VERSION,
    TIP_HOUR_BANDS_UTC,
    frozen_threshold_receipt,
)

COVERAGE_26C = OUT_ROOT / "coverage_26c"
DOCS_DIR = REPO / "docs" / "ops" / "ncaam"
MAPPING_RULE_VERSION = "espn_b7_map_v1_phase26c"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def bin_label(
    value: Optional[float],
    bins: Sequence[Tuple[str, Optional[float], Optional[float]]],
) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "missing"
    for name, lo, hi in bins:
        if lo is not None and value < lo:
            continue
        if hi is not None and value >= hi:
            continue
        return name
    return "missing"


def tip_band(hour: Optional[int]) -> str:
    if hour is None:
        return "missing"
    for name, rng in TIP_HOUR_BANDS_UTC:
        if hour in rng:
            return name
    return "missing"


def smd(a: List[float], b: List[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    pooled = math.sqrt((va + vb) / 2.0)
    if pooled == 0:
        return 0.0
    return (ma - mb) / pooled


def load_kenpom_di_universe() -> Set[str]:
    snaps = sorted(KENPOM_SNAPSHOT_DIR.glob("kenpom_2024-1*.parquet")) + sorted(
        KENPOM_SNAPSHOT_DIR.glob("kenpom_2025-*.parquet")
    )
    di: Set[str] = set()
    if not snaps:
        return di
    for snap in (snaps[0], snaps[len(snaps) // 2], snaps[-1]):
        df = pd.read_parquet(snap, columns=["team_norm"])
        di |= {str(x) for x in df["team_norm"].tolist()}
    return di


def load_kenpom_by_day() -> Dict[str, Dict[str, Dict[str, Any]]]:
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    snaps = sorted(KENPOM_SNAPSHOT_DIR.glob("kenpom_2024-1*.parquet")) + sorted(
        KENPOM_SNAPSHOT_DIR.glob("kenpom_2025-*.parquet")
    )
    for snap in snaps:
        df = pd.read_parquet(
            snap, columns=["team_norm", "adjem", "adjtempo", "confshort", "snapshot_date"]
        )
        day = str(df["snapshot_date"].iloc[0])[:10]
        bucket: Dict[str, Dict[str, Any]] = {}
        for row in df.itertuples(index=False):
            bucket[str(row.team_norm)] = {
                "adjem": float(row.adjem) if pd.notna(row.adjem) else None,
                "adjt": float(row.adjtempo) if pd.notna(row.adjtempo) else None,
                "conf": str(row.confshort),
            }
        out[day] = bucket
    return out


def load_spread_by_event() -> Dict[str, float]:
    df = pd.read_parquet(
        ODDS_PARQUET, columns=["event_id", "commence_time", "close_spread_home"]
    )
    df["d"] = pd.to_datetime(df["commence_time"], utc=True)
    sub = df[(df["d"] >= "2024-11-01") & (df["d"] <= "2025-04-15")].copy()
    sub = sub.dropna(subset=["close_spread_home"])
    g = sub.groupby("event_id")["close_spread_home"].median()
    return {str(k): float(abs(v)) for k, v in g.items()}


def classify_espn_reject(
    *,
    espn_id: str,
    day: str,
    tip: str,
    status: str,
    home_c: Optional[Dict[str, Any]],
    away_c: Optional[Dict[str, Any]],
    mapped: Dict[str, Any],
    di_universe: Set[str],
    digest: str,
    rel: str,
    seen: Set[str],
) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "espn_game_id": espn_id,
        "event_date": day,
        "tip": tip,
        "raw_home_name": ((home_c or {}).get("team") or {}).get("displayName"),
        "raw_away_name": ((away_c or {}).get("team") or {}).get("displayName"),
        "raw_home_espn_id": str(((home_c or {}).get("team") or {}).get("id") or ""),
        "raw_away_espn_id": str(((away_c or {}).get("team") or {}).get("id") or ""),
        "attempted_home_norm": None,
        "attempted_away_norm": None,
        "mapped_home_b7": mapped.get("home"),
        "mapped_away_b7": mapped.get("away"),
        "source_payload_path": rel,
        "source_payload_sha256": digest,
        "mapping_rule_version": MAPPING_RULE_VERSION,
        "scores_omitted": True,
    }
    if home_c is None or away_c is None:
        return {
            **base,
            "classification": "malformed_source_record",
            "deterministic_evidence": {"detail": "missing_home_or_away"},
        }
    if espn_id and espn_id in seen:
        return {
            **base,
            "classification": "duplicate_schedule_event",
            "deterministic_evidence": {"detail": "duplicate_espn_game_id"},
        }
    if status in {"STATUS_CANCELED", "STATUS_POSTPONED", "STATUS_SCHEDULED"}:
        return {
            **base,
            "classification": "cancelled_or_non_final",
            "deterministic_evidence": {"espn_status": status},
        }
    notes = home_c.get("notes") or away_c.get("notes") or []
    note_text = " ".join(str(n.get("headline") or n.get("text") or n) for n in notes).lower()
    if any(t in note_text for t in ("exhibition", "scrimmage", "exh.")):
        return {
            **base,
            "classification": "exhibition_or_scrimmage",
            "deterministic_evidence": {"notes": note_text},
        }

    ht, at = home_c.get("team") or {}, away_c.get("team") or {}
    home_name = str(ht.get("displayName") or "")
    away_name = str(at.get("displayName") or "")
    home_attempt = odds_name_to_team_norm(home_name)
    away_attempt = odds_name_to_team_norm(away_name)
    base["attempted_home_norm"] = home_attempt
    base["attempted_away_norm"] = away_attempt

    for side, name, attempt in (
        ("home", home_name, home_attempt),
        ("away", away_name, away_attempt),
    ):
        if "(" in name and ")" in name and attempt and attempt in di_universe:
            if resolve_team_id(name) is None:
                return {
                    **base,
                    "classification": "ambiguous_identity",
                    "deterministic_evidence": {
                        "side": side,
                        "raw_name": name,
                        "aggressive_norm_would_be": attempt,
                        "detail": "parenthetical_campus_blocks_di_homonym_collapse",
                    },
                }

    if bool(mapped.get("home")) ^ bool(mapped.get("away")):
        if mapped.get("home"):
            uname, uattempt, uid = away_name, away_attempt, base["raw_away_espn_id"]
            mapped_b7 = mapped.get("home")
        else:
            uname, uattempt, uid = home_name, home_attempt, base["raw_home_espn_id"]
            mapped_b7 = mapped.get("away")
        in_di = bool(uattempt and uattempt in di_universe)
        direct = resolve_team_id(uname)
        if direct is None and not in_di:
            return {
                **base,
                "classification": "confirmed_non_di_opponent",
                "deterministic_evidence": {
                    "mapped_di_side_b7": mapped_b7,
                    "unmapped_raw_name": uname,
                    "unmapped_espn_team_id": uid,
                    "odds_name_to_team_norm": uattempt,
                    "in_kenpom_2024_25_di_universe": False,
                    "governed_reference": "kenpom_2024_25_di_roster_union",
                },
            }
        if in_di and direct is None:
            return {
                **base,
                "classification": "b7_alias_missing",
                "deterministic_evidence": {
                    "unmapped_raw_name": uname,
                    "kenpom_team_norm": uattempt,
                },
            }
        return {
            **base,
            "classification": "b7_team_missing",
            "deterministic_evidence": {"unmapped_raw_name": uname},
        }

    if mapped.get("reason") == "same_side":
        return {
            **base,
            "classification": "ambiguous_identity",
            "deterministic_evidence": {"map_reason": "same_side"},
        }
    if not mapped.get("home") and not mapped.get("away"):
        return {
            **base,
            "classification": "b7_team_missing",
            "deterministic_evidence": {"detail": "both_sides_unmapped"},
        }
    return {
        **base,
        "classification": "other_explicit_reason",
        "deterministic_evidence": {"map_reason": mapped.get("reason")},
    }


def build_espn_reject_ledger(di_universe: Set[str]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    mapped_count = 0
    for path in sorted(RAW_ESPN_DIR.glob("espn_scoreboard_*.json")):
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        env = json.loads(raw.decode("utf-8"))
        day = str(
            env.get("day")
            or path.name.replace("espn_scoreboard_", "").replace(".json", "")
        )
        try:
            d = date.fromisoformat(day)
            if d < WINDOW_START or d > WINDOW_END:
                continue
        except ValueError:
            pass
        rel = str(path.relative_to(OUT_ROOT))
        for event in (env.get("payload") or {}).get("events") or []:
            espn_id = str(event.get("id") or "")
            tip = str(event.get("date") or "")
            comps = (event.get("competitions") or [None])[0] or {}
            status = str(((comps.get("status") or {}).get("type") or {}).get("name") or "")
            home_c = away_c = None
            for c in comps.get("competitors") or []:
                if c.get("homeAway") == "home":
                    home_c = c
                elif c.get("homeAway") == "away":
                    away_c = c
            if home_c is None or away_c is None:
                rows.append(
                    classify_espn_reject(
                        espn_id=espn_id,
                        day=day,
                        tip=tip,
                        status=status,
                        home_c=home_c,
                        away_c=away_c,
                        mapped={"home": None, "away": None, "reason": "malformed"},
                        di_universe=di_universe,
                        digest=digest,
                        rel=rel,
                        seen=seen,
                    )
                )
                if espn_id:
                    seen.add(espn_id)
                continue
            mapped = map_espn_event_sides(home_c.get("team") or {}, away_c.get("team") or {})
            if mapped.get("ok"):
                mapped_count += 1
                if espn_id:
                    seen.add(espn_id)
                continue
            rows.append(
                classify_espn_reject(
                    espn_id=espn_id,
                    day=day,
                    tip=tip,
                    status=status,
                    home_c=home_c,
                    away_c=away_c,
                    mapped=mapped,
                    di_universe=di_universe,
                    digest=digest,
                    rel=rel,
                    seen=seen,
                )
            )
            if espn_id:
                seen.add(espn_id)

    counts = Counter(r["classification"] for r in rows)
    taxonomy_counts = {k: int(counts.get(k, 0)) for k in ESPN_REJECT_TAXONOMY}
    for k, v in counts.items():
        taxonomy_counts.setdefault(k, int(v))
    taxonomy_sum = sum(taxonomy_counts.values())
    return {
        "schema_version": "ncaam-espn-reject-ledger-26c-v1",
        "expected_reject_count": EXPECTED_ESPN_REJECT_COUNT,
        "n_rejects": len(rows),
        "n_mapped_both_sides": mapped_count,
        "taxonomy_counts": taxonomy_counts,
        "taxonomy_sum": taxonomy_sum,
        "taxonomy_sums_to_expected": taxonomy_sum == EXPECTED_ESPN_REJECT_COUNT == len(rows),
        "kenpom_di_universe_size": len(di_universe),
        "mapping_rule_version": MAPPING_RULE_VERSION,
        "quarantine_count": sum(
            1
            for r in rows
            if r["classification"]
            in {
                "ambiguous_identity",
                "b7_alias_missing",
                "b7_team_missing",
                "other_explicit_reason",
            }
        ),
        "rows": rows,
        "scores_omitted": True,
        "interpretation": (
            "Non-DI confirmed via KenPom DI roster absence + fail-closed identity, "
            "not B7-absence alone. Parenthetical DI-homonyms quarantined as ambiguous."
        ),
    }


def build_identity_collision_audit(odds_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    aliases = _aliases()
    omit = _omit()
    reverse: Dict[str, List[str]] = defaultdict(list)
    for raw, tid in aliases.items():
        reverse[str(tid)].append(raw)

    checks = [
        ("miami", None),
        ("miami fl", "miami fl"),
        ("miami oh", "miami oh"),
        ("usc", "usc"),
        ("south carolina", "south carolina"),
        ("texas a&m", "texas a&m"),
        ("texas a&m commerce", "east texas a&m"),
        ("east texas a&m", "east texas a&m"),
        ("ut arlington", "ut arlington"),
        ("utsa", "utsa"),
        ("utep", "utep"),
        ("st francis", None),
        ("st francis pa", "st francis pa"),
        ("loyola", None),
        ("loyola chicago", "loyola chicago"),
        ("loyola marymount", "loyola marymount"),
        ("saint mary's", "saint mary's"),
        ("southern", None),
        ("northern iowa", "northern iowa"),
        ("eastern kentucky", "eastern kentucky"),
        ("western kentucky", "western kentucky"),
    ]
    failures = []
    results: Dict[str, Any] = {}
    for raw, expected in checks:
        resolved = odds_name_to_team_norm(raw)
        direct = resolve_team_id(raw)
        ok = True
        if expected is None:
            if fold_ncaam_alias(raw) not in omit and (resolved is not None or direct is not None):
                ok = False
        else:
            if resolved != expected and direct != expected:
                ok = False
        results[raw] = {
            "expected": expected,
            "odds_norm": resolved,
            "direct": direct,
            "ok": ok,
        }
        if not ok:
            failures.append({**results[raw], "raw": raw})

    unresolved = [r for r in odds_rows if r.get("b1_status") == "IDENTITY_UNRESOLVED"]
    rule_hits: Counter[str] = Counter()
    for r in odds_rows:
        for raw in (r.get("home_team_raw"), r.get("away_team_raw")):
            if not raw:
                continue
            folded = fold_ncaam_alias(str(raw))
            if folded in aliases:
                rule_hits["exact_alias"] += 1
            elif odds_name_to_team_norm(str(raw)):
                rule_hits["deterministic_expansion"] += 1
            else:
                rule_hits["unresolved"] += 1

    overbroad = [
        bare
        for bare in ("miami", "loyola", "southern", "st francis")
        if fold_ncaam_alias(bare) not in omit and odds_name_to_team_norm(bare)
    ]
    return {
        "schema_version": "ncaam-identity-collision-audit-26c-v1",
        "n_alias_entries": len(aliases),
        "n_omit_entries": len(omit),
        "n_b7_targets": len(reverse),
        "identity_unresolved_events": len(unresolved),
        "identity_unresolved_cleared": len(unresolved) == 0,
        "rule_hit_counts": dict(rule_hits),
        "homonym_checks": results,
        "collision_failures": failures,
        "overbroad_bare_tokens": overbroad,
        "collision_safe": len(failures) == 0 and len(overbroad) == 0,
        "forbidden_methods_not_used": [
            "fuzzy_matching",
            "nearest_name",
            "city_only",
            "conference_only",
            "home_away_flip_to_match",
            "silent_many_to_one_collapse",
        ],
        "scores_omitted": True,
    }


def build_reversal_diagnostic(
    odds_rows: List[Dict[str, Any]], schedule_games: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    dups = [r for r in odds_rows if r.get("b1_status") == "DUPLICATE_CONFLICT"]
    by_reason = Counter(tuple(r.get("reasons") or []) for r in dups)
    orientation = [
        r for r in dups if "participant_orientation_mismatch" in (r.get("reasons") or [])
    ]
    true_dups = [r for r in dups if "duplicate_event_grain" in (r.get("reasons") or [])]

    sched_idx: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for g in schedule_games:
        hid, aid = str(g.get("home") or ""), str(g.get("away") or "")
        tip_date = str(g.get("date") or "")[:10]
        if not hid or not aid:
            continue
        a, b = sorted([hid, aid])
        sched_idx[(a, b, tip_date)].append(g)

    full: List[Dict[str, Any]] = []
    for r in orientation:
        hid = str(r.get("home_team_id") or "")
        aid = str(r.get("away_team_id") or "")
        tip_date = str(r.get("tip_date") or "")[:10]
        a, b = sorted([hid, aid])
        matches = sched_idx.get((a, b, tip_date), [])
        reverse_matches = [g for g in matches if g.get("home") == aid and g.get("away") == hid]
        exact_matches = [g for g in matches if g.get("home") == hid and g.get("away") == aid]
        unambiguous = len(reverse_matches) == 1 and len(exact_matches) == 0
        full.append(
            {
                "odds_event_id": r.get("event_id"),
                "tip_date": tip_date,
                "odds_home": hid,
                "odds_away": aid,
                "n_schedule_pair_date_matches": len(matches),
                "n_reverse_orientation_matches": len(reverse_matches),
                "n_exact_orientation_matches": len(exact_matches),
                "schedule_espn_game_id": (
                    reverse_matches[0].get("espn_game_id") if unambiguous else None
                ),
                "mathematically_unambiguous_orientation_map": unambiguous,
                "would_require": (
                    [
                        "swap_home_away",
                        "negate_home_spread",
                        "preserve_total",
                        "reconcile_commence_timestamps",
                        "retain_schedule_espn_game_id_as_authoritative",
                    ]
                    if unambiguous
                    else ["remain_quarantined"]
                ),
                "recovery_applied": False,
                "scores_omitted": True,
            }
        )

    n_unambiguous = sum(1 for c in full if c["mathematically_unambiguous_orientation_map"])
    summary = {
        "schema_version": "ncaam-reversal-duplicate-diagnostic-26c-v1",
        "n_duplicate_conflicts": len(dups),
        "expected_duplicate_conflicts": EXPECTED_DUPLICATE_CONFLICT_COUNT,
        "counts_match_expected": len(dups) == EXPECTED_DUPLICATE_CONFLICT_COUNT,
        "reason_tuple_counts": {str(list(k)): v for k, v in by_reason.items()},
        "n_orientation_mismatch": len(orientation),
        "n_true_duplicate_grain": len(true_dups),
        "true_duplicate_cases": [
            {
                "odds_event_id": r.get("event_id"),
                "tip_date": r.get("tip_date"),
                "home_team_id": r.get("home_team_id"),
                "away_team_id": r.get("away_team_id"),
                "reasons": r.get("reasons"),
                "verdict": "true_duplicate_or_event_id_collision_quarantined",
            }
            for r in true_dups
        ],
        "future_recovery_spec": {
            "status": "DRAFT_FUTURE_ONLY_NOT_APPLIED",
            "eligible_if": (
                "unordered B7 pair + tip_date uniquely match exactly one schedule game "
                "with reversed home/away; provider event id preserved; no score-based survivor"
            ),
            "transform": {
                "swap_home_away": True,
                "negate_home_spread": True,
                "total_unchanged": True,
                "authoritative_schedule_id": True,
            },
            "n_orientation_rows": len(orientation),
            "n_unambiguous_orientation_maps": n_unambiguous,
            "n_ambiguous_remain_quarantined": len(orientation) - n_unambiguous,
            "true_duplicate_rows_remain_quarantined": len(true_dups),
            "recovery_applied_in_phase_26c": False,
        },
        "all_153_remain_quarantined": True,
        "recovery_applied": False,
        "scores_omitted": True,
        "model_performance_not_used": True,
    }
    return summary, full


def build_representativeness(
    features: List[Dict[str, Any]],
    odds_rows: List[Dict[str, Any]],
    schedule_games: List[Dict[str, Any]],
    kenpom_lookup: Dict[str, Dict[str, Dict[str, Any]]],
    spread_by_event: Dict[str, float],
) -> Dict[str, Any]:
    odds_by_espn = {
        str(r.get("schedule_espn_game_id")): r
        for r in odds_rows
        if r.get("schedule_espn_game_id")
    }
    odds_by_event = {str(r.get("event_id")): r for r in odds_rows}
    sched_by_id = {
        str(g.get("espn_game_id") or g.get("game_id")): g for g in schedule_games
    }

    enriched: List[Dict[str, Any]] = []
    for f in features:
        eid = str(f.get("event_id"))
        tip = str(f.get("tip") or "")
        tip_dt = None
        try:
            tip_dt = datetime.fromisoformat(tip.replace("Z", "+00:00"))
        except ValueError:
            pass
        tip_hour = tip_dt.hour if tip_dt else None
        tip_date = str(f.get("tip_date") or (tip[:10] if tip else ""))
        month = tip_date[:7] if tip_date else "missing"
        weekday = tip_dt.strftime("%A") if tip_dt else "missing"
        venue = str(f.get("venue_status") or "unknown")
        complete = bool((f.get("eligibility_flags") or {}).get("complete_intersection"))
        b1 = str(f.get("b1_status") or "")
        g = sched_by_id.get(eid) or {}
        season_type = str(g.get("season_type") or "unknown")
        conf_game = bool(g.get("conference_game"))
        snap_id = str(f.get("kenpom_snapshot_id") or "")
        snap_day = None
        for part in snap_id.replace(".parquet", "").split("_"):
            if len(part) == 10 and part[4] == "-" and part[7] == "-":
                snap_day = part
                break
        home = str(f.get("home_team_id") or f.get("home_team_norm") or "")
        away = str(f.get("away_team_id") or f.get("away_team_norm") or "")
        home_kp = (kenpom_lookup.get(snap_day) or {}).get(home) if snap_day else None
        away_kp = (kenpom_lookup.get(snap_day) or {}).get(away) if snap_day else None
        adjm_gap = None
        adjt_mean = None
        home_conf = None
        if (
            home_kp
            and away_kp
            and home_kp.get("adjem") is not None
            and away_kp.get("adjem") is not None
        ):
            adjm_gap = float(home_kp["adjem"]) - float(away_kp["adjem"])
        if (
            home_kp
            and away_kp
            and home_kp.get("adjt") is not None
            and away_kp.get("adjt") is not None
        ):
            adjt_mean = (float(home_kp["adjt"]) + float(away_kp["adjt"])) / 2.0
        if home_kp:
            home_conf = home_kp.get("conf")
        power = "missing"
        if home_conf:
            power = "power" if home_conf in POWER_CONF_SHORT else "non_power"

        odds = odds_by_espn.get(eid) or odds_by_event.get(str(f.get("b1_odds_event_id") or ""))
        n_books = None
        if odds:
            n_books = odds.get("n_books") or odds.get("books_present")
        elif f.get("books_present") is not None:
            n_books = f.get("books_present")
        close_ts = (odds or {}).get("close_snapshot_ts") or f.get("b1_close_ts")
        close_hour = None
        if close_ts:
            try:
                close_hour = datetime.fromisoformat(str(close_ts).replace("Z", "+00:00")).hour
            except ValueError:
                pass
        hours_to_tip = None
        if tip_dt and close_ts:
            try:
                cts = datetime.fromisoformat(str(close_ts).replace("Z", "+00:00"))
                hours_to_tip = (tip_dt - cts).total_seconds() / 3600.0
            except ValueError:
                pass
        odds_eid = str(f.get("b1_odds_event_id") or (odds or {}).get("event_id") or "")
        spread_mag = spread_by_event.get(odds_eid)

        enriched.append(
            {
                "event_id": eid,
                "complete": complete,
                "b1_status": b1,
                "timestamp_honest": b1 == "B1_ELIGIBLE",
                "timestamp_dishonest": b1 == "TIMESTAMP_DISHONEST",
                "month": month,
                "weekday": weekday,
                "tip_hour_utc": tip_hour,
                "tip_band_utc": tip_band(tip_hour),
                "venue_status": venue,
                "season_type": season_type,
                "conference_game": str(conf_game),
                "home_conf": home_conf or "missing",
                "power": power,
                "adjm_gap": adjm_gap,
                "adjm_gap_bin": bin_label(adjm_gap, ADJM_GAP_BINS),
                "adjt_mean": adjt_mean,
                "adjt_bin": bin_label(adjt_mean, ADJT_BINS),
                "n_books": float(n_books) if n_books is not None else None,
                "close_hour_utc": close_hour,
                "hours_close_to_tip": hours_to_tip,
                "spread_mag": spread_mag,
                "spread_mag_bin": bin_label(spread_mag, SPREAD_MAG_BINS),
                "schedule_source_day": tip_date,
                "home_team": home,
                "away_team": away,
            }
        )

    included = [e for e in enriched if e["complete"]]
    reference = enriched
    honest = [e for e in enriched if e["timestamp_honest"]]
    dishonest = [e for e in enriched if e["timestamp_dishonest"]]
    global_cov = (len(included) / len(reference)) if reference else None

    def coverage_table(key: str) -> List[Dict[str, Any]]:
        ref_c = Counter(str(r.get(key) or "missing") for r in reference)
        inc_c = Counter(str(r.get(key) or "missing") for r in included)
        out = []
        for slice_key, ref_n in sorted(ref_c.items(), key=lambda x: (-x[1], str(x[0]))):
            inc_n = int(inc_c.get(slice_key, 0))
            cov = (inc_n / ref_n) if ref_n else None
            gap = None if cov is None or global_cov is None else abs(cov - global_cov) * 100.0
            out.append(
                {
                    "slice": key,
                    "slice_value": slice_key,
                    "included_count": inc_n,
                    "denominator_count": ref_n,
                    "coverage_rate": cov,
                    "coverage_pct": None if cov is None else round(100.0 * cov, 2),
                    "abs_gap_pp_vs_global": None if gap is None else round(gap, 2),
                    "material_flag": bool(
                        gap is not None and gap >= ABS_COVERAGE_GAP_PP_MATERIAL
                    ),
                }
            )
        return out

    slices = {
        key: coverage_table(key)
        for key in (
            "month",
            "weekday",
            "tip_band_utc",
            "venue_status",
            "power",
            "home_conf",
            "adjm_gap_bin",
            "adjt_bin",
            "season_type",
            "close_hour_utc",
            "spread_mag_bin",
            "conference_game",
        )
    }

    def numeric_smd(field: str) -> Dict[str, Any]:
        a = [float(e[field]) for e in included if e.get(field) is not None]
        b = [
            float(e[field])
            for e in reference
            if (not e["complete"]) and e.get(field) is not None
        ]
        s = smd(a, b)
        return {
            "feature": field,
            "included_n": len(a),
            "excluded_n": len(b),
            "included_mean": (sum(a) / len(a)) if a else None,
            "excluded_mean": (sum(b) / len(b)) if b else None,
            "smd": None if s is None else round(s, 4),
            "material_flag": bool(s is not None and abs(s) >= SMD_MATERIAL),
            "clearly_material_flag": bool(s is not None and abs(s) >= SMD_CLEARLY_MATERIAL),
        }

    numeric = [
        numeric_smd("adjm_gap"),
        numeric_smd("adjt_mean"),
        numeric_smd("tip_hour_utc"),
        numeric_smd("n_books"),
        numeric_smd("hours_close_to_tip"),
        numeric_smd("spread_mag"),
    ]

    def rate_by(key: str) -> List[Dict[str, Any]]:
        c_all = Counter(str(r.get(key) or "missing") for r in enriched)
        c_bad = Counter(
            str(r.get(key) or "missing") for r in enriched if r["timestamp_dishonest"]
        )
        out = []
        for k, n in sorted(c_all.items(), key=lambda x: (-x[1], str(x[0]))):
            bad = c_bad.get(k, 0)
            out.append(
                {
                    "slice": key,
                    "slice_value": k,
                    "n": n,
                    "n_timestamp_dishonest": bad,
                    "dishonest_rate": (bad / n) if n else None,
                }
            )
        return out

    honesty_dependence = {
        "by_tip_band_utc": rate_by("tip_band_utc"),
        "by_weekday": rate_by("weekday"),
        "by_month": rate_by("month"),
        "by_power": rate_by("power"),
        "by_venue_status": rate_by("venue_status"),
        "by_close_hour_utc": rate_by("close_hour_utc"),
        "synthetic_close_hour_utc": SYNTHETIC_CLOSE_HOUR_UTC,
        "n_dishonest_on_features": len(dishonest),
        "n_honest_on_features": len(honest),
        "expected_dishonest_odds_rows": EXPECTED_TIMESTAMP_DISHONEST_COUNT,
    }

    material_rows = [row for table in slices.values() for row in table if row.get("material_flag")]
    material_numeric = [n for n in numeric if n.get("material_flag")]
    missingness = {
        "adjm_gap_missing_pct": round(
            100.0 * sum(1 for e in enriched if e["adjm_gap"] is None) / max(len(enriched), 1),
            2,
        ),
        "adjt_missing_pct": round(
            100.0 * sum(1 for e in enriched if e["adjt_mean"] is None) / max(len(enriched), 1),
            2,
        ),
        "n_books_missing_pct": round(
            100.0 * sum(1 for e in enriched if e["n_books"] is None) / max(len(enriched), 1),
            2,
        ),
        "home_conf_missing_pct": round(
            100.0
            * sum(1 for e in enriched if e["home_conf"] == "missing")
            / max(len(enriched), 1),
            2,
        ),
        "spread_mag_missing_pct": round(
            100.0 * sum(1 for e in enriched if e["spread_mag"] is None) / max(len(enriched), 1),
            2,
        ),
    }

    if missingness["adjm_gap_missing_pct"] > 40 or missingness["home_conf_missing_pct"] > 40:
        conclusion = "INCONCLUSIVE_DUE_TO_MISSING_FEATURES"
    elif material_rows or material_numeric:
        conclusion = "MATERIAL_SELECTION_DETECTED"
    else:
        conclusion = "REPRESENTATIVE_ON_AUDITED_FEATURES"
    assert conclusion in ALLOWED_CONCLUSIONS

    cov_rates = [
        r["coverage_rate"] for t in slices.values() for r in t if r["coverage_rate"] is not None
    ]
    return {
        "schema_version": "ncaam-feature-only-representativeness-26c-v1",
        "threshold_version": THRESHOLD_VERSION,
        "n_mapped_schedule": len(reference),
        "n_complete_intersection": len(included),
        "global_coverage_pct": round(100.0 * len(included) / max(len(reference), 1), 2),
        "slices": slices,
        "numeric_smds": numeric,
        "material_selection_flags": material_rows,
        "material_numeric_flags": material_numeric,
        "honesty_dependence": honesty_dependence,
        "missingness": missingness,
        "coverage_rate_min": min(cov_rates) if cov_rates else None,
        "coverage_rate_max": max(cov_rates) if cov_rates else None,
        "multiplicity_note": (
            "Many slices tested; material flags are descriptive disclosures under "
            "predeclared thresholds, not multiplicity-adjusted p-values."
        ),
        "conclusion": conclusion,
        "scores_omitted": True,
        "outcomes_omitted": True,
        "ats_roi_clv_calibration_omitted": True,
        "candidate_predictions_omitted": True,
    }


def build_storage_convention_inventory() -> Dict[str, Any]:
    """Inventory existing NFL DR S3/R2 pattern; no provisioning."""
    raw_files = sorted(RAW_ESPN_DIR.glob("espn_scoreboard_*.json")) if RAW_ESPN_DIR.exists() else []
    total_bytes = sum(p.stat().st_size for p in raw_files)
    sha_sidecars = list(RAW_ESPN_DIR.glob("*.sha256")) if RAW_ESPN_DIR.exists() else []
    git_attrs = REPO / ".gitattributes"
    lfs = git_attrs.exists() and "filter=lfs" in git_attrs.read_text(
        encoding="utf-8", errors="ignore"
    )
    dr_path = REPO / "services" / "model-service" / "data_platform_nfl" / "dr_backup.py"
    nfl_pattern = {
        "module": str(dr_path.relative_to(REPO)) if dr_path.exists() else None,
        "env_var": "NFL_DR_REMOTE_URI",
        "uri_shape": "s3://bucket/prefix (AWS CLI; R2-compatible endpoint via AWS config)",
        "upload_fn": "upload_dump_if_configured",
        "sidecar": ".sha256 next to object",
        "local_default": "data/backups/nfl",
        "retention_env": "NFL_DR_BACKUP_KEEP",
        "docs": ["docs/NFL_DATA_RESILIENCE.md", "docs/NFL_DATA_PLATFORM.md"],
        "raw_object_table_pattern": "nfl_dp_raw_objects (checksum + payload; not git)",
    }
    return {
        "schema_version": "ncaam-storage-convention-inventory-26c-v1",
        "phase": "2.6C",
        "provisioning_performed": False,
        "awaiting_decision_owner": "Ryan",
        "existing_patterns_inventoried": {
            "nfl_dr_s3_r2": nfl_pattern,
            "git_lfs": {"configured": lfs, "recommendation": "do_not_add_raw_espn_to_lfs"},
            "local_holdout_raw": {
                "path": str(RAW_ESPN_DIR.relative_to(REPO)),
                "payload_count": len(raw_files),
                "total_bytes": total_bytes,
                "total_mib": round(total_bytes / (1024 * 1024), 2),
                "sha256_sidecar_count": len(sha_sidecars),
            },
        },
        "candidate_conventions_for_ncaam_raw": [
            {
                "id": "A_s3_r2_immutable_prefix",
                "description": (
                    "Mirror NFL DR: optional remote URI env (e.g. NCAAM_HOLDOUT_RAW_URI="
                    "s3://…/ncaam/holdout_2024_25/raw/espn_scoreboard) + local cache + sha256 sidecars"
                ),
                "pros": ["matches NFL ops muscle memory", "immutable object keys", "offline-capable"],
                "cons": ["needs Ryan bucket/prefix decision", "credential wiring"],
            },
            {
                "id": "B_content_addressed_object_store",
                "description": "sha256-keyed objects with manifest index in-repo; blobs external",
                "pros": ["dedupe", "strong integrity"],
                "cons": ["more tooling; overkill for day-keyed ESPN boards"],
            },
            {
                "id": "C_git_lfs",
                "description": "Track raw JSON via Git LFS",
                "pros": ["simple clone path"],
                "cons": ["rejected for ~100MiB+ growing lab datasets; PR bloat"],
                "status": "not_recommended",
            },
        ],
        "hard_stops": [
            "no_bucket_provisioning_in_26c",
            "no_raw_deletion",
            "no_migration_execution",
            "await_ryan_architecture_decision",
        ],
        "scores_omitted": True,
    }


def build_storage_architecture_adr(inventory: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "ncaam-storage-architecture-adr-26c-v1",
        "adr_id": "ADR_2026-09-05_holdout_raw_object_storage",
        "status": "PROPOSED_AWAITING_RYAN",
        "evaluated": False,
        "decision": None,
        "context": (
            "Holdout raw ESPN scoreboard payloads (~100 MiB, 300+ day files) currently live under "
            "data/ops/lab/ncaam/holdout_2024_25/raw/. PR491 must not land as a single mega-diff "
            "of raw JSON. NFL DR already uses optional S3/R2 via NFL_DR_REMOTE_URI + sha256 sidecars."
        ),
        "options_considered": inventory.get("candidate_conventions_for_ncaam_raw"),
        "recommendation_pending_ryan": "A_s3_r2_immutable_prefix",
        "non_goals_26c": [
            "provision_bucket",
            "upload_raw",
            "delete_local_raw",
            "rewrite_pr491",
            "unseal_or_score",
        ],
        "doc_path": "docs/ops/ncaam/ADR_2026-09-05_holdout_raw_object_storage.md",
        "scores_omitted": True,
    }


def build_pr491_split_migration_plan() -> Dict[str, Any]:
    return {
        "schema_version": "ncaam-pr491-split-migration-plan-26c-v1",
        "status": "DRAFT_PLAN_ONLY",
        "migration_executed": False,
        "pr491_rewritten": False,
        "awaiting_decision_owner": "Ryan",
        "split_tracks": [
            {
                "track": 1,
                "name": "reusable_ingestion_code_schema_tests",
                "includes": [
                    "scripts/ncaam/ingest_espn_official_schedule.py",
                    "ncaam_espn_schedule_map / identity helpers",
                    "apps/web/tests_pipeline holdout foundation + 26c tests",
                    "normalized schedule SoT schema (no bulk raw)",
                ],
                "excludes": ["raw espn_scoreboard_*.json bulk payloads"],
            },
            {
                "track": 2,
                "name": "manifest_and_small_normalized_fixtures",
                "includes": [
                    "day receipts / sha256 manifests",
                    "tiny fixture days for CI",
                    "feature/odds audit summaries (no outcome joins)",
                ],
                "excludes": ["full-window raw scoreboard dump"],
            },
            {
                "track": 3,
                "name": "externally_stored_immutable_raw_dataset",
                "includes": [
                    "object-store prefix for espn_scoreboard_YYYY-MM-DD.json + .sha256",
                    "fetch/verify script gated on Ryan-approved URI",
                ],
                "excludes": [
                    "git history rewrite",
                    "deletion of local raw before remote verify",
                ],
                "blocked_until": "storage_architecture_decision",
            },
        ],
        "doc_path": "docs/ops/ncaam/PR491_SPLIT_MIGRATION_PLAN_26C.md",
        "scores_omitted": True,
    }


def build_offline_mac_recovery_manifest(odds_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    dishonest = [r for r in odds_rows if r.get("b1_status") == "TIMESTAMP_DISHONEST"]
    rows: List[Dict[str, Any]] = []
    for r in dishonest:
        tip_date = str(r.get("tip_date") or "")[:10]
        rows.append(
            {
                "odds_event_id": r.get("event_id"),
                "schedule_espn_game_id": r.get("schedule_espn_game_id"),
                "tip_date": tip_date,
                "home_team_id": r.get("home_team_id"),
                "away_team_id": r.get("away_team_id"),
                "home_team_raw": r.get("home_team_raw"),
                "away_team_raw": r.get("away_team_raw"),
                "open_snapshot_ts": r.get("open_snapshot_ts"),
                "close_snapshot_ts": r.get("close_snapshot_ts"),
                "reasons": list(r.get("reasons") or []),
                "acceptance_rule": "source_snapshot_time < event_tip",
                "recovery_applied": False,
                "cloud_drive_accessed": False,
            }
        )
    return {
        "schema_version": "ncaam-offline-mac-recovery-manifest-26c-v1",
        "owner": "Ryan offline Mac historical odds archive",
        "n_timestamp_dishonest": len(rows),
        "expected_timestamp_dishonest": EXPECTED_TIMESTAMP_DISHONEST_COUNT,
        "counts_match_expected": len(rows) == EXPECTED_TIMESTAMP_DISHONEST_COUNT,
        "acceptance_rule": "source_snapshot_time < event_tip",
        "cloud_must_not_access_external_drive": True,
        "no_api_credits": True,
        "no_post_tip_relabel": True,
        "recovery_applied": False,
        "runbook_path": "docs/ops/ncaam/OFFLINE_MAC_RECOVERY_RUNBOOK_26C.md",
        "rows": rows,
        "scores_omitted": True,
    }


def build_seal_governance(
    seal: Dict[str, Any],
    arch_v1: Optional[Dict[str, Any]],
    *,
    membership_changed: bool,
) -> Dict[str, Any]:
    return {
        "schema_version": "ncaam-seal-governance-26c-v1",
        "holdout_id": HOLDOUT_ID,
        "package_version": PACKAGE_VERSION,
        "preserve_v1": True,
        "preserve_v1_1": True,
        "v1_archive_present": arch_v1 is not None,
        "v1_archive_path": "seal_archive/v1/seal_receipt.json",
        "v1_1_seal_path": "seal/seal_receipt.json",
        "current_seal_receipt_sha256": seal.get("seal_receipt_sha256"),
        "n_complete_intersection": seal.get("n_complete_intersection"),
        "membership_changed": membership_changed,
        "new_seal_issued": False,
        "evaluated": False,
        "features_labels_joined_for_evaluation": False,
        "policy": (
            "No new seal unless complete-intersection membership changes. "
            "Phase 2.6C does not change membership; preserve v1 archive + v1.1 seal."
        ),
        "scores_omitted": True,
        "unseal_omitted": True,
    }


def write_ops_docs(
    *,
    inventory: Dict[str, Any],
    adr: Dict[str, Any],
    split_plan: Dict[str, Any],
) -> Dict[str, str]:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    adr_path = DOCS_DIR / "ADR_2026-09-05_holdout_raw_object_storage.md"
    split_path = DOCS_DIR / "PR491_SPLIT_MIGRATION_PLAN_26C.md"
    runbook_path = DOCS_DIR / "OFFLINE_MAC_RECOVERY_RUNBOOK_26C.md"

    adr_md = f"""# ADR 2026-09-05 — NCAAM holdout raw object storage

**Status:** PROPOSED — awaiting Ryan decision  
**Phase:** 2.6C (inventory + plan only; no provisioning)

## Context

Raw ESPN scoreboard payloads for the 2024–25 sealed holdout live under
`data/ops/lab/ncaam/holdout_2024_25/raw/espn_scoreboard/`
(~{inventory['existing_patterns_inventoried']['local_holdout_raw']['total_mib']} MiB,
{inventory['existing_patterns_inventoried']['local_holdout_raw']['payload_count']} day files).
Landing them as a single PR491 git blob is blocked.

NFL already has an optional remote dump pattern:

- Env: `NFL_DR_REMOTE_URI=s3://bucket/prefix`
- Tooling: `services/model-service/data_platform_nfl/dr_backup.py` → `upload_dump_if_configured`
- Sidecar: `.sha256` next to the object
- Docs: `docs/NFL_DATA_RESILIENCE.md`

## Decision (pending)

Recommended default (not executed): **A_s3_r2_immutable_prefix** — day-keyed immutable
objects + sha256 sidecars, local cache retained until remote verify succeeds.

## Non-goals (2.6C)

- No bucket provisioning
- No upload / delete of raw
- No PR491 rewrite in this phase
- No scoring / unseal

## Consequences

Until Ryan picks a convention, readiness remains `BLOCKED_STORAGE_ARCHITECTURE`.
"""

    split_md = """# PR491 split migration plan (Phase 2.6C)

**Status:** DRAFT plan only — migration not executed; PR491 not rewritten.

## Goal

Split the holdout raw/ingestion landing into three independently reviewable tracks so
code+tests can ship without embedding ~100 MiB of raw ESPN JSON in git history.

## Track 1 — reusable ingestion code / schema / tests

- ESPN ingest + B7 map helpers
- Schedule SoT schema / normalize
- Foundation + Phase 2.6C pytest
- **Exclude:** bulk `espn_scoreboard_*.json`

## Track 2 — manifests + small fixtures

- Day receipts / sha256 manifests
- Tiny CI fixtures (1–3 days)
- Audit summaries (no outcome joins)

## Track 3 — externally stored immutable raw dataset

- Object-store prefix for full-window raw + sidecars
- Fetch/verify script gated on Ryan-approved URI
- **Blocked until** storage ADR decision
- **Never** delete local raw before remote verify

## Hard stops

No migration execution in 2.6C. No raw deletion. Await Ryan.
"""

    runbook_md = """# Offline Mac recovery runbook — TIMESTAMP_DISHONEST (Phase 2.6C)

## Purpose

Recover honest open/close snapshot times for odds events currently marked
`TIMESTAMP_DISHONEST` (expected n=2006) from Ryan's offline Mac historical archive.

## Acceptance rule (unchanged)

`source_snapshot_time < event_tip`

Do **not** relabel post-tip snapshots as honest. Do **not** invent closes.

## Cloud / agent hard stops

- Do **not** mount or access the external drive from cloud agents
- Do **not** spend Odds API credits to backfill
- Do **not** apply recovery in Phase 2.6C (`recovery_applied=false`)

## Offline operator steps (Ryan Mac only)

1. Load `coverage_26c/offline_mac_recovery_manifest.json` rows.
2. For each `odds_event_id`, locate archive quotes whose capture time is strictly before tip.
3. Prefer book-consistent open/close pairs; retain provider event id.
4. Emit a recovery receipt (sha256 of source files + accepted timestamps).
5. Hand receipt to a future phase for rematerialize — not 2.6C.

## Out of scope

Scoring, ATS/ROI/CLV, unseal, model evaluation.
"""

    adr_path.write_text(adr_md, encoding="utf-8")
    split_path.write_text(split_md, encoding="utf-8")
    runbook_path.write_text(runbook_md, encoding="utf-8")
    return {
        "adr": str(adr_path.relative_to(REPO)),
        "split_plan": str(split_path.relative_to(REPO)),
        "runbook": str(runbook_path.relative_to(REPO)),
    }


def update_readiness_report(
    *,
    seal: Dict[str, Any],
    features: List[Dict[str, Any]],
    odds_rows: List[Dict[str, Any]],
    espn_ledger: Dict[str, Any],
    repr_audit: Dict[str, Any],
    identity_audit: Dict[str, Any],
    reversal: Dict[str, Any],
    offline: Dict[str, Any],
) -> Dict[str, Any]:
    n_complete = sum(
        1 for f in features if (f.get("eligibility_flags") or {}).get("complete_intersection")
    )
    status_counts = Counter(r.get("b1_status") for r in odds_rows)
    blockers = ["BLOCKED_TIMESTAMP_INTEGRITY", "BLOCKED_STORAGE_ARCHITECTURE"]
    readiness = {
        "status": "BLOCKED_MULTIPLE",
        "secondary_status_notes": ["SEALED_COVERAGE_REVIEW_REQUIRED"],
        "blockers": blockers,
        "phase": "2.6C",
        "package_version": PACKAGE_VERSION,
        "holdout_id": HOLDOUT_ID,
        "scheduled_event_count": len(features),
        "b1_eligibility_count": int(status_counts.get("B1_ELIGIBLE") or 0),
        "complete_intersection_count": n_complete,
        "n_timestamp_dishonest": int(status_counts.get("TIMESTAMP_DISHONEST") or 0),
        "n_duplicate_conflict": int(status_counts.get("DUPLICATE_CONFLICT") or 0),
        "n_espn_rejects": espn_ledger.get("n_rejects"),
        "espn_taxonomy_sums_to_expected": espn_ledger.get("taxonomy_sums_to_expected"),
        "identity_collision_safe": identity_audit.get("collision_safe"),
        "identity_unresolved_cleared": identity_audit.get("identity_unresolved_cleared"),
        "reversal_recovery_applied": False,
        "offline_mac_recovery_applied": False,
        "representativeness_conclusion": repr_audit.get("conclusion"),
        "threshold_version": THRESHOLD_VERSION,
        "n_gte_100_not_sufficient_for_representativeness": True,
        "manifest_hash_status": {
            "feature_manifest_sha256": seal.get("feature_manifest_sha256"),
            "label_manifest_sha256": seal.get("label_manifest_sha256"),
            "seal_receipt_sha256": seal.get("seal_receipt_sha256"),
            "features_labels_joined_for_evaluation": False,
        },
        "seal_evaluated": False,
        "new_seal_issued": False,
        "storage_architecture_decision_pending": True,
        "selection_integrity_notes": [
            f"complete_intersection={n_complete} of mapped={len(features)}",
            f"b1_eligible={status_counts.get('B1_ELIGIBLE', 0)}",
            f"timestamp_dishonest={status_counts.get('TIMESTAMP_DISHONEST', 0)} "
            f"(offline_manifest_rows={offline.get('n_timestamp_dishonest')})",
            f"duplicate_conflict={status_counts.get('DUPLICATE_CONFLICT', 0)} "
            f"(orientation={reversal.get('n_orientation_mismatch')})",
            f"espn_rejects={espn_ledger.get('n_rejects')}",
            f"representativeness={repr_audit.get('conclusion')}",
        ],
        "scores_omitted": True,
        "performance_scoring_omitted": True,
        "holdout_unseal_omitted": True,
        "outcome_distribution_inspection_omitted": True,
        "model_implementation_omitted": True,
        "ats_roi_clv_calibration_omitted": True,
        "candidate_predictions_omitted": True,
        "merged_deployed_promoted": False,
    }
    write_json(OUT_ROOT / "readiness_report.json", readiness)
    return readiness


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    COVERAGE_26C.mkdir(parents=True, exist_ok=True)

    # 1) Threshold lock FIRST — before any slice math
    threshold_receipt = frozen_threshold_receipt()
    write_json(COVERAGE_26C / "threshold_lock.json", threshold_receipt)

    features = load_json(OUT_ROOT / "feature_package" / "features.json")
    odds_rows = load_json(OUT_ROOT / "odds_audit" / "odds_audit_rows.json")
    pack = load_json(CANONICAL_PACK_PATH)
    schedule_games = list(pack.get("games") or [])
    seal = load_json(OUT_ROOT / "seal" / "seal_receipt.json")
    arch_path = OUT_ROOT / "seal_archive" / "v1" / "seal_receipt.json"
    arch_v1 = load_json(arch_path) if arch_path.exists() else None

    di_universe = load_kenpom_di_universe()
    espn_ledger = build_espn_reject_ledger(di_universe)
    write_json(COVERAGE_26C / "espn_reject_ledger.json", espn_ledger)

    identity_audit = build_identity_collision_audit(odds_rows)
    write_json(COVERAGE_26C / "identity_collision_audit.json", identity_audit)

    reversal, orientation_full = build_reversal_diagnostic(odds_rows, schedule_games)
    write_json(COVERAGE_26C / "reversal_duplicate_diagnostic.json", reversal)
    write_json(
        COVERAGE_26C / "reversal_orientation_full.json",
        {
            "schema_version": "ncaam-reversal-orientation-full-26c-v1",
            "n_rows": len(orientation_full),
            "recovery_applied": False,
            "rows": orientation_full,
            "scores_omitted": True,
        },
    )

    kenpom_lookup = load_kenpom_by_day()
    spread_by_event = load_spread_by_event()
    repr_audit = build_representativeness(
        features, odds_rows, schedule_games, kenpom_lookup, spread_by_event
    )
    write_json(COVERAGE_26C / "feature_only_representativeness.json", repr_audit)

    inventory = build_storage_convention_inventory()
    write_json(COVERAGE_26C / "storage_convention_inventory.json", inventory)
    adr = build_storage_architecture_adr(inventory)
    write_json(COVERAGE_26C / "storage_architecture_adr.json", adr)
    split_plan = build_pr491_split_migration_plan()
    write_json(COVERAGE_26C / "pr491_split_migration_plan.json", split_plan)

    offline = build_offline_mac_recovery_manifest(odds_rows)
    write_json(COVERAGE_26C / "offline_mac_recovery_manifest.json", offline)

    seal_gov = build_seal_governance(seal, arch_v1, membership_changed=False)
    write_json(COVERAGE_26C / "seal_governance.json", seal_gov)

    docs = write_ops_docs(inventory=inventory, adr=adr, split_plan=split_plan)

    readiness = update_readiness_report(
        seal=seal,
        features=features,
        odds_rows=odds_rows,
        espn_ledger=espn_ledger,
        repr_audit=repr_audit,
        identity_audit=identity_audit,
        reversal=reversal,
        offline=offline,
    )

    summary = {
        "schema_version": "ncaam-coverage-26c-summary-v1",
        "phase": "2.6C",
        "holdout_id": HOLDOUT_ID,
        "package_version": PACKAGE_VERSION,
        "threshold_version": THRESHOLD_VERSION,
        "threshold_locked_before_slices": True,
        "n_espn_rejects": espn_ledger.get("n_rejects"),
        "espn_taxonomy_sum": espn_ledger.get("taxonomy_sum"),
        "espn_taxonomy_sums_to_expected": espn_ledger.get("taxonomy_sums_to_expected"),
        "identity_collision_safe": identity_audit.get("collision_safe"),
        "identity_unresolved_events": identity_audit.get("identity_unresolved_events"),
        "n_duplicate_conflicts": reversal.get("n_duplicate_conflicts"),
        "n_orientation_mismatch": reversal.get("n_orientation_mismatch"),
        "n_true_duplicate_grain": reversal.get("n_true_duplicate_grain"),
        "recovery_applied": False,
        "n_timestamp_dishonest": offline.get("n_timestamp_dishonest"),
        "representativeness_conclusion": repr_audit.get("conclusion"),
        "readiness_status": readiness.get("status"),
        "blockers": readiness.get("blockers"),
        "secondary_status_notes": readiness.get("secondary_status_notes"),
        "seal_evaluated": False,
        "new_seal_issued": False,
        "docs": docs,
        "coverage_dir": str(COVERAGE_26C.relative_to(REPO)),
        "scores_omitted": True,
        "performance_scoring_omitted": True,
        "holdout_unseal_omitted": True,
        "model_implementation_omitted": True,
        "hard_stops_honored": [
            "no_scoring",
            "no_unseal",
            "no_model",
            "no_api",
            "no_external_drive",
            "no_recovery_applied",
            "no_raw_deletion",
        ],
    }
    write_json(COVERAGE_26C / "coverage_26c_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

