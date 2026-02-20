#!/usr/bin/env python3
"""
Single entrypoint for the NCAAB data pipeline. Runs steps in order with env check.

Usage (from apps/web):
  python run_pipeline.py              # full pipeline (ratings → odds → join → merge)
  python run_pipeline.py --skip-odds  # skip process_odds (use existing parquet)
  python run_pipeline.py --check-env  # only print env status and exit

Requires: data/raw/ratings/ with KenPom (and optionally Torvik, Evan) CSVs.
For odds: run scripts/fetch_historical_ncaab_odds.py first, or use --skip-odds if parquet exists.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent
SRC = WEB_ROOT / "src"
SCRIPT = WEB_ROOT / "scripts"


def _load_dotenv() -> None:
    """Load .env.local / .env so check_env reflects keys set there."""
    for name in (".env.local", ".env"):
        path = WEB_ROOT / name
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        break


def check_env() -> dict[str, bool]:
    """Report which env vars are set (for API keys)."""
    return {
        "ODDS_API_KEY": bool(os.environ.get("ODDS_API_KEY", "").strip()),
        "KENPOM_API_KEY": bool(os.environ.get("KENPOM_API_KEY", "").strip()),
    }


def print_env_status() -> None:
    status = check_env()
    print("Environment:")
    for key, ok in status.items():
        print(f"  {key}: {'set' if ok else 'not set'}")
    if not status["ODDS_API_KEY"]:
        print("  -> Set ODDS_API_KEY (e.g. in .env.local) to fetch historical odds.")
    if not status["KENPOM_API_KEY"]:
        print("  -> Set KENPOM_API_KEY to use ingest_kenpom.py.")


def run(cmd: list[str], cwd: Path) -> bool:
    """Run a command; return True on success."""
    print(f"\n>>> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        print(f"Failed with exit code {r.returncode}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Run NCAAB pipeline (ratings → odds → join → merge)")
    ap.add_argument("--skip-odds", action="store_true", help="Skip process_odds (use existing odds parquet)")
    ap.add_argument("--check-env", action="store_true", help="Only print env status and exit")
    args = ap.parse_args()

    _load_dotenv()
    print_env_status()
    if args.check_env:
        return 0

    steps = [
        [sys.executable, str(SRC / "build_ratings.py")],
        [sys.executable, str(SRC / "build_ensemble_ratings.py")],
    ]
    if not args.skip_odds:
        steps.append([sys.executable, str(SRC / "process_odds.py")])
    steps.extend([
        [sys.executable, str(SRC / "join_and_backtest.py")],
        [sys.executable, str(SRC / "merge_games_ensemble.py")],
    ])

    for step in steps:
        if not run(step, WEB_ROOT):
            return 1
    print("\nPipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
