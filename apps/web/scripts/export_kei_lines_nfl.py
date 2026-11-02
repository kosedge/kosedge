"""
Export KEINFL lines (projected spread + O/U) for the shared edge board.
Reads Kosedge fair-lines from the model-service and writes
data/processed/kei_lines_nfl.json with Odds-API team names.

Usage (from repo root or apps/web):
  MODEL_SERVICE_URL=http://127.0.0.1:8000 python apps/web/scripts/export_kei_lines_nfl.py

t5178u export policy (DECIDED; no M0 types):
  Upstream/503, unexpected empty, blank identity, malformed/nonfinite numeric,
  inconsistent counts, or partial-row drop → non-actionable refusal / exit 1.
  Prior valid OUT is left untouched. Fully valid output replaces atomically.
  NFL is excluded from the common-sports honesty sport set — do not treat
  those honest-empty statuses as exit-0 success. 503 with empty reasons is unavailable.
"""
from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
OUT = WEB / "data" / "processed" / "kei_lines_nfl.json"

# Versioned NFL-only status contract. Do not import or honor the
# common-sports honesty sport / honest-empty enums (those exclude NFL).
NFL_EXPORT_STATUS_CONTRACT = "nfl-export-status-v1"

# Same ONE contract as services/model-service/.../nfl_fixture_assembly/contract.py
FIXTURE_CONTRACT_ID = "t5178u-nfl-fixture-assembly-v0"
FIXTURE_CONTRACT_SCHEMA_VERSION = "nfl-fixture-assembly-v0"
CHAIN_CONTRACT_ID = "t5194u-nfl-fixture-chain-v1"
CHAIN_SCHEMA_VERSION = "nfl-fixture-chain-v1"
FIXTURE_CHANNEL = "FIXTURE"
ELIGIBILITY_REQUIRED_KEYS = (
    "result",
    "reason",
    "contract_id",
    "schema_version",
    "channel",
    "fixture",
    "subscriber_consumable",
    "betting_consumable",
    "production_consumable",
    "env_bypass_honored",
    "cacheable",
)
ELIGIBILITY_REQUIRED_FALSE_BOOLS = (
    "subscriber_consumable",
    "betting_consumable",
    "production_consumable",
    "env_bypass_honored",
    "cacheable",
)
NON_FIXTURE_CONSUMERS = frozenset(
    {
        "subscriber",
        "betting",
        "production",
        "fair_lines_api",
        "honesty_board",
        "props_eligibility",
    }
)
OUTPUT_REFUSE = {
    "TOTAL": "REFUSE_TOTALS",
    "MONEYLINE": "REFUSE_MONEYLINE",
    "COVER_PROBABILITY": "REFUSE_COVER_PROBABILITY",
    "ECONOMIC_ELIGIBILITY": "REFUSE_ECONOMIC_ELIGIBILITY",
}


class NflExportRefuse(Exception):
    """Non-actionable export refusal. Never an exit-0 success."""

    def __init__(self, reason: str):
        self.reason = reason
        self.actionable = False
        super().__init__(reason)


def emit_non_actionable(reason: str) -> None:
    print(
        json.dumps(
            {
                "ok": False,
                "actionable": False,
                "sport": "nfl",
                "statusContract": NFL_EXPORT_STATUS_CONTRACT,
                "reason": reason,
            },
            separators=(",", ":"),
        ),
        file=sys.stderr,
    )


