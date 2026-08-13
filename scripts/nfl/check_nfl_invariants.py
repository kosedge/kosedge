#!/usr/bin/env python3
"""NFL Truth Layer invariant suite (I1–I8).

Exit non-zero on any hard fail. Intended to **block publish / deploy** of
production NFL projection boards — dashboard-only warn is not enough.

Usage:
  python scripts/nfl/check_nfl_invariants.py
  python scripts/nfl/check_nfl_invariants.py --bundle data/ops/nfl-preseason-sim-2026-...
  python scripts/nfl/check_nfl_invariants.py --deliberate-break I3   # acceptance: must fail
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from services.nfl_canonical_teams import (  # noqa: E402
    CANONICAL_TEAMS,
    CONFERENCE_OF,
    canonicalize_team,
    missing_canonical_teams,
)

# I1: Σ wins ≈ 272 (no ties in current season engine — document if ties modeled)
WINS_TARGET = 272.0
WINS_TOL = 0.51
# I2
SB_TARGET = 1.0
SB_TOL = 0.01
# I3 / I4
PLAYOFF_CONF_TARGET = 7.0
PLAYOFF_CONF_TOL = 0.05


@dataclass
class CheckResult:
    id: str
    ok: bool
    detail: str


@dataclass
class SuiteResult:
    results: List[CheckResult] = field(default_factory=list)

    def add(self, check_id: str, ok: bool, detail: str) -> None:
        self.results.append(CheckResult(check_id, ok, detail))

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)


def _load_pointer() -> Dict[str, Any]:
    path = ROOT / "data" / "ops" / "nfl-web-launch-bundle.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_bundle(bundle: Optional[str]) -> Path:
    if bundle:
        p = Path(bundle)
        if not p.is_absolute():
            p = ROOT / p
        return p
    pointer = _load_pointer()
    bid = pointer.get("active_run_id") or pointer.get("bundle_id")
    if not bid:
        raise SystemExit("pointer missing active_run_id/bundle_id")
    return ROOT / "data" / "ops" / str(bid)


def _load_team_rows(bundle_dir: Path) -> List[Dict[str, str]]:
    path = bundle_dir / "team_regular_season_outcomes.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def is_valid_american(price: Any) -> bool:
    try:
        p = float(price)
    except (TypeError, ValueError):
        return False
    if not (p == p) or p == 0:  # NaN / zero
        return False
    return abs(p) >= 100.0


def recompute_edge(kei: float, market: float) -> float:
    return float(kei) - float(market)


def check_bundle(
    bundle_dir: Path,
    *,
    deliberate_break: Optional[str] = None,
    edge_samples: Optional[Sequence[Dict[str, float]]] = None,
) -> SuiteResult:
    suite = SuiteResult()
    rows = _load_team_rows(bundle_dir)
    pointer = _load_pointer()
    active = str(pointer.get("active_run_id") or pointer.get("bundle_id") or "")

    # Normalize + optional deliberate I3 break
    playoff_by_team: Dict[str, float] = {}
    wins_sum = 0.0
    sb_sum = 0.0
    teams_present: List[str] = []
    for r in rows:
        team = canonicalize_team(r.get("team")) or str(r.get("team") or "")
        teams_present.append(team)
        wins_sum += float(r.get("expected_wins") or 0)
        sb_sum += float(r.get("super_bowl_win_prob") or 0)
        playoff_by_team[team] = float(r.get("playoff_prob") or 0)

    if deliberate_break == "I3":
        # Inflate one AFC team so conference sum leaves ±0.05 band.
        for t in CANONICAL_TEAMS:
            if CONFERENCE_OF[t] == "AFC":
                playoff_by_team[t] = playoff_by_team.get(t, 0.0) + 0.5
                break

    sum_afc = sum(
        playoff_by_team.get(t, 0.0)
        for t in CANONICAL_TEAMS
        if CONFERENCE_OF[t] == "AFC"
    )
    sum_nfc = sum(
        playoff_by_team.get(t, 0.0)
        for t in CANONICAL_TEAMS
        if CONFERENCE_OF[t] == "NFC"
    )

    # I1 — wins sum (ties not modeled → plain wins)
    i1_ok = abs(wins_sum - WINS_TARGET) <= WINS_TOL
    suite.add(
        "I1",
        i1_ok,
        f"Σ wins={wins_sum:.4f} target={WINS_TARGET}±{WINS_TOL} "
        f"(ties not modeled — wins only)",
    )

    # I2 — SB
    i2_ok = abs(sb_sum - SB_TARGET) <= SB_TOL
    suite.add("I2", i2_ok, f"Σ SB={sb_sum:.6f} target={SB_TARGET}±{SB_TOL}")

    # I3 / I4 — playoff conference sums
    i3_ok = abs(sum_afc - PLAYOFF_CONF_TARGET) <= PLAYOFF_CONF_TOL
    suite.add(
        "I3",
        i3_ok,
        f"Σ AFC playoff={sum_afc:.6f} target={PLAYOFF_CONF_TARGET}±{PLAYOFF_CONF_TOL}",
    )
    i4_ok = abs(sum_nfc - PLAYOFF_CONF_TARGET) <= PLAYOFF_CONF_TOL
    suite.add(
        "I4",
        i4_ok,
        f"Σ NFC playoff={sum_nfc:.6f} target={PLAYOFF_CONF_TARGET}±{PLAYOFF_CONF_TOL}",
    )

    # I5 — American ML validity (sample fixture + any quality_checks odds)
    bad_prices = [-66, 0, 50, -50, None, "abc"]
    good_prices = [-110, 105, -1500, 250]
    i5_ok = all(not is_valid_american(p) for p in bad_prices) and all(
        is_valid_american(p) for p in good_prices
    )
    # Also scan optional board sample in quality_checks
    qc_path = bundle_dir / "quality_checks.json"
    if qc_path.exists():
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        for price in qc.get("sample_american_mls") or []:
            if not is_valid_american(price):
                i5_ok = False
    suite.add(
        "I5",
        i5_ok,
        "American MLs: reject |price|<100 and non-finite; accept standard lines",
    )

    # I6 — edge arithmetic sample
    samples = list(edge_samples or [])
    if not samples:
        samples = [
            {"kei": -3.5, "market": -2.5, "edge": -1.0},
            {"kei": 47.5, "market": 45.5, "edge": 2.0},
            {"kei": 0.55, "market": 0.48, "edge": 0.07},
        ]
    i6_ok = True
    i6_details = []
    for s in samples:
        got = recompute_edge(s["kei"], s["market"])
        exp = float(s["edge"])
        match = abs(got - exp) <= 1e-6
        i6_ok = i6_ok and match
        i6_details.append(f"{s['kei']}-{s['market']}=>{got:.6g} (exp {exp})")
    suite.add("I6", i6_ok, "sampled edges: " + "; ".join(i6_details))

    # I7 — 32 teams present (canonical, no LA/LAR double)
    unique = sorted({canonicalize_team(t) or t for t in teams_present})
    missing = missing_canonical_teams(unique)
    has_both_la = "LA" in teams_present and "LAR" in {
        canonicalize_team(t) or t for t in teams_present
    }
    # After canonicalize, exactly 32 and no missing
    i7_ok = len(unique) == 32 and not missing and "LA" not in unique
    suite.add(
        "I7",
        i7_ok,
        f"unique_canonical={len(unique)} missing={missing} raw_n={len(rows)}",
    )

    # I8 — active_run aligned
    bundle_name = bundle_dir.name
    summary_path = bundle_dir / "run_summary.json"
    summary_run = None
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary_run = summary.get("web_bundle_id") or summary.get("active_run_id")
    # I8 — bundle self-id. Pointer alignment is required only after the
    # pointer already names this bundle. Pre-flip publish of a candidate
    # must not fail I8 or the pointer can never move.
    bundle_self = summary_run in (None, "", bundle_name)
    if active == bundle_name:
        i8_ok = bundle_self
        i8_detail = (
            f"active_run_id={active!r} bundle={bundle_name!r} "
            f"summary_run={summary_run!r}"
        )
    else:
        i8_ok = bundle_self
        i8_detail = (
            f"candidate bundle={bundle_name!r} summary_run={summary_run!r} "
            f"(pointer still {active!r}; pre-flip)"
        )
    suite.add("I8", i8_ok, i8_detail)

    # Kickoff smoke (schedule pack): NE–SEA + 4 others appear once each as unique games
    try:
        from nfl_playoff_from_week_rates import build_schedule_games

        games = build_schedule_games()
        smoke = {
            ("NE", "SEA"),
            ("KC", "LAC"),
            ("PHI", "DAL"),
            ("BUF", "MIA"),
            ("SF", "LAR"),
        }
        pairs = {(a, h) for h, a, _w in games} | {(h, a) for h, a, _w in games}
        # games are (home, away, week); check unordered matchup presence
        found = 0
        for away, home in smoke:
            if (home, away) in {(h, a) for h, a, _ in games} or (
                away,
                home,
            ) in {(h, a) for h, a, _ in games}:
                found += 1
        kickoff_ok = found == len(smoke) and len(games) >= 250
        suite.add(
            "KICKOFF_SMOKE",
            kickoff_ok,
            f"wall-chart unique games={len(games)} smoke_found={found}/{len(smoke)}",
        )
    except Exception as exc:  # pragma: no cover
        suite.add("KICKOFF_SMOKE", False, f"error: {exc}")

    # STRENGTH_ALIGN — board expected_wins ≈ Σ week win rates ≈ win_dist.mean
    # (single production strength path; DET leftover was hierarchical dist μ).
    rates_path = bundle_dir / "team_week_win_rates.json"
    win_dist_path = bundle_dir / "team_win_distributions.json"
    if rates_path.exists():
        try:
            from nfl_playoff_from_week_rates import (  # noqa: WPS433
                _normalize_week_rates,
                season_wins_from_rates,
            )

            rates = _normalize_week_rates(
                json.loads(rates_path.read_text(encoding="utf-8"))
            )
            rate_wins = season_wins_from_rates(rates)
            board_wins = {
                canonicalize_team(r.get("team")) or str(r.get("team") or ""): float(
                    r.get("expected_wins") or 0
                )
                for r in rows
            }
            mismatches = []
            for t in CANONICAL_TEAMS:
                bw = board_wins.get(t)
                rw = rate_wins.get(t)
                if bw is None or rw is None:
                    mismatches.append(f"{t}:missing")
                    continue
                if abs(bw - rw) > 0.35:
                    mismatches.append(f"{t}:{rw:.2f}vs{bw:.2f}")
            dist_mismatches = []
            if win_dist_path.exists():
                for dist in json.loads(win_dist_path.read_text(encoding="utf-8")):
                    t = canonicalize_team(str(dist.get("team") or "")) or str(
                        dist.get("team") or ""
                    )
                    if t not in CANONICAL_TEAMS:
                        continue
                    bw = board_wins.get(t)
                    if bw is None:
                        continue
                    mean = float(dist.get("mean") or 0)
                    if abs(mean - bw) > 0.35:
                        dist_mismatches.append(f"{t}:{mean:.2f}vs{bw:.2f}")
            align_ok = (
                not mismatches and not dist_mismatches and "LA" not in rates
            )
            detail = (
                "week-rate Σ + win_dist.mean ≈ board expected_wins (±0.35); no raw LA key"
                if align_ok
                else f"rate={mismatches[:6]} dist={dist_mismatches[:6]}"
            )
            suite.add("STRENGTH_ALIGN", align_ok, detail)
        except Exception as exc:  # pragma: no cover
            suite.add("STRENGTH_ALIGN", False, f"error: {exc}")
    else:
        suite.add("STRENGTH_ALIGN", False, "missing team_week_win_rates.json")

    # I9 / week1_reg_count — Edge Board Week 1 must equal schedule pack (16).
    # Silent drops (board shows 13) are a hard fail for publish/deploy.
    try:
        week1_mod_path = ROOT / "scripts" / "nfl" / "check_edge_board_week1.py"
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "check_edge_board_week1", week1_mod_path
        )
        assert spec and spec.loader
        week1_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(week1_mod)
        w1_results = week1_mod.check_week1()
        for check_id, passed, detail in w1_results:
            suite.add(check_id, passed, detail)
    except Exception as exc:  # pragma: no cover
        suite.add("WEEK1_REG_COUNT", False, f"error: {exc}")

    return suite


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", default=None, help="Bundle dir (default: active_run)")
    ap.add_argument(
        "--deliberate-break",
        default=None,
        choices=["I3"],
        help="Force a known invariant failure (acceptance test)",
    )
    ap.add_argument("--json-out", default=None, help="Write results JSON")
    args = ap.parse_args(argv)

    bundle_dir = _resolve_bundle(args.bundle)
    if not bundle_dir.exists():
        print(f"FAIL: bundle not found: {bundle_dir}", file=sys.stderr)
        return 2

    suite = check_bundle(bundle_dir, deliberate_break=args.deliberate_break)
    for r in suite.results:
        flag = "PASS" if r.ok else "FAIL"
        print(f"{flag} {r.id}: {r.detail}")

    if args.json_out:
        out = {
            "bundle": str(bundle_dir),
            "ok": suite.ok,
            "results": [
                {"id": r.id, "ok": r.ok, "detail": r.detail} for r in suite.results
            ],
        }
        Path(args.json_out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    if not suite.ok:
        print("\nNFL Truth Layer invariants FAILED — blocking publish/deploy.", file=sys.stderr)
        return 1
    print("\nNFL Truth Layer invariants OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
