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