def _finite_or_none(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise NflExportRefuse("malformed_numeric") from None
    if not math.isfinite(number):
        raise NflExportRefuse("malformed_numeric")
    return number


def _required_identity(row: object) -> tuple[str, str, str]:
    if not isinstance(row, dict):
        raise NflExportRefuse("blank_required_identity")
    game_id = str(row.get("game_id") or "").strip()
    home = str(row.get("home_team") or "").strip()
    away = str(row.get("away_team") or "").strip()
    if not game_id or not home or not away:
        raise NflExportRefuse("blank_required_identity")
    return game_id, home, away


def assemble_games(payload: object) -> list[dict[str, object]]:
    """Build export games or raise NflExportRefuse. No silent skip / partial drop."""
    if not isinstance(payload, dict):
        raise NflExportRefuse("unexpected_empty_payload")
    eligibility = payload.get("eligibility")
    if payload.get("fixture") is True or (
        isinstance(eligibility, dict) and eligibility.get("result") == "ALLOW_FIXTURE"
    ):
        # Customer export is fair_lines_api / production — cannot consume ALLOW_FIXTURE.
        raise NflExportRefuse("REFUSE_PRODUCTION_CHANNEL")
    error = payload.get("error")
    if isinstance(error, str) and error.strip():
        # 503-shaped / error-bearing body is unavailable, not empty-success.
        raise NflExportRefuse("upstream_unavailable")
    if "lines" not in payload:
        raise NflExportRefuse("unexpected_empty_payload")
    lines = payload.get("lines")
    if not isinstance(lines, list):
        raise NflExportRefuse("unexpected_empty_payload")
    declared = payload.get("count")
    if declared is not None:
        try:
            declared_n = int(declared)
        except (TypeError, ValueError):
            raise NflExportRefuse("inconsistent_counts") from None
        if declared_n != len(lines):
            raise NflExportRefuse("inconsistent_counts")
    if len(lines) == 0:
        # Honest empty requires a future M0 NFL status contract.
        # Common-sports honest-empty statuses are not imported and not honored.
        raise NflExportRefuse("unexpected_empty_payload")

    games: list[dict[str, object]] = []
    for row in lines:
        game_id, home, away = _required_identity(row)
        spread = _finite_or_none(row.get("spread_home"))
        total = _finite_or_none(row.get("total_mean"))
        commence = row.get("start_time") or row.get("game_date")
        games.append(
            {
                "id": game_id,
                "homeTeam": home,
                "awayTeam": away,
                "homeAbbr": row.get("home_abbr"),
                "awayAbbr": row.get("away_abbr"),
                "commenceTime": commence,
                "projSpreadHome": round(spread, 2) if spread is not None else None,
                "projTotal": round(total, 2) if total is not None else None,
            }
        )
    if len(games) != len(lines):
        raise NflExportRefuse("partial_row_drop")
    return games


def consume_fixture_eligibility(decision: object, consumer: str) -> dict[str, object]:
    """Same exact-field gate as assemble.consume_fixture_eligibility (A tip)."""
    if not isinstance(decision, dict):
        raise NflExportRefuse("REFUSE_PARTIAL")
    missing = [key for key in ELIGIBILITY_REQUIRED_KEYS if key not in decision]
    if missing:
        raise NflExportRefuse("REFUSE_MISSING")
    if decision["contract_id"] != FIXTURE_CONTRACT_ID:
        raise NflExportRefuse("REFUSE_VERSION")
    if decision["schema_version"] != FIXTURE_CONTRACT_SCHEMA_VERSION:
        raise NflExportRefuse("REFUSE_VERSION")
    if decision["channel"] != FIXTURE_CHANNEL:
        raise NflExportRefuse("REFUSE_PRODUCTION_CHANNEL")
    if decision["fixture"] is not True:
        if decision["fixture"] is False:
            raise NflExportRefuse("REFUSE_QUALIFICATION")
        raise NflExportRefuse("REFUSE_PARTIAL")
    for key in ELIGIBILITY_REQUIRED_FALSE_BOOLS:
        value = decision[key]
        if value is not False:
            if not isinstance(value, bool):
                raise NflExportRefuse("REFUSE_PARTIAL")
            raise NflExportRefuse("REFUSE_PRODUCTION_CHANNEL")
    result = decision["result"]
    if result != "ALLOW_FIXTURE":
        raise NflExportRefuse(str(result) if result else "REFUSE_QUALIFICATION")
    if not isinstance(decision["reason"], str) or not decision["reason"]:
        raise NflExportRefuse("REFUSE_PARTIAL")
    token = consumer if isinstance(consumer, str) else ""
    token = token.strip().lower()
    if token in NON_FIXTURE_CONSUMERS:
        raise NflExportRefuse("REFUSE_PRODUCTION_CHANNEL")
    if token != "fixture":
        raise NflExportRefuse("REFUSE_QUALIFICATION")
    return {
        "result": "ALLOW_FIXTURE",
        "reason": decision["reason"],
        "fixture": True,
        "channel": FIXTURE_CHANNEL,
        "subscriber_consumable": False,
        "betting_consumable": False,
        "production_consumable": False,
        "env_bypass_honored": False,
        "cacheable": False,
        "contract_id": FIXTURE_CONTRACT_ID,
        "schema_version": FIXTURE_CONTRACT_SCHEMA_VERSION,
        "actionable": False,
    }


def _load_consume_chain():
    """A's consume_chain SoT. Lazy so production KEI export stays isolated."""
    ms = Path(__file__).resolve().parents[3] / "services" / "model-service"
    if str(ms) not in sys.path:
        sys.path.insert(0, str(ms))
    from src.services.nfl_fixture_assembly.consume_chain import (  # type: ignore[import-not-found]
        consume_fixture_chain,
    )
    from src.services.nfl_fixture_assembly.contract import (  # type: ignore[import-not-found]
        FixtureHardRefuse,
    )

    return consume_fixture_chain, FixtureHardRefuse


def assert_fixture_chain_record(payload: object) -> dict[str, object]:
    """Refuse mutated/missing A→B handoff via A's consume_chain (not shape-only)."""
    consume_fixture_chain, fixture_hard_refuse = _load_consume_chain()
    try:
        return consume_fixture_chain(payload, consumer="fixture")
    except fixture_hard_refuse as exc:
        raise NflExportRefuse(exc.result.value) from exc


def project_fixture_assembly_to_export(
    assembly: object,
    *,
    consumer: str,
    home_team: str,
    away_team: str,
    home_abbr: str = "HOM",
    away_abbr: str = "AWY",
    requested_output: str = "POINT_MARGIN_SPREAD",
) -> dict[str, object]:
    """Project the SAME t5178u contract into the export game shape. Spread only."""
    if not isinstance(assembly, dict):
        raise NflExportRefuse("unexpected_empty_payload")
    if assembly.get("chain_contract_id") is not None:
        assert_fixture_chain_record(assembly)
        if assembly.get("requested_output") not in (None, "POINT_MARGIN_SPREAD"):
            requested_output = str(assembly["requested_output"])
    if requested_output != "POINT_MARGIN_SPREAD":
        raise NflExportRefuse(
            OUTPUT_REFUSE.get(requested_output, "REFUSE_CAPABILITY")
        )
    eligibility = consume_fixture_eligibility(assembly.get("eligibility"), consumer)
    quote = assembly.get("quote")
    if not isinstance(quote, dict):
        raise NflExportRefuse("REFUSE_MISSING")
    event_id = str(quote.get("event_id") or "").strip()
    home = home_team.strip()
    away = away_team.strip()
    if not event_id or not home or not away:
        raise NflExportRefuse("blank_required_identity")
    if str(quote.get("period") or "") != "full_game":
        raise NflExportRefuse("REFUSE_PERIOD")
    side = str(quote.get("side") or "")
    if side not in {"HOME", "AWAY"}:
        raise NflExportRefuse("REFUSE_SIGN")
    spread = _finite_or_none(quote.get("line"))
    if spread is None:
        raise NflExportRefuse("malformed_numeric")
    if side == "AWAY":
        spread = -spread
    game = {
        "id": event_id,
        "homeTeam": home,
        "awayTeam": away,
        "homeAbbr": home_abbr,
        "awayAbbr": away_abbr,
        "commenceTime": quote.get("time"),
        "projSpreadHome": round(spread, 2),
        "projTotal": None,
        "fixture": True,
    }
    return {
        "sport": "nfl",
        "keiCode": "KEINFL",
        "fixture": True,
        "eligibility": eligibility,
        "games": [game],
        "contract_id": FIXTURE_CONTRACT_ID,
    }


def write_atomic(path: Path, doc: object) -> None:
    """Fully valid output replaces OUT atomically. Failures leave prior bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(doc, handle, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def main() -> int:
    base = (os.environ.get("MODEL_SERVICE_URL") or "http://127.0.0.1:8000").rstrip("/")
    season = int(os.environ.get("NFL_KEI_SEASON") or "2026")
    days_ahead = int(os.environ.get("NFL_KEI_DAYS_AHEAD") or "200")
    include_past = int(os.environ.get("NFL_KEI_INCLUDE_PAST_DAYS") or "14")
    url = (
        f"{base}/nfl/fair-lines"
        f"?season={season}&days_ahead={days_ahead}&include_past_days={include_past}"
    )

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        # #697 tip 0aad8d75 transport refusals RETAIN — exit 1 before OUT write.
        print(f"Failed to fetch fair-lines from {url}: {exc}", file=sys.stderr)
        emit_non_actionable("upstream_unavailable")
        return 1

    try:
        games = assemble_games(payload)
        write_atomic(OUT, {"sport": "nfl", "keiCode": "KEINFL", "games": games})
    except NflExportRefuse as exc:
        emit_non_actionable(exc.reason)
        return 1
    except OSError:
        emit_non_actionable("write_failed")
        return 1

    print(f"Wrote {OUT} with {len(games)} games (KEINFL).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
