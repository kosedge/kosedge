"""Leakage-free historical evaluation contract (t4141u).

Retracts the unlocated n=2998 claim. Closest committed train n is 2992
(`data/ops/nfl-kav-supervised-retrain-v3.json`). The 570-row chronological
tail is CONTAMINATED for certification (same-week join / uncapped week /
default rest 7.0 / injury 0.0 still in production code).

This module does not recompute holdout metrics, does not invent a 6-game
drop list, and does not fabricate retrospective pregame predictions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
KAV_V3 = ROOT / "data/ops/nfl-kav-supervised-retrain-v3.json"

N_2998_STATUS = "RETRACTED"
N_CLAIMED_2998 = 2998
N_CLOSEST_TRAIN = 2992
N_ROWS_SEEN = 3562
N_TEST_CONTAMINATED = 570
DELTA_UNEXPLAINED = N_CLAIMED_2998 - N_CLOSEST_TRAIN

LEAKAGE_PATTERNS = (
    {
        "id": "same_week_join",
        "where": "scripts/nfl/historical_market_backtest.py",
        "pattern": "hf.week = sch.week",
        "effect": "same-week market features join the label week",
    },
    {
        "id": "uncapped_week_desc",
        "where": "services/model-service/src/services/nfl_matchup_features.py",
        "pattern": "ORDER BY priority, season DESC, week DESC",
        "effect": "matchup pack may pick a later week than the game",
    },
    {
        "id": "defaulted_rest",
        "where": "services/model-service/src/tasks.py",
        "pattern": "else 7.0",
        "effect": "silent rest=7.0",
    },
    {
        "id": "defaulted_injury",
        "where": "services/model-service/src/tasks.py",
        "pattern": 'impact_score", 0.0',
        "effect": "silent injury impact=0.0",
    },
)

AS_OF_RULE = (
    "Features for game week W may use PBP / injuries / rest only from games "
    "with kickoff_utc < game.kickoff_utc (strict lag; KAV as-of week W-1)."
)


def load_kav_v3(path: Path = KAV_V3) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def retraction(*, kav: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    doc = kav if kav is not None else load_kav_v3()
    metrics = dict(doc.get("metrics") or {})
    train = metrics.get("train_rows")
    test = metrics.get("test_rows")
    seen = doc.get("rows_seen")
    return {
        "claim": N_CLAIMED_2998,
        "status": N_2998_STATUS,
        "committed_artifact": None,
        "closest_train_n": train if train is not None else N_CLOSEST_TRAIN,
        "closest_test_n": test if test is not None else N_TEST_CONTAMINATED,
        "rows_seen": seen if seen is not None else N_ROWS_SEEN,
        "unexplained_delta_vs_2992": (
            None if train is None else int(N_CLAIMED_2998) - int(train)
        ),
        "do_not_invent_drop_list": True,
        "source": str(KAV_V3.relative_to(ROOT)) if KAV_V3.is_file() else None,
        "generated_at": doc.get("generated_at"),
        "model_version": doc.get("model_version"),
        "note": (
            "n=2998 is retracted. Do not treat it as a located sample. "
            f"Unexplained delta vs committed train is {DELTA_UNEXPLAINED} "
            "if train_rows=2992. Publish an itemized drop list before any "
            "future n=2998 claim."
        ),
    }


def split_contract(*, kav: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    doc = kav if kav is not None else load_kav_v3()
    metrics = dict(doc.get("metrics") or {})
    return {
        "method": "chronological last-slice holdout (HOLDOUT_FRACTION≈0.16)",
        "train_rows": metrics.get("train_rows"),
        "test_rows": metrics.get("test_rows"),
        "rows_seen": doc.get("rows_seen"),
        "train_seasons_documented": doc.get("train_start_season"),
        "test_status": "CONTAMINATED_DO_NOT_USE_FOR_CERT",
        "untouched_test_set": False,
        "recompute_holdout": "FORBIDDEN",
        "as_of_rule": AS_OF_RULE,
        "leakage_patterns_to_clear_before_cert": [p["id"] for p in LEAKAGE_PATTERNS],
    }


def evaluate_leakage_in_tree(root: Path = ROOT) -> Dict[str, Any]:
    """Read-only scan. Does not patch certified files."""
    violations: List[Dict[str, Any]] = []
    for spec in LEAKAGE_PATTERNS:
        path = root / spec["where"]
        if not path.is_file():
            violations.append({**spec, "present": False, "detail": "file missing"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        present = spec["pattern"] in text
        if present:
            violations.append({**spec, "present": True})
    return {
        "label": "LEAKAGE-EXPOSED" if violations else "LEAKAGE-CLEAR",
        "code_clear": not violations,
        "violations": violations,
        "holdout_570": "CONTAMINATED",
        "n_2998": retraction(),
    }


def contract_report(*, include_leakage_scan: bool = False) -> Dict[str, Any]:
    kav = load_kav_v3()
    doc: Dict[str, Any] = {
        "schema": "nfl-historical-eval-contract/v1",
        "retraction": retraction(kav=kav),
        "split": split_contract(kav=kav),
        "fabricated_pregame": False,
        "reconstructions_labelled": "RETROSPECTIVE",
    }
    if include_leakage_scan:
        doc["leakage"] = evaluate_leakage_in_tree()
    else:
        doc["leakage"] = {
            "label": "SCAN_OMITTED_FROM_WEEKLY_RECEIPT",
            "patterns": [p["id"] for p in LEAKAGE_PATTERNS],
        }
    return doc
