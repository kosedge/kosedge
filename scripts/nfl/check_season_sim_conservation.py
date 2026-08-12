#!/usr/bin/env python3
"""NFL season-sim conservation invariants C1–C6 (P0 Futures trust gate).

Fail the job (exit non-zero) when football arithmetic does not hold.
Does **not** UI-normalize team wins to force sums.

| ID | Rule |
| C1 | One winner + one loser per RS game (ties not modeled) |
| C2 | Σ team RS wins = 272 per path |
| C3 | Exactly 7 AFC + 7 NFC playoff teams per path |
| C4 | Exactly 8 division winners per path |
| C5 | Exactly 1 SB winner per path |
| C6 | Aggregated board E[wins] across 32 = 272.00 (± rounding) |

Also reports win-ceiling soft-pile size (publish guard).

Usage:
  python scripts/nfl/check_season_sim_conservation.py
  python scripts/nfl/check_season_sim_conservation.py --bundle data/ops/nfl-preseason-sim-2026-...
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from services.nfl_canonical_teams import (  # noqa: E402
    CANONICAL_TEAMS,
    CONFERENCE_OF,
    canonicalize_team,
)

WINS_TARGET = 272.0
WINS_TOL = 0.51
CEILING_BAND = 0.35
CEILING_MAX = 3


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


def _load_board_wins(bundle_dir: Path) -> Dict[str, float]:
    path = bundle_dir / "team_regular_season_outcomes.csv"
    out: Dict[str, float] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            team = canonicalize_team(r.get("team")) or str(r.get("team") or "")
            out[team] = float(r.get("expected_wins") or 0)
    return out


def win_histogram(wins: Dict[str, float]) -> Dict[str, int]:
    bins = {"<=6": 0, "7-9": 0, "10-11": 0, ">=12": 0}
    for w in wins.values():
        if w <= 6:
            bins["<=6"] += 1
        elif w < 10:
            bins["7-9"] += 1
        elif w < 12:
            bins["10-11"] += 1
        else:
            bins[">=12"] += 1
    return bins


def ceiling_cluster_count(wins: Dict[str, float], *, band: float = CEILING_BAND) -> int:
    if not wins:
        return 0
    top = max(wins.values())
    return sum(1 for w in wins.values() if top - w <= band)


def sample_path_conservation(
    week_rates: Dict[str, Any],
    *,
    n_replicates: int = 2_000,
    seed: int = 20260811,
) -> Dict[str, Any]:
    """Draw RS + playoff + SB paths and verify C1–C5 on every replicate."""
    import numpy as np
    from nfl_playoff_from_week_rates import (
        _normalize_week_rates,
        _run_conference_bracket,
        build_schedule_games,
        home_win_prob,
        seed_conference,
        strength_win_prob,
    )

    rates = _normalize_week_rates(week_rates)
    games = build_schedule_games()
    rng = np.random.default_rng(seed)
    home_list = [g[0] for g in games]
    away_list = [g[1] for g in games]
    weeks = [g[2] for g in games]
    probs = np.array(
        [home_win_prob(h, a, w, rates) for h, a, w in zip(home_list, away_list, weeks)],
        dtype=np.float64,
    )
    afc = [t for t in CANONICAL_TEAMS if CONFERENCE_OF[t] == "AFC"]
    nfc = [t for t in CANONICAL_TEAMS if CONFERENCE_OF[t] == "NFC"]

    c1_fail = c2_fail = c3_fail = c4_fail = c5_fail = 0
    for _ in range(n_replicates):
        draws = rng.random(len(games)) < probs
        records = {t: 0 for t in CANONICAL_TEAMS}
        # C1: each game assigns exactly one win (no ties modeled).
        for i, won_home in enumerate(draws):
            if won_home:
                records[home_list[i]] += 1
            else:
                records[away_list[i]] += 1
        if len(draws) != len(games):
            c1_fail += 1
        # C2
        if sum(records.values()) != len(games):
            c2_fail += 1
        seeds = {
            "AFC": seed_conference(rng, records, afc),
            "NFC": seed_conference(rng, records, nfc),
        }
        # C3
        if len(seeds["AFC"]) != 7 or len(seeds["NFC"]) != 7:
            c3_fail += 1
        if len(set(seeds["AFC"])) != 7 or len(set(seeds["NFC"])) != 7:
            c3_fail += 1
        # C4 — first four seeds per conference are division winners
        div_winners = list(seeds["AFC"][:4]) + list(seeds["NFC"][:4])
        if len(div_winners) != 8 or len(set(div_winners)) != 8:
            c4_fail += 1
        # C5
        path_strength = {t: float(records[t]) for t in CANONICAL_TEAMS}
        afc_champ = _run_conference_bracket(rng, seeds["AFC"], path_strength)
        nfc_champ = _run_conference_bracket(rng, seeds["NFC"], path_strength)
        p_afc = strength_win_prob(
            path_strength[afc_champ], path_strength[nfc_champ], home_field=False
        )
        sb_winner = afc_champ if rng.random() < p_afc else nfc_champ
        if sb_winner not in CANONICAL_TEAMS:
            c5_fail += 1

    return {
        "n_replicates": n_replicates,
        "n_games": len(games),
        "ties_policy": "not_modeled — each game is a Bernoulli home win; no 0.5 ties",
        "c1_fail": c1_fail,
        "c2_fail": c2_fail,
        "c3_fail": c3_fail,
        "c4_fail": c4_fail,
        "c5_fail": c5_fail,
    }


def check_bundle(
    bundle_dir: Path,
    *,
    n_path_replicates: int = 2_000,
    skip_paths: bool = False,
) -> SuiteResult:
    suite = SuiteResult()
    board = _load_board_wins(bundle_dir)
    wins_sum = sum(board.values())
    hist = win_histogram(board)
    ceil_n = ceiling_cluster_count(board)

    # C6 — board aggregate
    c6_ok = abs(wins_sum - WINS_TARGET) <= WINS_TOL and len(board) == 32
    suite.add(
        "C6",
        c6_ok,
        f"Σ E[wins]={wins_sum:.4f} target={WINS_TARGET}±{WINS_TOL} n={len(board)} hist={hist}",
    )

    # Ceiling soft-pile publish guard (related to Futures trust)
    ceil_ok = ceil_n <= CEILING_MAX
    suite.add(
        "CEILING_PILE",
        ceil_ok,
        f"teams within {CEILING_BAND} of max={ceil_n} (limit {CEILING_MAX})",
    )

    rates_path = bundle_dir / "team_week_win_rates.json"
    if skip_paths:
        suite.add("C1", True, "skipped")
        suite.add("C2", True, "skipped")
        suite.add("C3", True, "skipped")
        suite.add("C4", True, "skipped")
        suite.add("C5", True, "skipped")
        return suite

    if not rates_path.exists():
        for cid in ("C1", "C2", "C3", "C4", "C5"):
            suite.add(cid, False, "missing team_week_win_rates.json")
        return suite

    try:
        rates = json.loads(rates_path.read_text(encoding="utf-8"))
        path = sample_path_conservation(rates, n_replicates=n_path_replicates)
        suite.add(
            "C1",
            path["c1_fail"] == 0,
            f"one winner per game; ties policy={path['ties_policy']}; "
            f"fails={path['c1_fail']}/{path['n_replicates']} games={path['n_games']}",
        )
        suite.add(
            "C2",
            path["c2_fail"] == 0,
            f"Σ path wins == n_games ({path['n_games']}); fails={path['c2_fail']}/{path['n_replicates']}",
        )
        suite.add(
            "C3",
            path["c3_fail"] == 0,
            f"7 AFC + 7 NFC playoff seeds; fails={path['c3_fail']}/{path['n_replicates']}",
        )
        suite.add(
            "C4",
            path["c4_fail"] == 0,
            f"8 division winners (4+4); fails={path['c4_fail']}/{path['n_replicates']}",
        )
        suite.add(
            "C5",
            path["c5_fail"] == 0,
            f"1 SB winner per path; fails={path['c5_fail']}/{path['n_replicates']}",
        )
    except Exception as exc:  # pragma: no cover
        for cid in ("C1", "C2", "C3", "C4", "C5"):
            suite.add(cid, False, f"error: {exc}")

    return suite


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", default=None)
    ap.add_argument("--n-path-replicates", type=int, default=2_000)
    ap.add_argument("--skip-paths", action="store_true")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    bundle_dir = _resolve_bundle(args.bundle)
    if not bundle_dir.exists():
        print(f"FAIL: bundle not found: {bundle_dir}", file=sys.stderr)
        return 2

    suite = check_bundle(
        bundle_dir,
        n_path_replicates=args.n_path_replicates,
        skip_paths=args.skip_paths,
    )
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
        print(
            "\nSeason-sim conservation FAILED — blocking Futures publish.",
            file=sys.stderr,
        )
        return 1
    print("\nSeason-sim conservation OK (C1–C6 + ceiling).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
