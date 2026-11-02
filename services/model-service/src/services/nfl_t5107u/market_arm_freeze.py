"""t5155u R5 Phase 1 — market arm freeze (metadata-only, before scoring).

Intersects sealed B1 admissible quotes with REG496. Applies KO−60, ≤24h,
deterministic latest-per-(game,book,market) selection, then median eligible
DK/FD mainline home spread → home margin by negation.

No odds pulls, late-quote substitution, or outcome-based selection.
Selection-limited DEV (2020–21 REG496). R2-C HOLD threshold unchanged.
No ML / Brier / log-loss. CERT=0. DRAFT≠merge.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Callable, Mapping, Sequence

from src.services.nfl_odds_reader import normalize_quote_timestamp

from .cohort_enforcement import (
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    PROFILE_FEATURE_RECON_REG496,
    REG496_IDENTITY_SHA256,
    OutcomeReadSpy,
    check_cohort_before_feature_output_finalization,
    check_cohort_before_target_outcome_loading,
    expected_profile_ids,
)
from .evaluator import (
    BENCHMARK_BOOKS,
    CUTOFF_MINUTES,
    MAX_QUOTE_AGE_HOURS,
    PER_SEASON_EXCLUSION_HOLD,
    home_margin_from_handicap,
    kickoff_minus_minutes,
    quote_age_hours,
    season_exclusion_hold,
)
from .metric_cohorts import DECLARED_REG_UNIVERSE, WILDCARD_2020_W18, cohort_sha256
from .recon_driver import sha256_file, sha256_text

TICKET = "t5155u"
PACKAGE = "B_R5_PHASE1_MARKET_ARM_FREEZE"
SCHEMA = "nfl-t5155u-market-arm-freeze-v1"
CERT_CANDIDATE = 0
OWNER_CLEAR_SHA8 = "659cd7d9"
COS_ORDER_SHA8 = "3e14602b"
COS_ACCEPT_700_SHA8 = "4b23584a"
ALEX_700_SHA8 = "f4147e76"
ALEX_RETURN_SHA8 = "7057e5a9"
TIP_700 = "12ccc482db54dd53bc6d79cea5f4af01c5540950"

B1_UNIVERSE_PATH = (
    "data/ops/nfl-t5119u-r2-owned-coverage/t5136u_B1/ADMISSIBLE_QUOTES_B1.jsonl"
)
B1_UNIVERSE_SHA256 = (
    "b4a3a4dbb8c5404d095b8095ec4018b96ceae532a50600d6d7f29f9d8fe950e6"
)
INTERSECTION_N = 96
INTERSECTION_BY_SEASON = {"2020": 41, "2021": 55}
INTERSECTION_ONE_BOOK_N = 5
INTERSECTION_TWO_BOOK_N = 91
INTERSECTION_MISSING_N = 400
INTERSECTION_BYTES_SHA256 = (
    "072e99e0c984fbd5ef87a2b419344c89148952a06b9185f52556147caeae70df"
)
INTERSECTION_IDENTITY_SHA256 = (
    "558fbfe5de0344925e389650c28b8c0c42546cd98013c0a55968f67de6e7242e"
)
REG496_ONLY_EXTRAS_VS_DEV437 = ("2020_05_BUF_TEN", "2021_15_WAS_PHI")
OUT_DIR = Path("data/ops/nfl-t5155u-r5-phase1")
FREEZE_NAME = "MARKET_ARM_FREEZE.json"
PROTECTED_B1 = frozenset({B1_UNIVERSE_PATH})
FORBIDDEN_SCORE_KEYS = frozenset(
    {
        "home_score",
        "away_score",
        "actual_margin",
        "brier",
        "logloss",
        "log_loss",
        "ml",
        "moneyline_p",
        "p_home_fair",
        "mae",
        "rmse",
    }
)
DEV_SEASONS = frozenset({2020, 2021})
MAINLINE_SPREAD = "spread"


class MarketArmFreezeRefuse(ValueError):
    """Fail-closed market-arm freeze. Not scoring. Not EVAL."""


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def _as_ids(values: Sequence[str] | None) -> list[str]:
    return [str(v) for v in (values or [])]


def _n_by_season(game_ids: Sequence[str]) -> dict[str, int]:
    counts = Counter(str(gid).split("_", 1)[0] for gid in game_ids)
    return dict(sorted(counts.items()))


def _week(game_id: str) -> int:
    parts = str(game_id).split("_")
    if len(parts) < 2:
        raise MarketArmFreezeRefuse(f"unparseable game_id {game_id}")
    return int(parts[1])


def _season(game_id: str) -> int:
    return int(str(game_id).split("_", 1)[0])


def assert_b1_universe_bytes(root: Path) -> str:
    path = Path(root) / B1_UNIVERSE_PATH
    if not path.is_file():
        raise MarketArmFreezeRefuse(f"B1 universe missing: {B1_UNIVERSE_PATH}")
    digest = sha256_file(path)
    if digest != B1_UNIVERSE_SHA256:
        raise MarketArmFreezeRefuse(
            f"B1 universe sha {digest} != pinned {B1_UNIVERSE_SHA256}"
        )
    return digest


def load_b1_quotes(root: Path) -> list[dict[str, Any]]:
    assert_b1_universe_bytes(root)
    rows: list[dict[str, Any]] = []
    path = Path(root) / B1_UNIVERSE_PATH
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, Mapping):
            raise MarketArmFreezeRefuse("B1 row is not an object")
        leaked = sorted(FORBIDDEN_SCORE_KEYS & set(row))
        if leaked:
            raise MarketArmFreezeRefuse(
                f"B1 quote carries scoring/outcome keys {leaked} — refuse"
            )
        rows.append(dict(row))
    if not rows:
        raise MarketArmFreezeRefuse("B1 universe empty")
    return rows


def _finite_spread(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def select_latest_eligible_spreads(
    quotes: Sequence[Mapping[str, Any]],
    allowed_ids: Sequence[str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Deterministic latest-per-(game,book,spread) after KO−60 and ≤24h."""
    allow = set(_as_ids(allowed_ids))
    excluded: list[dict[str, Any]] = []
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for raw in quotes:
        gid = str(raw.get("game_id") or "")
        if gid not in allow:
            continue
        season = int(raw.get("season") or _season(gid))
        if season not in DEV_SEASONS:
            excluded.append({"game_id": gid, "reason": "not_dev_selection"})
            continue
        if gid in WILDCARD_2020_W18:
            raise MarketArmFreezeRefuse(f"Wild Card leaked into market selection {gid}")
        if _week(gid) < 2:
            excluded.append({"game_id": gid, "reason": "week_lt_2"})
            continue
        book = str(raw.get("book") or "").lower()
        market = str(raw.get("market") or "").lower()
        if book not in BENCHMARK_BOOKS:
            excluded.append({"game_id": gid, "book": book, "reason": "book_not_benchmark"})
            continue
        if market != MAINLINE_SPREAD:
            continue
        spread = _finite_spread(raw.get("spread_home"))
        if spread is None:
            spread = _finite_spread(raw.get("line"))
        if spread is None:
            excluded.append({"game_id": gid, "book": book, "reason": "missing_spread"})
            continue
        kickoff = raw.get("kickoff_utc") or raw.get("kickoff")
        captured = normalize_quote_timestamp(raw.get("captured_at"), source_timezone="UTC")
        try:
            cutoff = kickoff_minus_minutes(kickoff, CUTOFF_MINUTES, source_timezone="UTC")
        except Exception as exc:
            excluded.append({"game_id": gid, "reason": f"unresolvable_kickoff:{exc}"})
            continue
        if captured is None:
            excluded.append({"game_id": gid, "reason": "unresolvable_captured_at"})
            continue
        if captured > cutoff:
            excluded.append(
                {
                    "game_id": gid,
                    "book": book,
                    "reason": "late_quote_post_cutoff",
                    "captured_at": captured.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "cutoff": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )
            continue
        age = quote_age_hours(captured, cutoff)
        if age > MAX_QUOTE_AGE_HOURS:
            excluded.append(
                {
                    "game_id": gid,
                    "book": book,
                    "reason": "quote_too_old",
                    "age_hours": age,
                }
            )
            continue
        buckets[(gid, book)].append(
            {
                "game_id": gid,
                "season": season,
                "week": int(raw.get("week") or _week(gid)),
                "book": book,
                "market": MAINLINE_SPREAD,
                "spread_home": float(spread),
                "home_margin": home_margin_from_handicap(spread),
                "captured_at": captured.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cutoff_utc": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "kickoff_utc": str(kickoff),
                "provenance": str(raw.get("provenance") or ""),
                "source": str(raw.get("source") or ""),
            }
        )
    latest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (gid, book), group in buckets.items():
        group.sort(
            key=lambda row: (
                row["captured_at"],
                row["provenance"],
                row["source"],
                f"{row['spread_home']:.6f}",
            )
        )
        latest[gid].append(group[-1])
    for gid in latest:
        latest[gid].sort(key=lambda row: row["book"])
    return dict(latest), excluded


def collapse_to_game_points(
    latest: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for gid in sorted(latest):
        books = list(latest[gid])
        spreads = [float(row["spread_home"]) for row in books]
        if not spreads:
            continue
        spread_med = float(median(spreads))
        points.append(
            {
                "game_id": gid,
                "season": int(books[0]["season"]),
                "week": int(books[0]["week"]),
                "books_used": [row["book"] for row in books],
                "book_count": len(books),
                "spread_home_median": spread_med,
                "home_margin": home_margin_from_handicap(spread_med),
                "captured_at_latest": max(row["captured_at"] for row in books),
                "cutoff_utc": books[0]["cutoff_utc"],
                "quotes": books,
            }
        )
    return points


def intersection_bytes_sha256(points: Sequence[Mapping[str, Any]]) -> str:
    canonical = [
        {
            "game_id": row["game_id"],
            "season": row["season"],
            "week": row["week"],
            "books_used": list(row["books_used"]),
            "book_count": row["book_count"],
            "spread_home_median": row["spread_home_median"],
            "home_margin": row["home_margin"],
            "captured_at_latest": row["captured_at_latest"],
            "cutoff_utc": row["cutoff_utc"],
        }
        for row in points
    ]
    return sha256_text(json.dumps(canonical, sort_keys=True, separators=(",", ":")))


def r2c_hold_disclosure(matched_ids: Sequence[str]) -> dict[str, Any]:
    """Disclose HOLD vs declared PBP REG. Threshold 0.30 is not changed."""
    by = _n_by_season(matched_ids)
    seasons: dict[str, Any] = {}
    any_hold = False
    for season in ("2020", "2021"):
        declared = int(DECLARED_REG_UNIVERSE[int(season)])
        matched = int(by.get(season, 0))
        body = season_exclusion_hold(declared, declared - matched)
        seasons[season] = body
        any_hold = any_hold or bool(body["hold"])
    return {
        "rule": "R2-C HOLD unchanged",
        "hold_threshold": PER_SEASON_EXCLUSION_HOLD,
        "threshold_unchanged": True,
        "declared_universe": "owned PBP REG (INPUT_BINDINGS n_reg_games)",
        "declared_pbp_reg": {str(k): v for k, v in DECLARED_REG_UNIVERSE.items() if k in DEV_SEASONS},
        "by_season": seasons,
        "any_hold": any_hold,
        "loosened": False,
        "eval": None,
        "scoring": None,
    }


def build_market_arm_freeze(
    *,
    root: Path,
    quotes: Sequence[Mapping[str, Any]] | None = None,
    reg496_ids: Sequence[str] | None = None,
    worker_a: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = Path(root)
    b1_sha = assert_b1_universe_bytes(repo)
    ids = _as_ids(reg496_ids if reg496_ids is not None else expected_profile_ids(
        PROFILE_FEATURE_RECON_REG496, repo
    ))
    if len(ids) != 496:
        raise MarketArmFreezeRefuse(f"REG496 n={len(ids)} != 496")
    if cohort_sha256(ids) != REG496_IDENTITY_SHA256:
        raise MarketArmFreezeRefuse("REG496 identity drifted vs 6429f859")
    loaded = list(quotes) if quotes is not None else load_b1_quotes(repo)
    for row in loaded:
        leaked = sorted(FORBIDDEN_SCORE_KEYS & set(row))
        if leaked:
            raise MarketArmFreezeRefuse(
                f"B1 quote carries scoring/outcome keys {leaked} — refuse"
            )
    latest, excluded = select_latest_eligible_spreads(loaded, ids)
    points = collapse_to_game_points(latest)
    matched = [row["game_id"] for row in points]
    missing = [gid for gid in ids if gid not in set(matched)]
    if any(_season(gid) not in DEV_SEASONS for gid in matched):
        raise MarketArmFreezeRefuse("non-DEV game survived selection-limited DEV freeze")
    one_book = sum(1 for row in points if row["book_count"] == 1)
    two_book = sum(1 for row in points if row["book_count"] >= 2)
    bytes_sha = intersection_bytes_sha256(points)
    identity_sha = cohort_sha256(matched)
    if quotes is None:
        if len(matched) != INTERSECTION_N or _n_by_season(matched) != INTERSECTION_BY_SEASON:
            raise MarketArmFreezeRefuse(
                f"intersection n drifted {len(matched)} {_n_by_season(matched)}"
            )
        if bytes_sha != INTERSECTION_BYTES_SHA256 or identity_sha != INTERSECTION_IDENTITY_SHA256:
            raise MarketArmFreezeRefuse("intersection bytes/identity drifted vs freeze pin")
        if one_book != INTERSECTION_ONE_BOOK_N or two_book != INTERSECTION_TWO_BOOK_N:
            raise MarketArmFreezeRefuse("one-book / two-book disclosure drifted")
        extra = sorted(set(REG496_ONLY_EXTRAS_VS_DEV437) - set(matched))
        if extra:
            raise MarketArmFreezeRefuse(f"REG496-only extras missing {extra}")
    payload = {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "package": PACKAGE,
        "cert_candidate": CERT_CANDIDATE,
        "draft": True,
        "verified": False,
        "scoring": None,
        "eval": None,
        "real_eval_executed": False,
        "odds_pulls": False,
        "late_quotes": False,
        "outcome_based_selection": False,
        "selection_limited": "DEV_2020_2021_REG496",
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "cos_order_sha8": COS_ORDER_SHA8,
        "cos_accept_700_sha8": COS_ACCEPT_700_SHA8,
        "alex_700_sha8": ALEX_700_SHA8,
        "alex_return_sha8": ALEX_RETURN_SHA8,
        "closed_700_tip": TIP_700,
        "b1_universe": {
            "path": B1_UNIVERSE_PATH,
            "sha256": b1_sha,
            "n_rows": len(loaded) if quotes is None else len(quotes),
        },
        "reg496": {
            "n": len(ids),
            "n_by_season": _n_by_season(ids),
            "identity_sha256": REG496_IDENTITY_SHA256,
        },
        "selection": {
            "books": sorted(BENCHMARK_BOOKS),
            "cutoff_minutes": CUTOFF_MINUTES,
            "max_quote_age_hours": MAX_QUOTE_AGE_HOURS,
            "market": MAINLINE_SPREAD,
            "dedup": "latest_per_game_book_spread after identical-fingerprint B1 seal",
            "home_margin": "negation of median eligible DK/FD mainline home spread",
            "performance_selection": False,
        },
        "intersection": {
            "n": len(matched),
            "n_by_season": _n_by_season(matched),
            "missing_n": len(missing),
            "missing_n_by_season": _n_by_season(missing),
            "one_book_n": one_book,
            "two_book_n": two_book,
            "identity_sha256": identity_sha,
            "bytes_sha256": bytes_sha,
            "game_ids": matched,
            "missing_game_ids": missing,
            "games": points,
        },
        "excluded_slots": excluded,
        "r2c_hold": r2c_hold_disclosure(matched),
        "worker_a_forecast_freeze": dict(worker_a)
        if worker_a
        else {
            "status": "PENDING",
            "note": "combine after A tips — do not race forecast/identity core",
        },
        "limitations": {
            "publication_timestamp_status": "unverified",
            "observation_timestamp_status": "unverified",
            "fit_label": "RETRO_FIT",
            "label": "RECONSTRUCTED",
            "production_causal_claim": False,
            "nfl_green": False,
            "eval": None,
            "cert_candidate": CERT_CANDIDATE,
        },
    }
    leaked = sorted(FORBIDDEN_SCORE_KEYS & set(payload))
    if leaked:
        raise MarketArmFreezeRefuse(f"freeze payload leaked scoring keys {leaked}")
    for row in points:
        leaked_row = sorted(FORBIDDEN_SCORE_KEYS & set(row))
        if leaked_row:
            raise MarketArmFreezeRefuse(f"game point leaked scoring keys {leaked_row}")
    return payload


def write_market_arm_freeze(
    payload: Mapping[str, Any],
    *,
    root: Path,
    dest: Path | None = None,
) -> Path:
    repo = Path(root)
    out = Path(dest) if dest is not None else repo / OUT_DIR / FREEZE_NAME
    try:
        rel = out.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        rel = None
    if rel in PROTECTED_B1:
        raise MarketArmFreezeRefuse(f"refusing to write protected original {rel}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def run_market_arm_freeze(
    *,
    root: Path | None = None,
    outcome_loader: OutcomeReadSpy | Callable[[], Any] | None = None,
    invoke_outcome_after_gates: bool = False,
    coverage_blocked: bool = False,
    finalize: bool = True,
    dest: Path | None = None,
    quotes: Sequence[Mapping[str, Any]] | None = None,
    worker_a: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Guarded freeze: A feature + outcome gates, then metadata write.

    Normal command leaves ``invoke_outcome_after_gates`` false — no scoring.
    """
    repo = _repo_root(root)
    spy = outcome_loader if outcome_loader is not None else OutcomeReadSpy()
    if getattr(spy, "reads", 0) not in (None, 0):
        raise MarketArmFreezeRefuse("outcome loader already read — refuse (join-before-gate)")
    reg_ids = expected_profile_ids(PROFILE_FEATURE_RECON_REG496, repo)
    try:
        assert_b1_universe_bytes(repo)
        feature = check_cohort_before_feature_output_finalization(
            PROFILE_FEATURE_RECON_REG496,
            reg_ids,
            candidate_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            root=repo,
        )
        outcome = check_cohort_before_target_outcome_loading(
            PROFILE_FEATURE_RECON_REG496,
            reg_ids,
            frozen_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            expected_bytes_sha=FEATURE_RECON_REG496_ARTIFACT_SHA256,
            coverage_blocked=coverage_blocked,
            outcome_loader=spy,
            root=repo,
        )
        if getattr(spy, "reads", 0) != 0:
            raise MarketArmFreezeRefuse("cohort gate invoked target-outcome loader")
        payload = build_market_arm_freeze(
            root=repo, quotes=quotes, reg496_ids=reg_ids, worker_a=worker_a
        )
        if invoke_outcome_after_gates:
            spy()
    except Exception:
        if getattr(spy, "reads", 0) != 0:
            raise MarketArmFreezeRefuse(
                "target scoring outcomes were read on refusal — refuse"
            )
        raise
    if invoke_outcome_after_gates:
        if getattr(spy, "reads", 0) != 1:
            raise MarketArmFreezeRefuse("expected one post-gate synthetic outcome read")
    elif getattr(spy, "reads", 0) != 0:
        raise MarketArmFreezeRefuse("target scoring outcomes were read before freeze")
    written = None
    if finalize:
        written = write_market_arm_freeze(payload, root=repo, dest=dest)
    return {
        "ok": True,
        "payload": payload,
        "dest": None if written is None else written.as_posix(),
        "feature_gate": dict(feature),
        "outcome_gate": dict(outcome),
        "outcome_loader_reads": int(getattr(spy, "reads", 0)),
        "outcome_loader_invoked_after_gates": bool(invoke_outcome_after_gates),
        "real_eval_executed": False,
        "cert_candidate": CERT_CANDIDATE,
        "n": payload["intersection"]["n"],
        "bytes_sha256": payload["intersection"]["bytes_sha256"],
        "identity_sha256": payload["intersection"]["identity_sha256"],
    }
