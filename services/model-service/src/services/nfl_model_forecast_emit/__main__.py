"""CLI: emit | audit | slate. No Odds. No seal dests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.services.nfl_model_forecast_emit.completeness import audit_week_inputs
from src.services.nfl_model_forecast_emit.emit import (
    ForecastIncompleteError,
    canonicalize,
    emit_model_forecast,
)
from src.services.nfl_model_forecast_emit.slate import run_week_slate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nfl_model_forecast_emit")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_emit = sub.add_parser("emit", help="emit one forecast from a JSON inputs file")
    p_emit.add_argument("--inputs", required=True)
    p_emit.add_argument("--dest")

    p_audit = sub.add_parser("audit", help="audit current inputs for a week slate")
    p_audit.add_argument("--season", type=int, default=2026)
    p_audit.add_argument("--week", type=int, default=8)
    p_audit.add_argument("--out")

    p_slate = sub.add_parser("slate", help="full-slate emit; fails if inputs incomplete")
    p_slate.add_argument("--season", type=int, default=2026)
    p_slate.add_argument("--week", type=int, default=8)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "emit":
            payload = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
            art = emit_model_forecast(payload, dest_path=args.dest)
            sys.stdout.write(canonicalize(art) + "\n")
            return 0
        if args.cmd == "audit":
            report = audit_week_inputs(season=args.season, week=args.week)
            text = canonicalize(report) + "\n"
            if args.out:
                Path(args.out).write_text(text, encoding="utf-8")
            sys.stdout.write(text)
            return 0 if report["ok"] else 2
        if args.cmd == "slate":
            run_week_slate(season=args.season, week=args.week)
            return 0
    except ForecastIncompleteError as exc:
        sys.stderr.write(f"FAIL_CLOSED gap={exc.gap} reason={exc.reason}: {exc}\n")
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
