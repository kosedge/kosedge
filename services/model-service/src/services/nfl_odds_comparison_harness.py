"""Synthetic NFL forecast ↔ owned-odds comparison harness (CERT=0).

Connects the Package A reader (`nfl_odds_reader.join_quotes_at_cutoff`) to a
frozen forecast file + matching owned-odds manifest. Reuses the reader's
identity, cutoff, sign, and exclusion contract. Does not rewrite the reader.

Synthetic forecasts and synthetic outcomes only. No paid Odds, no 2024–25
open, no fitting, no scoring, no real-outcome EVAL. Invalid inputs are
refused or excluded — comparisons are never fabricated.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_odds_reader import (
    AMBIGUOUS_IDENTITY,
    PERMITTED_SEASONS,
    SIGN_CONVENTION,
    EligibleQuote,
    ExcludedRow,
    canonical_market,
    join_quotes_at_cutoff,
    line_for_side,
    resolve_team_identity,
)

FORECAST_SCHEMA = "nfl-odds-comparison-forecast-v1"
MANIFEST_SCHEMA = "nfl-odds-comparison-manifest-v1"
REPORT_SCHEMA = "nfl-odds-comparison-report-v1"
SYNTHETIC_LABEL = "SYNTHETIC"
SYNTHETIC_PURPOSE = "synthetic_comparison_only"
CERT_CANDIDATE = 0

READER_PATH = "services/model-service/src/services/nfl_odds_reader.py"
HARNESS_PATH = "services/model-service/src/services/nfl_odds_comparison_harness.py"
PACKAGE_A_HEAD = "f6b5b4c3ec4021fc64d86a36c863b483246be78b"
CLEAR_TIP = "4f3b9666"
ALEX_PASS_RO = "db8d27a2"
COS_ACCEPT = "7f9f7918"

MISSING_PROBABILITY = "missing_probability"
INCOMPATIBLE_LINE = "incompatible_line"
DUPLICATE_GAME = "duplicate_game"
NO_ELIGIBLE_QUOTE = "no_eligible_quote"
MISSING_FORECAST = "missing_forecast"
NOT_SYNTHETIC = "not_synthetic"
INVALID_SCHEMA = "invalid_schema"
REAL_OUTCOME_REFUSED = "real_outcome_refused"
PAID_ODDS_REFUSED = "paid_odds_refused"
SEASON_OUT_OF_BOUNDS = "season_out_of_bounds"

MARKET_KEYS = ("spread", "total", "moneyline")
P_FIELDS = {
    "spread": ("p_home_cover", "p"),
    "total": ("p_over", "p"),
    "moneyline": ("p_home", "p"),
}

FORBIDDEN_SOURCE_TOKENS = (
    "the-odds-api.com",
    "odds-api",
    "paid-odds",
    "paid_odds",
    "/seals/",
    "w8_first_seal",
)

class HarnessRefusal(ValueError):
    """Whole-run refusal. No comparison rows are emitted."""

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> Dict[str, Any]:
        return {
            "refused": True,
            "reason": self.reason,
            "detail": self.detail,
            "comparisons": [],
            "cert_candidate": CERT_CANDIDATE,
            "label": SYNTHETIC_LABEL,
        }


@dataclass
class ComparisonRow:
    game_id: str
    event_id: str
    season: int
    game_date: str
    home_abbr: str
    away_abbr: str
    book: str
    market: str
    forecast_line: Optional[float]
    market_line: Optional[float]
    line_delta: Optional[float]
    forecast_p: float
    implied_p: Optional[float]
    p_delta: Optional[float]
    home_line: Optional[float]
    away_line: Optional[float]
    price: Optional[float]
    captured_at: str
    forecast_cutoff: str
    quote_provenance: str
    forecast_provenance: str
    sign_convention: str = SIGN_CONVENTION
    synthetic_outcome: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonReport:
    schema_version: str = REPORT_SCHEMA
    label: str = SYNTHETIC_LABEL
    cert_candidate: int = CERT_CANDIDATE
    purpose: str = SYNTHETIC_PURPOSE
    refused: bool = False
    refuse_reason: Optional[str] = None
    refuse_detail: Optional[str] = None
    generated_at_utc: str = ""
    code_pin: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    join: Dict[str, Any] = field(default_factory=dict)
    comparisons: List[ComparisonRow] = field(default_factory=list)
    excluded: List[ExcludedRow] = field(default_factory=list)
    reason_tallies: Dict[str, int] = field(default_factory=dict)
    identical_duplicate_n: int = 0
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "label": self.label,
            "cert_candidate": self.cert_candidate,
            "purpose": self.purpose,
            "refused": self.refused,
            "refuse_reason": self.refuse_reason,
            "refuse_detail": self.refuse_detail,
            "generated_at_utc": self.generated_at_utc,
            "code_pin": self.code_pin,
            "inputs": self.inputs,
            "join": self.join,
            "comparison_n": len(self.comparisons),
            "excluded_n": len(self.excluded),
            "identical_duplicate_n": self.identical_duplicate_n,
            "reason_tallies": dict(self.reason_tallies),
            "comparisons": [row.as_dict() for row in self.comparisons],
            "excluded": [item.as_dict() for item in self.excluded],
            "notes": list(self.notes),
            "eval": None,
            "scoring": None,
            "fitting": None,
        }


def american_implied_prob(price: Any) -> Optional[float]:
    """Raw implied probability from an American price. Does not remove vig."""
    if price is None or price == "":
        return None
    try:
        value = float(price)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return abs(value) / (abs(value) + 100.0)
    if value > 0:
        return 100.0 / (value + 100.0)
    return None


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def grade_synthetic_outcome(
    market: str,
    line: Optional[float],
    home_score: Any,
    away_score: Any,
) -> Optional[str]:
    """Label a synthetic result. Push/tie when the line is exactly hit."""
    home = _as_float(home_score)
    away = _as_float(away_score)
    if home is None or away is None:
        return None
    margin = home - away
    total = home + away
    code = canonical_market(market)
    if code == "spread":
        if line is None:
            return None
        adj = margin + line
        if adj == 0:
            return "push"
        return "home_cover" if adj > 0 else "away_cover"
    if code == "total":
        if line is None:
            return None
        if total == line:
            return "push"
        return "over" if total > line else "under"
    if code == "moneyline":
        if margin == 0:
            return "tie"
        return "home" if margin > 0 else "away"
    return None


def _git(*args: str) -> str:
    root = Path(__file__).resolve().parents[4]
    try:
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HarnessRefusal(INVALID_SCHEMA, f"{path}: {exc}") from exc
    except OSError as exc:
        raise HarnessRefusal(INVALID_SCHEMA, f"unreadable {path}: {exc}") from exc


def _dump_scan(payload: Any) -> str:
    return json.dumps(payload, default=str).casefold()


def _refuse_if_paid_or_protected(payload: Mapping[str, Any], *, where: str) -> None:
    blob = _dump_scan(payload)
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in blob:
            raise HarnessRefusal(PAID_ODDS_REFUSED, f"{where} cites {token}")


def _require_synthetic_header(payload: Mapping[str, Any], *, schema: str, where: str) -> None:
    if not isinstance(payload, Mapping):
        raise HarnessRefusal(INVALID_SCHEMA, f"{where} must be a JSON object")
    if str(payload.get("schema_version") or "") != schema:
        raise HarnessRefusal(
            INVALID_SCHEMA,
            f"{where} schema_version must be {schema!r}, got {payload.get('schema_version')!r}",
        )
    if str(payload.get("label") or "") != SYNTHETIC_LABEL:
        raise HarnessRefusal(NOT_SYNTHETIC, f"{where} label must be {SYNTHETIC_LABEL}")
    if str(payload.get("purpose") or "") != SYNTHETIC_PURPOSE:
        raise HarnessRefusal(NOT_SYNTHETIC, f"{where} purpose must be {SYNTHETIC_PURPOSE}")
    try:
        cert = int(payload.get("cert_candidate"))
    except (TypeError, ValueError):
        cert = None
    if cert != CERT_CANDIDATE:
        raise HarnessRefusal(NOT_SYNTHETIC, f"{where} cert_candidate must be 0")
    if str(payload.get("sport") or "nfl").casefold() != "nfl":
        raise HarnessRefusal(INVALID_SCHEMA, f"{where} sport must be nfl")
    _refuse_if_paid_or_protected(payload, where=where)


def _season_or_refuse(value: Any, *, where: str) -> int:
    try:
        season = int(value)
    except (TypeError, ValueError) as exc:
        raise HarnessRefusal(SEASON_OUT_OF_BOUNDS, f"{where} season={value!r}") from exc
    if season not in PERMITTED_SEASONS:
        raise HarnessRefusal(
            SEASON_OUT_OF_BOUNDS,
            f"{where} season {season} is outside {sorted(PERMITTED_SEASONS)}",
        )
    return season


def _forecast_p(market: str, body: Mapping[str, Any]) -> Optional[float]:
    for key in P_FIELDS.get(canonical_market(market), ("p",)):
        value = _as_float(body.get(key))
        if value is not None:
            return value
    return None


def _forecast_line(market: str, body: Mapping[str, Any]) -> Optional[float]:
    code = canonical_market(market)
    if code == "spread":
        return _as_float(body.get("prediction") if body.get("prediction") not in (None, "") else body.get("spread_home"))
    if code == "total":
        return _as_float(body.get("prediction") if body.get("prediction") not in (None, "") else body.get("total_points"))
    return None


def _identity_key(row: Mapping[str, Any]) -> Tuple[str, str, str]:
    home = resolve_team_identity(str(row.get("home_team") or row.get("home") or row.get("home_abbr") or ""))
    away = resolve_team_identity(str(row.get("away_team") or row.get("away") or row.get("away_abbr") or ""))
    day = str(row.get("game_date") or row.get("kickoff") or "")[:10]
    return day, home.abbr or home.raw, away.abbr or away.raw


def load_forecast_file(path: Path) -> Dict[str, Any]:
    payload = _read_json(Path(path))
    _require_synthetic_header(payload, schema=FORECAST_SCHEMA, where="forecast file")
    forecasts = payload.get("forecasts")
    if not isinstance(forecasts, list) or not forecasts:
        raise HarnessRefusal(INVALID_SCHEMA, "forecast file needs a non-empty forecasts list")
    outcomes = payload.get("synthetic_outcomes") or []
    if outcomes is None:
        outcomes = []
    if not isinstance(outcomes, list):
        raise HarnessRefusal(INVALID_SCHEMA, "synthetic_outcomes must be a list")
    for idx, row in enumerate(forecasts):
        if not isinstance(row, Mapping):
            raise HarnessRefusal(INVALID_SCHEMA, f"forecasts[{idx}] is not an object")
        _season_or_refuse(row.get("season"), where=f"forecasts[{idx}]")
        if not row.get("game_id"):
            raise HarnessRefusal(INVALID_SCHEMA, f"forecasts[{idx}] missing game_id")
        if not isinstance(row.get("markets"), Mapping) or not row.get("markets"):
            raise HarnessRefusal(INVALID_SCHEMA, f"forecasts[{idx}] missing markets")
    for idx, row in enumerate(outcomes):
        if not isinstance(row, Mapping):
            raise HarnessRefusal(INVALID_SCHEMA, f"synthetic_outcomes[{idx}] is not an object")
        source = str(row.get("source") or "").casefold()
        if source != "synthetic":
            raise HarnessRefusal(
                REAL_OUTCOME_REFUSED,
                f"synthetic_outcomes[{idx}] source must be 'synthetic', got {row.get('source')!r}",
            )
        if row.get("real") or str(row.get("kind") or "").casefold() in {"real", "actual", "nflverse"}:
            raise HarnessRefusal(REAL_OUTCOME_REFUSED, f"synthetic_outcomes[{idx}] looks like a real result")
    return payload


def load_odds_manifest(path: Path) -> Dict[str, Any]:
    payload = _read_json(Path(path))
    _require_synthetic_header(payload, schema=MANIFEST_SCHEMA, where="odds manifest")
    games = payload.get("games")
    quotes = payload.get("quotes")
    if not isinstance(games, list) or not games:
        raise HarnessRefusal(INVALID_SCHEMA, "odds manifest needs a non-empty games list")
    if not isinstance(quotes, list) or not quotes:
        raise HarnessRefusal(INVALID_SCHEMA, "odds manifest needs a non-empty quotes list")
    for idx, game in enumerate(games):
        if not isinstance(game, Mapping):
            raise HarnessRefusal(INVALID_SCHEMA, f"games[{idx}] is not an object")
        _season_or_refuse(game.get("season"), where=f"games[{idx}]")
    for idx, quote in enumerate(quotes):
        if not isinstance(quote, Mapping):
            raise HarnessRefusal(INVALID_SCHEMA, f"quotes[{idx}] is not an object")
        season = quote.get("season")
        if season not in (None, ""):
            _season_or_refuse(season, where=f"quotes[{idx}]")
        source = str(quote.get("source") or "")
        provenance = str(quote.get("provenance") or "")
        if "synthetic" not in f"{source} {provenance}".casefold():
            raise HarnessRefusal(
                NOT_SYNTHETIC,
                f"quotes[{idx}] must carry synthetic source/provenance",
            )
    return payload


def _copy_games_with_cutoffs(
    games: Sequence[Mapping[str, Any]],
    forecasts: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    by_id = {str(row.get("game_id") or ""): row for row in forecasts}
    out: List[Dict[str, Any]] = []
    for game in games:
        row = dict(game)
        if row.get("forecast_cutoff") in (None, ""):
            forecast = by_id.get(str(row.get("game_id") or ""), {})
            if forecast.get("forecast_cutoff"):
                row["forecast_cutoff"] = forecast["forecast_cutoff"]
        out.append(row)
    return out


def _duplicate_forecast_ids(forecasts: Sequence[Mapping[str, Any]]) -> set[str]:
    by_id: Dict[str, int] = Counter(str(row.get("game_id") or "") for row in forecasts)
    by_key: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    for row in forecasts:
        key = _identity_key(row)
        by_key[key].append(str(row.get("game_id") or ""))
    dupes = {gid for gid, n in by_id.items() if gid and n > 1}
    for key, ids in by_key.items():
        if key[0] and len(set(ids)) > 1:
            dupes.update(ids)
        if key[0] and len(ids) > 1:
            dupes.update(ids)
    return dupes


def _quote_price(quote: EligibleQuote) -> Optional[float]:
    code = quote.market
    if code == "spread":
        return quote.price_home if quote.price_home is not None else quote.price
    if code == "total":
        return quote.over_price if quote.over_price is not None else quote.price
    if code == "moneyline":
        return quote.price_home if quote.price_home is not None else quote.price
    return quote.price


def _lines_compatible(market: str, forecast_line: Optional[float], quote: EligibleQuote) -> bool:
    code = canonical_market(market)
    if code != quote.market:
        return False
    if code in {"spread", "total"}:
        return forecast_line is not None and quote.line is not None
    if code == "moneyline":
        return quote.line is None
    return False


def _outcome_map(outcomes: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in outcomes:
        gid = str(row.get("game_id") or "")
        if gid:
            out[gid] = dict(row)
    return out


def compare_forecasts_to_manifest(
    forecast_payload: Mapping[str, Any],
    manifest_payload: Mapping[str, Any],
    *,
    forecast_path: Optional[str] = None,
    manifest_path: Optional[str] = None,
) -> ComparisonReport:
    """Join owned odds at cutoff, then compare synthetic forecasts. Never fabricates."""
    _require_synthetic_header(forecast_payload, schema=FORECAST_SCHEMA, where="forecast payload")
    _require_synthetic_header(manifest_payload, schema=MANIFEST_SCHEMA, where="odds manifest")

    forecasts = [dict(row) for row in forecast_payload["forecasts"]]
    outcomes = list(forecast_payload.get("synthetic_outcomes") or [])
    games = _copy_games_with_cutoffs(manifest_payload["games"], forecasts)
    quotes = [dict(row) for row in manifest_payload["quotes"]]

    global_cutoff = forecast_payload.get("forecast_cutoff") or manifest_payload.get("forecast_cutoff")
    if global_cutoff in (None, "") and forecasts:
        global_cutoff = forecasts[0].get("forecast_cutoff")

    join = join_quotes_at_cutoff(quotes, games, global_cutoff)
    excluded: List[ExcludedRow] = list(join.excluded)
    comparisons: List[ComparisonRow] = []

    latest_by_game_market: Dict[Tuple[str, str], List[EligibleQuote]] = defaultdict(list)
    latest_by_game: Dict[str, List[EligibleQuote]] = defaultdict(list)
    for quote in join.latest_per_book_market:
        latest_by_game_market[(quote.game_id, quote.market)].append(quote)
        latest_by_game[quote.game_id].append(quote)

    dupes = _duplicate_forecast_ids(forecasts)
    outcome_by_game = _outcome_map(outcomes)

    for forecast in forecasts:
        game_id = str(forecast.get("game_id") or "")
        if game_id in dupes:
            excluded.append(
                ExcludedRow(
                    DUPLICATE_GAME,
                    f"duplicate forecast identity game_id={game_id!r}",
                    {"game_id": game_id},
                )
            )
            continue
        home = resolve_team_identity(str(forecast.get("home_team") or forecast.get("home") or ""))
        away = resolve_team_identity(str(forecast.get("away_team") or forecast.get("away") or ""))
        if home.status == "ambiguous" or away.status == "ambiguous":
            excluded.append(
                ExcludedRow(
                    AMBIGUOUS_IDENTITY,
                    f"forecast home={home.raw!r} away={away.raw!r}",
                    {"game_id": game_id},
                )
            )
            continue
        if home.status != "resolved" or away.status != "resolved":
            excluded.append(
                ExcludedRow(
                    AMBIGUOUS_IDENTITY if "ambiguous" in {home.status, away.status} else "unknown_team",
                    f"forecast home={home.raw!r} away={away.raw!r}",
                    {"game_id": game_id},
                )
            )
            continue

        markets = forecast.get("markets") or {}
        if not markets:
            excluded.append(ExcludedRow(MISSING_FORECAST, "no markets", {"game_id": game_id}))
            continue

        for raw_market, body in markets.items():
            code = canonical_market(raw_market)
            if not isinstance(body, Mapping):
                excluded.append(
                    ExcludedRow(MISSING_FORECAST, f"market={raw_market!r} body invalid", {"game_id": game_id})
                )
                continue
            p_value = _forecast_p(code, body)
            forecast_line = _forecast_line(code, body)
            quotes_for = list(latest_by_game_market.get((game_id, code), []))
            if not quotes_for:
                other = [quote.market for quote in latest_by_game.get(game_id, [])]
                if other:
                    excluded.append(
                        ExcludedRow(
                            INCOMPATIBLE_LINE,
                            f"{game_id} {code} has no matching line; owned quotes are {other}",
                            {"game_id": game_id, "market": code, "owned_markets": other},
                        )
                    )
                else:
                    excluded.append(
                        ExcludedRow(
                            NO_ELIGIBLE_QUOTE,
                            f"no cutoff-eligible {code} quote for {game_id}",
                            {"game_id": game_id, "market": code},
                        )
                    )
                continue
            if p_value is None:
                excluded.append(
                    ExcludedRow(
                        MISSING_PROBABILITY,
                        f"{game_id} {code} missing probability",
                        {"game_id": game_id, "market": code},
                    )
                )
                continue

            compatible = [quote for quote in quotes_for if _lines_compatible(code, forecast_line, quote)]
            if not compatible:
                excluded.append(
                    ExcludedRow(
                        INCOMPATIBLE_LINE,
                        f"{game_id} {code} forecast_line={forecast_line!r} vs quotes {[q.market for q in quotes_for]}",
                        {"game_id": game_id, "market": code, "forecast_line": forecast_line},
                    )
                )
                continue

            outcome = outcome_by_game.get(game_id)
            for quote in compatible:
                implied = american_implied_prob(_quote_price(quote))
                home_line = quote.spread_home if code == "spread" else quote.line
                away_line = None
                if code == "spread" and home_line is not None:
                    away_line = line_for_side(home_line, "away")
                synthetic = None
                if outcome is not None:
                    result = grade_synthetic_outcome(
                        code,
                        quote.line if code != "moneyline" else None,
                        outcome.get("home_score"),
                        outcome.get("away_score"),
                    )
                    if result is not None:
                        synthetic = {
                            "home_score": outcome.get("home_score"),
                            "away_score": outcome.get("away_score"),
                            "result": result,
                            "source": "synthetic",
                        }
                comparisons.append(
                    ComparisonRow(
                        game_id=quote.game_id,
                        event_id=quote.event_id,
                        season=quote.season,
                        game_date=quote.game_date,
                        home_abbr=quote.home_abbr,
                        away_abbr=quote.away_abbr,
                        book=quote.book,
                        market=quote.market,
                        forecast_line=forecast_line,
                        market_line=quote.line,
                        line_delta=(
                            None
                            if forecast_line is None or quote.line is None
                            else forecast_line - quote.line
                        ),
                        forecast_p=p_value,
                        implied_p=implied,
                        p_delta=None if implied is None else p_value - implied,
                        home_line=home_line,
                        away_line=away_line,
                        price=_quote_price(quote),
                        captured_at=quote.captured_at,
                        forecast_cutoff=str(
                            forecast.get("forecast_cutoff")
                            or global_cutoff
                            or ""
                        ),
                        quote_provenance=quote.provenance,
                        forecast_provenance=str(
                            forecast.get("provenance")
                            or forecast_payload.get("provenance")
                            or "synthetic_forecast"
                        ),
                        synthetic_outcome=synthetic,
                    )
                )

    tallies = Counter(item.reason for item in excluded)
    notes = [
        "CERT=0. DRAFT≠merge.",
        "Synthetic forecasts and synthetic outcomes only.",
        "No fitting, scoring, retuning, or real-outcome EVAL.",
        "Package A reader reused; later/closing quotes are never substituted.",
        f"CLEAR {CLEAR_TIP}; Alex PASS_RO {ALEX_PASS_RO}; CoS ACCEPT {COS_ACCEPT}.",
    ]
    return ComparisonReport(
        generated_at_utc=_now_utc(),
        code_pin={
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": _git("rev-parse", "HEAD"),
            "package_a_head": PACKAGE_A_HEAD,
            "reader": READER_PATH,
            "harness": HARNESS_PATH,
            "clear_tip": CLEAR_TIP,
            "alex_pass_ro": ALEX_PASS_RO,
            "cos_accept": COS_ACCEPT,
        },
        inputs={
            "forecast_path": forecast_path,
            "manifest_path": manifest_path,
            "forecast_n": len(forecasts),
            "game_n": len(games),
            "quote_n": len(quotes),
            "synthetic_outcome_n": len(outcomes),
        },
        join={
            "eligible_n": len(join.eligible),
            "excluded_n": len(join.excluded),
            "identical_duplicate_n": join.identical_duplicate_n,
            "reason_tallies": dict(join.reason_tallies),
            "latest_per_book_market_n": len(join.latest_per_book_market),
            "cutoff_rule": "source timestamp <= explicit forecast_cutoff; never substitute a later/closing quote",
            "sign_convention": SIGN_CONVENTION,
        },
        comparisons=comparisons,
        excluded=excluded,
        reason_tallies=dict(tallies),
        identical_duplicate_n=join.identical_duplicate_n,
        notes=notes,
    )


def run_comparison_files(forecast_path: Path, manifest_path: Path) -> ComparisonReport:
    forecast_payload = load_forecast_file(forecast_path)
    manifest_payload = load_odds_manifest(manifest_path)
    return compare_forecasts_to_manifest(
        forecast_payload,
        manifest_payload,
        forecast_path=str(forecast_path),
        manifest_path=str(manifest_path),
    )


def write_report(report: ComparisonReport, output_path: Path) -> Path:
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8")
    return dest
