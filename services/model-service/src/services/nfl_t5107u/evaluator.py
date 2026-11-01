"""Real-data evaluator scaffolding (CERT=0). No EXEC scoring in this package.

Market: KO−60 cutoff, ≤24h quote age, DK/FD, TZ contracts, p-bind refuse,
multiplicative de-vig. Metrics: paired ΔMAE primary; bootstrap B=10000
seed 20261101. Freeze forecast hashes + cohorts before outcome join.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from src.services.nfl_odds_comparison_harness import (
    UNBOUND_PROBABILITY_LINE,
    american_implied_prob,
    _probability_bound_to_quote,
)
from src.services.nfl_odds_reader import (
    EligibleQuote,
    ExcludedRow,
    join_quotes_at_cutoff,
    line_for_side,
    normalize_quote_timestamp,
)

from .builder import SCHEMA as FORECAST_SCHEMA
from .q2 import SEALED_SEASONS

CUTOFF_MINUTES = 60
MAX_QUOTE_AGE_HOURS = 24
BENCHMARK_BOOKS = frozenset({"draftkings", "fanduel"})
BOOT_B = 10000
BOOT_SEED = 20261101
MIN_N_REPORT = 100
PER_SEASON_EXCLUSION_HOLD = 0.30
LOGLOSS_CLIP = 1.0 / 8000.0
LABEL = "RESEARCH_CONSUMED_RETRO"
CERT_CANDIDATE = 0
COS_ONE_RUN_BIND = "COS_T5107U_ONE_RUN_BIND_NOT_ISSUED"

QUOTE_TOO_OLD = "quote_too_old"
BOOK_NOT_BENCHMARK = "book_not_benchmark"
MISSING_ML_PAIR = "missing_ml_pair"
UNBOUND_P = UNBOUND_PROBABILITY_LINE
SEASON_OUT_OF_BOUNDS = "season_out_of_bounds"


class EvalRefuse(ValueError):
    """Fail-closed evaluator. Never scores without bind + freeze."""


@dataclass
class FrozenCohort:
    forecast_sha256: str
    cohort_sha256: str
    game_ids: list[str]
    n: int
    sealed_before_outcome_join: bool
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "forecast_sha256": self.forecast_sha256,
            "cohort_sha256": self.cohort_sha256,
            "game_ids": list(self.game_ids),
            "n": self.n,
            "sealed_before_outcome_join": self.sealed_before_outcome_join,
            "label": LABEL,
            "cert_candidate": CERT_CANDIDATE,
        }


@dataclass
class MarketPoint:
    game_id: str
    season: int
    books_used: list[str]
    book_count: int
    market_margin: float | None
    spread_home: float | None
    p_home_fair: float | None
    p_compare: str
    captured_at: str | None
    cutoff: str
    notes: list[str] = field(default_factory=list)


def multiplicative_devig(q_home: float, q_away: float) -> float:
    """Fair home win probability. Never returns raw vig-inclusive as fair."""
    if q_home <= 0 or q_away <= 0:
        raise EvalRefuse("implied probs must be positive for multiplicative de-vig")
    return q_home / (q_home + q_away)


def kickoff_minus_minutes(kickoff: Any, minutes: int = CUTOFF_MINUTES, *, source_timezone: Any = None) -> datetime:
    dt = normalize_quote_timestamp(kickoff, source_timezone=source_timezone)
    if dt is None:
        raise EvalRefuse(f"kickoff unresolvable or missing timezone contract: {kickoff!r}")
    return dt - timedelta(minutes=int(minutes))


def quote_age_hours(captured: datetime, cutoff: datetime) -> float:
    return (cutoff - captured).total_seconds() / 3600.0


def home_margin_from_handicap(spread_home: float) -> float:
    """Odds API home handicap → home-margin sign before point-error comparison."""
    return -float(spread_home)


def freeze_forecast_cohort(forecast_payload: Mapping[str, Any]) -> FrozenCohort:
    """Hash forecasts + exact metric cohort before any outcome join."""
    if forecast_payload.get("eval") not in (None, {}):
        raise EvalRefuse("forecast payload already carries eval — refuse (join-before-freeze)")
    forecasts = list(forecast_payload.get("forecasts") or [])
    if not forecasts:
        raise EvalRefuse("no forecasts to freeze")
    for row in forecasts:
        if any(k in row for k in ("actual_margin", "home_score", "away_score", "outcome")):
            if row.get("actual_margin") is not None or row.get("home_score") is not None:
                raise EvalRefuse("forecast row already joined to target outcomes")
        if int(row.get("season") or 0) in SEALED_SEASONS:
            raise EvalRefuse(f"refusing 2024–26 forecast {row.get('game_id')}")
    game_ids = [str(row["game_id"]) for row in forecasts]
    if len(game_ids) != len(set(game_ids)):
        raise EvalRefuse("duplicate game_id in forecast cohort")
    body = {
        "schema_version": forecast_payload.get("schema_version") or FORECAST_SCHEMA,
        "forecasts": forecasts,
        "fit_policy": forecast_payload.get("fit_policy"),
        "if_arm": forecast_payload.get("if_arm"),
    }
    forecast_sha = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    cohort_sha = hashlib.sha256(
        json.dumps({"game_ids": game_ids}, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return FrozenCohort(
        forecast_sha256=forecast_sha,
        cohort_sha256=cohort_sha,
        game_ids=game_ids,
        n=len(game_ids),
        sealed_before_outcome_join=True,
        payload=dict(forecast_payload),
    )


def paired_mae(errors: Sequence[float]) -> float:
    if not errors:
        raise EvalRefuse("MAE on empty error list")
    return sum(abs(x) for x in errors) / len(errors)


def paired_rmse(errors: Sequence[float]) -> float:
    if not errors:
        raise EvalRefuse("RMSE on empty error list")
    return math.sqrt(sum(x * x for x in errors) / len(errors))


def paired_bias(errors: Sequence[float]) -> float:
    if not errors:
        raise EvalRefuse("bias on empty error list")
    return sum(errors) / len(errors)


def delta_mae(errors_a: Sequence[float], errors_b: Sequence[float]) -> float:
    if len(errors_a) != len(errors_b):
        raise EvalRefuse("paired ΔMAE requires identical per-metric games")
    return paired_mae(errors_a) - paired_mae(errors_b)


def bootstrap_ci(
    values: Sequence[float],
    *,
    stat=paired_mae,
    b: int = BOOT_B,
    seed: int = BOOT_SEED,
    clusters: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Game-unit (default) or week-cluster bootstrap. 95% interval."""
    if seed != BOOT_SEED:
        raise EvalRefuse(f"bootstrap seed is frozen at {BOOT_SEED}")
    if b != BOOT_B:
        raise EvalRefuse(f"bootstrap B is frozen at {BOOT_B}")
    n = len(values)
    rng = random.Random(seed)
    stats: list[float] = []
    if clusters is None:
        for _ in range(b):
            sample = [values[rng.randrange(n)] for _ in range(n)]
            stats.append(float(stat(sample)))
    else:
        if len(clusters) != n:
            raise EvalRefuse("cluster labels must align with values")
        by = defaultdict(list)
        for c, v in zip(clusters, values):
            by[c].append(v)
        keys = list(by)
        for _ in range(b):
            sample: list[float] = []
            for _k in keys:
                pick = keys[rng.randrange(len(keys))]
                sample.extend(by[pick])
            stats.append(float(stat(sample)))
    stats.sort()
    lo = stats[int(0.025 * (b - 1))]
    hi = stats[int(0.975 * (b - 1))]
    point = float(stat(values))
    verdict = "INCONCLUSIVE" if lo <= 0.0 <= hi else "CI_EXCLUDES_ZERO"
    return {
        "point": point,
        "ci95": [lo, hi],
        "B": b,
        "seed": seed,
        "n": n,
        "verdict": verdict,
        "note": "CI crossing zero = INCONCLUSIVE (not retune permission)",
    }


