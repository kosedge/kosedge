#!/usr/bin/env python3
"""Path A NCAAM odds lake integrity — CURRENT lake only. NO Odds API fetch.

Checks (fail-closed receipts, no credit spend):
  - expected pocket coverage (post-PR #482 densify ranges)
  - open/close pairing + honesty (>7d API timestamp drift)
  - parquet vs raw inventory
  - event_id duplicates / identity fail-closed (B7)
  - line/price validity, missingness, obvious outliers

Usage (repo root):
  python3 apps/web/scripts/ncaam_odds_lake_integrity.py
  python3 apps/web/scripts/ncaam_odds_lake_integrity.py --write-ops-note
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

WEB = Path(__file__).resolve().parents[1]
SRC = WEB / "src"
ROOT = WEB.parents[1]

for p in (str(WEB), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Post-PR #482 honesty-clean Path A pockets (from densify ops note).
EXPECTED_POCKETS: List[Tuple[str, str, int]] = [
    ("2022-11-05", "2023-04-11", 158),
    ("2023-10-10", "2024-04-15", 189),
    ("2024-10-27", "2025-01-16", 82),
    ("2025-11-01", "2025-12-04", 34),
]
EXPECTED_OPEN_CLOSE = 463
EXPECTED_PARQUET_ROWS = 189_609
EXPECTED_UNIQUE_EVENTS = 15_459
MAX_DRIFT_DAYS = 7

# Plausible CBB mainline bands (outliers only — not Lab gates).
SPREAD_ABS_SOFT = 40.0
SPREAD_ABS_HARD = 55.0
TOTAL_SOFT_LO, TOTAL_SOFT_HI = 100.0, 180.0
TOTAL_HARD_LO, TOTAL_HARD_HI = 80.0, 220.0


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _daterange(start: date, end: date) -> List[date]:
    out: List[date] = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def _expected_stems() -> Set[str]:
    stems: Set[str] = set()
    for a, b, _n in EXPECTED_POCKETS:
        for d in _daterange(_d(a), _d(b)):
            stems.add(d.isoformat())
    return stems


def _parse_api_ts(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_payload(fp: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"timestamp": None, "data": data}
    return None


def _honesty_drift_days(stem: str, payload: Dict[str, Any]) -> Optional[float]:
    api_dt = _parse_api_ts(payload.get("timestamp"))
    if api_dt is None:
        return None
    try:
        file_dt = datetime.strptime(stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return abs((api_dt - file_dt).total_seconds()) / 86400.0


def check_pockets(open_dir: Path, close_dir: Path) -> Dict[str, Any]:
    open_stems = {p.stem for p in open_dir.glob("*.json")}
    close_stems = {p.stem for p in close_dir.glob("*.json")}
    expected = _expected_stems()
    expected_n = sum(n for *_r, n in EXPECTED_POCKETS)
    assert expected_n == EXPECTED_OPEN_CLOSE

    pocket_rows = []
    for a, b, n_exp in EXPECTED_POCKETS:
        want = {_d(a) + timedelta(days=i) for i in range(n_exp)}
        # Prefer inclusive calendar count
        want = set(_daterange(_d(a), _d(b)))
        present = {s for s in open_stems if s in {d.isoformat() for d in want}}
        missing = sorted({d.isoformat() for d in want} - open_stems)
        extra_in_range = sorted(present - {d.isoformat() for d in want})
        pocket_rows.append(
            {
                "start": a,
                "end": b,
                "expected_days": n_exp,
                "calendar_days": len(want),
                "open_present": len(present & open_stems),
                "close_present": len({s for s in close_stems if s in {d.isoformat() for d in want}}),
                "missing_open": missing[:20],
                "n_missing_open": len(missing),
            }
        )

    open_only = sorted(open_stems - close_stems)
    close_only = sorted(close_stems - open_stems)
    unexpected = sorted(open_stems - expected)
    missing_expected = sorted(expected - open_stems)

    return {
        "open_count": len(open_stems),
        "close_count": len(close_stems),
        "expected_count": EXPECTED_OPEN_CLOSE,
        "open_equals_close_pairing": open_stems == close_stems,
        "open_only": open_only[:50],
        "close_only": close_only[:50],
        "n_open_only": len(open_only),
        "n_close_only": len(close_only),
        "matches_expected_inventory": (
            len(open_stems) == EXPECTED_OPEN_CLOSE
            and open_stems == close_stems
            and not missing_expected
            and not unexpected
        ),
        "n_unexpected_stems": len(unexpected),
        "unexpected_stems_sample": unexpected[:20],
        "n_missing_expected": len(missing_expected),
        "missing_expected_sample": missing_expected[:20],
        "pockets": pocket_rows,
        "open_first": min(open_stems) if open_stems else None,
        "open_last": max(open_stems) if open_stems else None,
    }


def check_honesty(open_dir: Path, close_dir: Path) -> Dict[str, Any]:
    dishonest_open: List[Dict[str, Any]] = []
    missing_ts: List[str] = []
    bad_json: List[str] = []
    honest = 0
    for fp in sorted(open_dir.glob("*.json")):
        payload = _load_payload(fp)
        if payload is None:
            bad_json.append(fp.stem)
            continue
        drift = _honesty_drift_days(fp.stem, payload)
        if drift is None:
            missing_ts.append(fp.stem)
            continue
        if drift > MAX_DRIFT_DAYS:
            dishonest_open.append(
                {
                    "date": fp.stem,
                    "drift_days": round(drift, 3),
                    "api_timestamp": payload.get("timestamp"),
                }
            )
        else:
            honest += 1

    # Close files: timestamp honesty is secondary (Market Edge filters on open),
    # but report drift >7d for inventory hygiene.
    dishonest_close: List[Dict[str, Any]] = []
    for fp in sorted(close_dir.glob("*.json")):
        payload = _load_payload(fp)
        if payload is None:
            continue
        drift = _honesty_drift_days(fp.stem, payload)
        if drift is not None and drift > MAX_DRIFT_DAYS:
            dishonest_close.append(
                {
                    "date": fp.stem,
                    "drift_days": round(drift, 3),
                    "api_timestamp": payload.get("timestamp"),
                }
            )

    return {
        "max_drift_days": MAX_DRIFT_DAYS,
        "open_honest_n": honest,
        "open_dishonest_n": len(dishonest_open),
        "open_dishonest_sample": dishonest_open[:25],
        "open_missing_timestamp_n": len(missing_ts),
        "open_missing_timestamp_sample": missing_ts[:20],
        "open_bad_json_n": len(bad_json),
        "close_dishonest_n": len(dishonest_close),
        "close_dishonest_sample": dishonest_close[:25],
        "open_honesty_clean": (
            len(dishonest_open) == 0 and len(missing_ts) == 0 and len(bad_json) == 0
        ),
    }


def check_raw_events(open_dir: Path) -> Dict[str, Any]:
    from ncaam_identity import resolve_team_id

    event_days: Dict[str, Set[str]] = defaultdict(set)
    event_meta: Dict[str, Dict[str, str]] = {}
    empty_id = 0
    empty_teams = 0
    sport_key_bad = 0
    n_events = 0
    home_unresolved = 0
    away_unresolved = 0
    both_resolved = 0
    omit_or_unknown_names: Counter = Counter()

    for fp in sorted(open_dir.glob("*.json")):
        payload = _load_payload(fp)
        if payload is None:
            continue
        events = payload.get("data") if isinstance(payload.get("data"), list) else []
        for ev in events:
            n_events += 1
            eid = str(ev.get("id") or "")
            if not eid:
                empty_id += 1
                continue
            home = str(ev.get("home_team") or "")
            away = str(ev.get("away_team") or "")
            if not home or not away:
                empty_teams += 1
            sk = str(ev.get("sport_key") or "")
            if sk and sk != "basketball_ncaab":
                sport_key_bad += 1
            event_days[eid].add(fp.stem)
            if eid not in event_meta:
                event_meta[eid] = {"home_team": home, "away_team": away}
            hid = resolve_team_id(home, source="odds")
            aid = resolve_team_id(away, source="odds")
            if hid is None:
                home_unresolved += 1
                omit_or_unknown_names[home or "(empty)"] += 1
            if aid is None:
                away_unresolved += 1
                omit_or_unknown_names[away or "(empty)"] += 1
            if hid is not None and aid is not None:
                both_resolved += 1

    multi_day = {eid: sorted(days) for eid, days in event_days.items() if len(days) > 1}
    # Same event_id with conflicting team strings across days
    # Second pass for identity conflicts on multi-day event_ids
    first_seen: Dict[str, Tuple[str, str]] = {}
    flip_conflicts: List[Dict[str, Any]] = []
    real_conflicts: List[Dict[str, Any]] = []
    for fp in sorted(open_dir.glob("*.json")):
        payload = _load_payload(fp)
        if payload is None:
            continue
        for ev in payload.get("data") or []:
            eid = str(ev.get("id") or "")
            if not eid or eid not in multi_day:
                continue
            pair = (str(ev.get("home_team") or ""), str(ev.get("away_team") or ""))
            if eid not in first_seen:
                first_seen[eid] = pair
            elif first_seen[eid] != pair:
                a, b = first_seen[eid]
                c, d = pair
                rec = {
                    "event_id": eid,
                    "first": {"home": a, "away": b},
                    "later": {"home": c, "away": d, "date": fp.stem},
                }
                if {a, b} == {c, d}:
                    flip_conflicts.append(rec)
                else:
                    real_conflicts.append(rec)

    return {
        "n_event_rows_across_open_files": n_events,
        "n_unique_event_ids_open": len(event_days),
        "empty_event_id_n": empty_id,
        "empty_team_name_n": empty_teams,
        "sport_key_not_basketball_ncaab_n": sport_key_bad,
        "event_ids_on_multiple_open_days_n": len(multi_day),
        "event_ids_on_multiple_open_days_sample": [
            {"event_id": k, "days": v[:5], "n_days": len(v)}
            for k, v in list(sorted(multi_day.items(), key=lambda kv: -len(kv[1])))[:15]
        ],
        "identity_team_string_conflicts_n": len(flip_conflicts) + len(real_conflicts),
        "identity_home_away_flips_n": len(flip_conflicts),
        "identity_home_away_flips_sample": flip_conflicts[:10],
        "identity_real_conflicts_n": len(real_conflicts),
        "identity_real_conflicts_sample": real_conflicts[:10],
        "identity_team_string_conflicts_sample": (real_conflicts + flip_conflicts)[:10],
        "b7_both_sides_resolved_n": both_resolved,
        "b7_home_unresolved_n": home_unresolved,
        "b7_away_unresolved_n": away_unresolved,
        "b7_resolve_rate_both": round(both_resolved / n_events, 4) if n_events else None,
        "b7_unresolved_name_top": omit_or_unknown_names.most_common(15),
        "note": (
            "B7 unresolved is fail-closed Lab omit (not lake corruption). "
            "Multi-day event_id in open files is expected (same tip reappears across snapshot days). "
            "Home/away flips across days are a known Odds API neutral-site quirk."
        ),
    }


def check_parquet(parquet_path: Path) -> Dict[str, Any]:
    import polars as pl

    if not parquet_path.exists():
        return {"exists": False, "path": str(parquet_path)}

    df = pl.read_parquet(parquet_path)
    n_rows = len(df)
    n_events = int(df["event_id"].n_unique()) if n_rows else 0

    # Duplicate event_id+book: Path A grain repeats the same tip across daily
    # snapshot files (different open_time). True corruption = same open_time.
    dup_keys = (
        df.group_by(["event_id", "book"])
        .agg(
            [
                pl.len().alias("n"),
                pl.col("open_time").n_unique().alias("n_open_times"),
            ]
        )
        .filter(pl.col("n") > 1)
    )
    true_dups = dup_keys.filter(pl.col("n_open_times") == 1)
    snapshot_dups = dup_keys.filter(pl.col("n_open_times") > 1)

    # Same event_id with home/away string flips (Odds API neutral-site quirk).
    # Pair-set equality → flip; unequal pair sets → real identity conflict.
    team_modes = (
        df.group_by("event_id")
        .agg(
            [
                pl.col("home_team").n_unique().alias("n_home"),
                pl.col("away_team").n_unique().alias("n_away"),
                pl.col("home_team").unique().alias("homes"),
                pl.col("away_team").unique().alias("aways"),
                pl.col("home_team").first().alias("home0"),
                pl.col("away_team").first().alias("away0"),
            ]
        )
        .filter((pl.col("n_home") > 1) | (pl.col("n_away") > 1))
    )
    flip_n = 0
    real_conflict_n = 0
    flip_sample: List[Dict[str, Any]] = []
    real_conflict_sample: List[Dict[str, Any]] = []
    for row in team_modes.to_dicts():
        homes = set(row.get("homes") or [])
        aways = set(row.get("aways") or [])
        rec = {
            "event_id": row["event_id"],
            "homes": sorted(homes),
            "aways": sorted(aways),
        }
        if homes == aways and len(homes) == 2:
            flip_n += 1
            if len(flip_sample) < 10:
                flip_sample.append(rec)
        else:
            real_conflict_n += 1
            if len(real_conflict_sample) < 10:
                real_conflict_sample.append(rec)

    missing = {
        c: int(df[c].null_count())
        for c in df.columns
    }
    empty_eid = int((df["event_id"].cast(pl.Utf8).str.len_chars() == 0).sum()) if n_rows else 0
    empty_home = int((df["home_team"].cast(pl.Utf8).str.len_chars() == 0).sum()) if n_rows else 0
    empty_away = int((df["away_team"].cast(pl.Utf8).str.len_chars() == 0).sum()) if n_rows else 0

    def _band_counts(col: str, soft_lo: Optional[float], soft_hi: Optional[float],
                     hard_lo: Optional[float], hard_hi: Optional[float], abs_mode: bool = False):
        s = df[col].drop_nulls()
        if abs_mode:
            soft = int(((s.abs() > soft_hi)).sum()) if soft_hi is not None else 0
            hard = int(((s.abs() > hard_hi)).sum()) if hard_hi is not None else 0
        else:
            soft = int(((s < soft_lo) | (s > soft_hi)).sum()) if soft_lo is not None else 0
            hard = int(((s < hard_lo) | (s > hard_hi)).sum()) if hard_lo is not None else 0
        return {
            "n_non_null": len(s),
            "min": float(s.min()) if len(s) else None,
            "max": float(s.max()) if len(s) else None,
            "mean": float(s.mean()) if len(s) else None,
            "soft_outlier_n": soft,
            "hard_outlier_n": hard,
        }

    open_spread = _band_counts(
        "open_spread_home", None, SPREAD_ABS_SOFT, None, SPREAD_ABS_HARD, abs_mode=True
    )
    close_spread = _band_counts(
        "close_spread_home", None, SPREAD_ABS_SOFT, None, SPREAD_ABS_HARD, abs_mode=True
    )
    open_total = _band_counts(
        "open_total", TOTAL_SOFT_LO, TOTAL_SOFT_HI, TOTAL_HARD_LO, TOTAL_HARD_HI
    )
    close_total = _band_counts(
        "close_total", TOTAL_SOFT_LO, TOTAL_SOFT_HI, TOTAL_HARD_LO, TOTAL_HARD_HI
    )

    # open_time span
    open_times = df["open_time"].drop_nulls() if "open_time" in df.columns else None
    open_span = {
        "min": str(open_times.min()) if open_times is not None and len(open_times) else None,
        "max": str(open_times.max()) if open_times is not None and len(open_times) else None,
    }

    matches_inventory = (
        n_rows == EXPECTED_PARQUET_ROWS and n_events == EXPECTED_UNIQUE_EVENTS
    )

    return {
        "exists": True,
        "path": str(parquet_path.relative_to(ROOT)),
        "n_rows": n_rows,
        "n_unique_events": n_events,
        "expected_rows": EXPECTED_PARQUET_ROWS,
        "expected_unique_events": EXPECTED_UNIQUE_EVENTS,
        "matches_densify_inventory": matches_inventory,
        "duplicate_event_id_book_n": len(dup_keys),
        "duplicate_event_id_book_same_open_time_n": len(true_dups),
        "duplicate_event_id_book_snapshot_grain_n": len(snapshot_dups),
        "duplicate_event_id_book_sample": dup_keys.head(10).to_dicts() if len(dup_keys) else [],
        "home_away_flip_events_n": flip_n,
        "home_away_flip_sample": flip_sample,
        "event_id_real_team_conflicts_n": real_conflict_n,
        "event_id_real_team_conflicts_sample": real_conflict_sample,
        "event_id_conflicting_team_strings_n": len(team_modes),
        "empty_event_id_rows": empty_eid,
        "empty_home_team_rows": empty_home,
        "empty_away_team_rows": empty_away,
        "null_counts": missing,
        "open_time_span": open_span,
        "line_validity": {
            "open_spread_home": open_spread,
            "close_spread_home": close_spread,
            "open_total": open_total,
            "close_total": close_total,
            "bands": {
                "spread_abs_soft": SPREAD_ABS_SOFT,
                "spread_abs_hard": SPREAD_ABS_HARD,
                "total_soft": [TOTAL_SOFT_LO, TOTAL_SOFT_HI],
                "total_hard": [TOTAL_HARD_LO, TOTAL_HARD_HI],
            },
        },
    }


def overall_verdict(receipt: Dict[str, Any]) -> Dict[str, Any]:
    pockets = receipt["pockets"]
    honesty = receipt["honesty"]
    parquet = receipt["parquet"]
    raw = receipt["raw_events"]

    blockers: List[str] = []
    warnings: List[str] = []

    if not pockets.get("matches_expected_inventory"):
        blockers.append("pocket inventory ≠ post-densify expected 463/463 honesty-clean set")
    if not pockets.get("open_equals_close_pairing"):
        blockers.append("open/close stem pairing mismatch")
    if not honesty.get("open_honesty_clean"):
        blockers.append("open honesty >7d drift or missing timestamp present")
    if not parquet.get("matches_densify_inventory"):
        blockers.append("parquet row/event counts ≠ densify receipt (189609 / 15459)")
    if parquet.get("duplicate_event_id_book_same_open_time_n", 0) > 0:
        blockers.append(
            "true duplicate event_id+book at same open_time "
            f"(n={parquet.get('duplicate_event_id_book_same_open_time_n')})"
        )
    if parquet.get("event_id_real_team_conflicts_n", 0) > 0:
        blockers.append(
            "event_id team-string conflicts that are NOT home/away flips "
            f"(n={parquet.get('event_id_real_team_conflicts_n')})"
        )
    if parquet.get("empty_event_id_rows", 0) > 0:
        blockers.append("empty event_id rows in parquet")
    if raw.get("empty_event_id_n", 0) > 0:
        warnings.append(f"raw open empty event_id rows: {raw['empty_event_id_n']}")

    snap_dups = int(parquet.get("duplicate_event_id_book_snapshot_grain_n") or 0)
    if snap_dups:
        warnings.append(
            f"event_id+book repeats across snapshot days (Path A grain): {snap_dups} — expected"
        )
    flips = int(parquet.get("home_away_flip_events_n") or 0)
    if flips:
        warnings.append(
            f"Odds API home/away flips across snapshot days (neutral-site quirk): "
            f"{flips} events — Lab SoT D fail-closed / consensus; not densify corruption"
        )
    if raw.get("identity_real_conflicts_n", 0) > 0:
        blockers.append(
            "raw open cross-day team-string conflicts that are NOT home/away flips "
            f"(n={raw['identity_real_conflicts_n']})"
        )
    if raw.get("identity_home_away_flips_n", 0) > 0:
        warnings.append(
            f"raw open home/away flips across days: {raw['identity_home_away_flips_n']}"
        )

    hard_out = 0
    lv = (parquet.get("line_validity") or {})
    for k in ("open_spread_home", "close_spread_home", "open_total", "close_total"):
        hard_out += int((lv.get(k) or {}).get("hard_outlier_n") or 0)
    if hard_out:
        warnings.append(f"hard line outliers (band check): {hard_out}")

    soft_out = 0
    for k in ("open_spread_home", "close_spread_home", "open_total", "close_total"):
        soft_out += int((lv.get(k) or {}).get("soft_outlier_n") or 0)
    if soft_out:
        warnings.append(f"soft line outliers (band check): {soft_out}")

    b7_rate = raw.get("b7_resolve_rate_both")
    if b7_rate is not None and b7_rate < 0.85:
        warnings.append(
            f"B7 both-sides resolve rate {b7_rate} (<0.85) — Lab omit grain, not lake fail"
        )

    status = "PASS" if not blockers else "FAIL"
    return {
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "scorecard_gate": (
            "ok_to_rerun_locked_scorecard"
            if status == "PASS"
            else "stop_diagnose_do_not_rebuild_model"
        ),
    }


def run_integrity(
    *,
    open_dir: Optional[Path] = None,
    close_dir: Optional[Path] = None,
    parquet_path: Optional[Path] = None,
) -> Dict[str, Any]:
    open_dir = open_dir or (WEB / "data" / "raw" / "odds" / "open")
    close_dir = close_dir or (WEB / "data" / "raw" / "odds" / "close")
    parquet_path = parquet_path or (
        WEB / "data" / "processed" / "ncaab_historical_odds_open_close.parquet"
    )

    receipt: Dict[str, Any] = {
        "task": "NCAAM Path A lake integrity (Scorecard v1.2 prep)",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "rules": {
            "no_odds_api": True,
            "no_fetch_historical": True,
            "no_credit_spend": True,
            "path": "A_only",
            "open_honesty_max_drift_days": MAX_DRIFT_DAYS,
        },
        "paths": {
            "open": str(open_dir.relative_to(ROOT)),
            "close": str(close_dir.relative_to(ROOT)),
            "parquet": str(parquet_path.relative_to(ROOT)),
        },
        "expected_from_densify_pr482": {
            "open_close_pockets": EXPECTED_OPEN_CLOSE,
            "pockets": [
                {"start": a, "end": b, "days": n} for a, b, n in EXPECTED_POCKETS
            ],
            "parquet_rows": EXPECTED_PARQUET_ROWS,
            "unique_events": EXPECTED_UNIQUE_EVENTS,
        },
    }
    receipt["pockets"] = check_pockets(open_dir, close_dir)
    receipt["honesty"] = check_honesty(open_dir, close_dir)
    receipt["raw_events"] = check_raw_events(open_dir)
    receipt["parquet"] = check_parquet(parquet_path)
    receipt["verdict"] = overall_verdict(receipt)
    return receipt


def render_ops_note(receipt: Dict[str, Any]) -> str:
    v = receipt["verdict"]
    p = receipt["pockets"]
    h = receipt["honesty"]
    q = receipt["parquet"]
    r = receipt["raw_events"]
    lines = [
        "# NCAAM Odds Path A — lake integrity (2026-09-04)",
        "",
        "**Task:** Kos Edge #14 / #3 — Scorecard v1.2 on CURRENT Path A lake",
        f"**As of:** `{receipt['as_of']}`",
        "**Rules:** NO Odds API · NO `fetch_historical` · NO credit spend · Path A only",
        f"**Verdict:** **{v['status']}**",
        f"**Scorecard gate:** `{v['scorecard_gate']}`",
        "",
        "> Integrity receipt only. Does **not** retune Lab cuts, thresholds, features,",
        "> or model. Does **not** light Edge Board / PLAY. B2 quarantine + board dark restated",
        "> after scorecard grades land (see Scorecard v1.2).",
        "",
        "## Inventory vs densify receipt (PR #482)",
        "",
        "| | Expected | Observed |",
        "|--|--------:|---------:|",
        f"| Open JSON | {EXPECTED_OPEN_CLOSE} | {p['open_count']} |",
        f"| Close JSON | {EXPECTED_OPEN_CLOSE} | {p['close_count']} |",
        f"| Open=close pairing | yes | {'yes' if p['open_equals_close_pairing'] else 'NO'} |",
        f"| Parquet rows | {EXPECTED_PARQUET_ROWS} | {q.get('n_rows')} |",
        f"| Unique events | {EXPECTED_UNIQUE_EVENTS} | {q.get('n_unique_events')} |",
        f"| Matches expected inventory | — | {'yes' if p.get('matches_expected_inventory') and q.get('matches_densify_inventory') else 'NO'} |",
        "",
        "### Pockets",
        "",
        "| Start | End | Expected | Open present | Missing |",
        "|-------|-----|--------:|-------------:|--------:|",
    ]
    for row in p.get("pockets") or []:
        lines.append(
            f"| {row['start']} | {row['end']} | {row['expected_days']} | "
            f"{row['open_present']} | {row['n_missing_open']} |"
        )
    lines += [
        "",
        f"Open span: `{p.get('open_first')}` → `{p.get('open_last')}`",
        "",
        "## Open/close timestamp honesty (>7d)",
        "",
        f"- Open honest: **{h['open_honest_n']}**",
        f"- Open dishonest (>7d): **{h['open_dishonest_n']}**",
        f"- Open missing timestamp: **{h['open_missing_timestamp_n']}**",
        f"- Close dishonest (>7d, informational): **{h['close_dishonest_n']}**",
        f"- Open honesty clean: **{h['open_honesty_clean']}**",
        "",
        "## Event / team identity (fail-closed)",
        "",
        f"- Unique event_ids in open files: `{r.get('n_unique_event_ids_open')}`",
        f"- Empty event_id rows (raw): `{r.get('empty_event_id_n')}`",
        f"- Cross-day team-string diffs (raw): `{r.get('identity_team_string_conflicts_n')}`",
        f"- Parquet event_id+book repeats (any open_time): `{q.get('duplicate_event_id_book_n')}`",
        f"- True dups (same open_time): `{q.get('duplicate_event_id_book_same_open_time_n')}` "
        f"(must be 0)",
        f"- Snapshot-grain repeats (diff open_time): `{q.get('duplicate_event_id_book_snapshot_grain_n')}` "
        f"(expected Path A)",
        f"- Home/away flips across snapshots: `{q.get('home_away_flip_events_n')}` "
        f"(Odds API neutral-site quirk)",
        f"- Real non-flip team conflicts: `{q.get('event_id_real_team_conflicts_n')}` "
        f"(must be 0)",
        f"- B7 both-sides resolve rate (Lab omit grain): `{r.get('b7_resolve_rate_both')}` "
        f"(home_unresolved={r.get('b7_home_unresolved_n')}, "
        f"away_unresolved={r.get('b7_away_unresolved_n')})",
        "",
        f"_Note:_ {r.get('note')}",
        "",
        "## Line / price validity + missingness + outliers",
        "",
        f"- Null counts (parquet): `{json.dumps(q.get('null_counts') or {})}`",
        f"- Empty event_id / home / away rows: "
        f"`{q.get('empty_event_id_rows')}` / `{q.get('empty_home_team_rows')}` / "
        f"`{q.get('empty_away_team_rows')}`",
        f"- open_time span: `{q.get('open_time_span')}`",
        "",
        "### Band checks (hygiene only — not Lab grade gates)",
        "",
        "```json",
        json.dumps(q.get("line_validity") or {}, indent=2),
        "```",
        "",
        "## Blockers / warnings",
        "",
    ]
    if v["blockers"]:
        for b in v["blockers"]:
            lines.append(f"- **BLOCKER:** {b}")
    else:
        lines.append("- Blockers: none")
    if v["warnings"]:
        for w in v["warnings"]:
            lines.append(f"- WARN: {w}")
    else:
        lines.append("- Warnings: none")
    lines += [
        "",
        "## Explicit non-actions",
        "",
        "- No Odds API / no `fetch_historical` / no Path B invent",
        "- No Lab cut / threshold / feature / peek-tune changes",
        "- No model rebuild (even if grades later land AMBER/RED)",
        "- No Edge Board / PLAY / Conf%",
        "",
        "## Machine receipt",
        "",
        "`data/ops/ncaam-odds-lake-integrity-20260904.receipt.json`",
        "",
        "## Next",
        "",
        "If verdict PASS → rematerialize Train-A/Test-A from current Path A parquet "
        "(locked cuts) → Scorecard v1.2 vs frozen v1.1 (same protocol gates).",
        "If FAIL → stop; diagnose here; do not rebuild model.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="NCAAM Path A lake integrity (no API)")
    parser.add_argument(
        "--write-ops-note",
        action="store_true",
        help="Write data/ops/ncaam-odds-lake-integrity-20260904.md",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print receipt only")
    args = parser.parse_args()

    receipt = run_integrity()
    out_json = ROOT / "data" / "ops" / "ncaam-odds-lake-integrity-20260904.receipt.json"
    out_md = ROOT / "data" / "ops" / "ncaam-odds-lake-integrity-20260904.md"

    if not args.dry_run:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if args.write_ops_note:
            out_md.write_text(render_ops_note(receipt), encoding="utf-8")

    summary = {
        "verdict": receipt["verdict"],
        "open_count": receipt["pockets"]["open_count"],
        "close_count": receipt["pockets"]["close_count"],
        "parquet_rows": receipt["parquet"].get("n_rows"),
        "unique_events": receipt["parquet"].get("n_unique_events"),
        "open_honesty_clean": receipt["honesty"]["open_honesty_clean"],
        "outputs": {
            "receipt": None if args.dry_run else str(out_json.relative_to(ROOT)),
            "ops_note": (
                None
                if args.dry_run or not args.write_ops_note
                else str(out_md.relative_to(ROOT))
            ),
        },
    }
    print(json.dumps(summary, indent=2))
    return 0 if receipt["verdict"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