def reporting_class(n: int) -> str:
    if n < MIN_N_REPORT:
        return "DESCRIPTIVE_ONLY"
    return "REPORTABLE_NOT_AUTO_PASS"


def season_exclusion_hold(declared_n: int, excluded_n: int) -> dict[str, Any]:
    if declared_n <= 0:
        raise EvalRefuse("declared REG universe n must be > 0")
    rate = excluded_n / declared_n
    return {
        "declared_n": declared_n,
        "excluded_n": excluded_n,
        "exclusion_rate": rate,
        "hold_threshold": PER_SEASON_EXCLUSION_HOLD,
        "hold": rate > PER_SEASON_EXCLUSION_HOLD,
    }


def clip_logloss_p(p: float) -> tuple[float, bool]:
    if p < LOGLOSS_CLIP:
        return LOGLOSS_CLIP, True
    if p > 1.0 - LOGLOSS_CLIP:
        return 1.0 - LOGLOSS_CLIP, True
    return p, False


def select_market_quotes(
    quotes: Sequence[Mapping[str, Any]],
    games: Sequence[Mapping[str, Any]],
    *,
    source_timezone: Any = None,
    forecasts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Join owned quotes at KO−60 with ≤24h age; DK/FD only for the benchmark."""
    prepared_games: list[dict[str, Any]] = []
    for game in games:
        row = dict(game)
        season = int(row.get("season") or 0)
        if season in SEALED_SEASONS:
            raise EvalRefuse(f"refusing 2024–26 game {row.get('game_id')}")
        kickoff = row.get("kickoff") or row.get("kickoff_utc")
        cutoff = kickoff_minus_minutes(kickoff, CUTOFF_MINUTES, source_timezone=source_timezone)
        row["forecast_cutoff"] = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        row["kickoff"] = kickoff
        prepared_games.append(row)

    join = join_quotes_at_cutoff(
        quotes,
        prepared_games,
        None,
        source_timezone=source_timezone,
        per_game_cutoff_key="forecast_cutoff",
    )
    excluded = list(join.excluded)
    eligible: list[EligibleQuote] = []
    for quote in join.latest_per_book_market:
        if quote.season in SEALED_SEASONS:
            excluded.append(ExcludedRow(SEASON_OUT_OF_BOUNDS, f"season={quote.season}", {"game_id": quote.game_id}))
            continue
        captured = normalize_quote_timestamp(quote.captured_at, source_timezone=source_timezone or "UTC")
        cutoff = normalize_quote_timestamp(
            next(g["forecast_cutoff"] for g in prepared_games if str(g.get("game_id")) == quote.game_id),
            source_timezone="UTC",
        )
        if captured is None or cutoff is None:
            excluded.append(ExcludedRow("unresolvable_timestamp", "captured/cutoff", {"game_id": quote.game_id}))
            continue
        if quote_age_hours(captured, cutoff) > MAX_QUOTE_AGE_HOURS:
            excluded.append(
                ExcludedRow(
                    QUOTE_TOO_OLD,
                    f"age_h={quote_age_hours(captured, cutoff):.3f} > {MAX_QUOTE_AGE_HOURS}",
                    {"game_id": quote.game_id, "book": quote.book},
                )
            )
            continue
        if quote.book not in BENCHMARK_BOOKS:
            excluded.append(
                ExcludedRow(
                    BOOK_NOT_BENCHMARK,
                    f"book={quote.book} not in {sorted(BENCHMARK_BOOKS)}",
                    {"game_id": quote.game_id, "book": quote.book},
                )
            )
            continue
        eligible.append(quote)

    by_game: dict[str, list[EligibleQuote]] = defaultdict(list)
    for quote in eligible:
        by_game[quote.game_id].append(quote)

    forecast_by_id = {str(row.get("game_id")): row for row in (forecasts or [])}
    points: list[MarketPoint] = []
    for game in prepared_games:
        gid = str(game.get("game_id"))
        qs = by_game.get(gid, [])
        spreads = [q for q in qs if q.market == "spread" and q.line is not None]
        mls = [q for q in qs if q.market == "moneyline"]
        books = sorted({q.book for q in spreads} | {q.book for q in mls})
        market_margin = None
        spread_home = None
        if spreads:
            margins = [home_margin_from_handicap(q.spread_home if q.spread_home is not None else q.line) for q in spreads]
            market_margin = float(median(margins))
            spread_home = float(median([q.spread_home if q.spread_home is not None else q.line for q in spreads]))
        p_home = None
        p_compare = "unavailable"
        paired_ps: list[float] = []
        for book in sorted({q.book for q in mls}):
            sides = [q for q in mls if q.book == book]
            # Need both sides same book/event/timestamp
            by_ts: dict[str, list[EligibleQuote]] = defaultdict(list)
            for q in sides:
                by_ts[q.captured_at].append(q)
            for ts, group in by_ts.items():
                qh = next((q for q in group if q.price_home is not None), None)
                qa = next((q for q in group if q.price_away is not None), None)
                if qh is None or qa is None:
                    excluded.append(ExcludedRow(MISSING_ML_PAIR, f"{gid} {book} {ts}", {"game_id": gid}))
                    continue
                q_home = american_implied_prob(qh.price_home)
                q_away = american_implied_prob(qa.price_away)
                if q_home is None or q_away is None:
                    continue
                paired_ps.append(multiplicative_devig(q_home, q_away))
        if paired_ps:
            p_home = float(median(paired_ps))
            p_compare = "bound"
        forecast = forecast_by_id.get(gid) or {}
        markets = forecast.get("markets") or {}
        if markets.get("spread") or markets.get("moneyline"):
            # Reuse harness p-bind: refuse probability delta when line/side unbound.
            for q in spreads + mls:
                body = markets.get(q.market) or markets.get("spread" if q.market == "spread" else "moneyline") or {}
                if body and not _probability_bound_to_quote(q.market, body, body.get("prediction"), q):
                    p_compare = UNBOUND_P
                    p_home = None
                    break
        points.append(
            MarketPoint(
                game_id=gid,
                season=int(game.get("season") or 0),
                books_used=books,
                book_count=len(books),
                market_margin=market_margin,
                spread_home=spread_home,
                p_home_fair=p_home,
                p_compare=p_compare,
                captured_at=max((q.captured_at for q in qs), default=None),
                cutoff=str(game.get("forecast_cutoff")),
                notes=[
                    f"cutoff=KO-{CUTOFF_MINUTES}m",
                    f"max_quote_age_h={MAX_QUOTE_AGE_HOURS}",
                    f"books={sorted(BENCHMARK_BOOKS)}",
                    "de-vig=multiplicative qH/(qH+qA)",
                    f"one_or_two_book={'two' if len(books) >= 2 else 'one' if books else 'none'}",
                ],
            )
        )

    one = sum(1 for p in points if p.book_count == 1)
    two = sum(1 for p in points if p.book_count >= 2)
    return {
        "points": [p.__dict__ for p in points],
        "excluded": [e.as_dict() for e in excluded],
        "book_disclosure": {"one_book_games": one, "two_book_games": two, "books": sorted(BENCHMARK_BOOKS)},
        "cutoff_minutes": CUTOFF_MINUTES,
        "max_quote_age_hours": MAX_QUOTE_AGE_HOURS,
        "join_eligible_n": len(join.eligible),
        "eval": None,
        "scoring": None,
    }


def run_eval_score(
    frozen: FrozenCohort,
    outcomes: Mapping[str, Mapping[str, Any]],
    *,
    exec_bind: str | None = None,
    market_points: Sequence[Mapping[str, Any]] | None = None,
    bootstrap_b: int = BOOT_B,
    bootstrap_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Single EVAL score pass. Refused until CoS one-run bind after Alex GO."""
    if exec_bind != COS_ONE_RUN_BIND or exec_bind is None:
        raise EvalRefuse(
            "EXEC scoring refused until independent Alex preflight GO and "
            "CoS one-run bind of FROZEN_MANIFEST (G7). "
            f"got exec_bind={exec_bind!r}"
        )
    # The bind token is not issued in this package. The branch below is
    # scaffolding only; tests never pass the production bind.
    if not frozen.sealed_before_outcome_join:
        raise EvalRefuse("cohort was not sealed before outcome join")
    rehash = freeze_forecast_cohort(frozen.payload)
    if rehash.forecast_sha256 != frozen.forecast_sha256 or rehash.cohort_sha256 != frozen.cohort_sha256:
        raise EvalRefuse("forecast/cohort hash mismatch — refuse scoring")
    if bootstrap_b != BOOT_B or bootstrap_seed != BOOT_SEED:
        raise EvalRefuse("bootstrap hyperparameters are frozen")

    rows = []
    for gid in frozen.game_ids:
        out = outcomes.get(gid)
        if not out:
            continue
        if int(out.get("season") or 0) in SEALED_SEASONS:
            raise EvalRefuse(f"outcome {gid} is 2024–26")
        rows.append(gid)
    # Never invent ATS/OU probabilities from continuous draws.
    return {
        "refused": False,
        "n_joined": len(rows),
        "note": "scaffolding path only; token is not issued in t5107u builder package",
        "eval": "NOT_AUTHORIZED_IN_THIS_PACKAGE",
    }


def refuse_invented_ats_ou_probs(draws: Iterable[Any]) -> None:
    _ = list(draws)
    raise EvalRefuse("refusing invented ATS/OU probabilities or settlement claims from continuous draws")
