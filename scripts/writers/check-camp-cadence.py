#!/usr/bin/env python3
"""Camp Desk + Monday preview cadence gate.

Fails when:
  - Camp window is active (ET date < 2026-09-09) AND newest
    content/writers/camp-desk-2026/YYYY-MM-DD.json desk_date is not today ET
  - Today is Monday ET AND any season-previews-2026/*.md **Date:** is before
    this Monday

Usage:
  python scripts/writers/check-camp-cadence.py
  python scripts/writers/check-camp-cadence.py --self-test
  python scripts/writers/check-camp-cadence.py --as-of 2026-08-30
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
DESK_DIR = REPO / "content" / "writers" / "camp-desk-2026"
PREVIEWS_DIR = REPO / "content" / "writers" / "season-previews-2026"
ET = ZoneInfo("America/New_York")
CAMP_END = date(2026, 9, 9)
DATE_LINE_RE = re.compile(
    r"^\*\*Date:\*\*\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})",
    re.MULTILINE,
)
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def et_today(as_of: str | None = None) -> date:
    if as_of:
        return date.fromisoformat(as_of)
    return datetime.now(ET).date()


def camp_window_active(today: date) -> bool:
    return today < CAMP_END


def newest_desk_date(desk_dir: Path) -> date | None:
    best: date | None = None
    for path in desk_dir.glob("????-??-??.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw = payload.get("desk_date") or path.stem
        try:
            d = date.fromisoformat(str(raw))
        except ValueError:
            continue
        if best is None or d > best:
            best = d
    return best


def parse_preview_date(text: str) -> date | None:
    m = DATE_LINE_RE.search(text)
    if not m:
        return None
    month = MONTHS.get(m.group(1).lower())
    if not month:
        return None
    return date(int(m.group(3)), month, int(m.group(2)))


def this_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


def check_desk(desk_dir: Path, today: date) -> list[str]:
    errors: list[str] = []
    if not camp_window_active(today):
        return errors
    newest = newest_desk_date(desk_dir)
    if newest is None:
        errors.append(
            f"Camp window open ({today.isoformat()} ET < {CAMP_END.isoformat()}): "
            "no camp-desk YYYY-MM-DD.json found."
        )
        return errors
    if newest != today:
        errors.append(
            f"Camp window open: newest desk_date is {newest.isoformat()}, "
            f"expected today ET {today.isoformat()}. "
            f"Add content/writers/camp-desk-2026/{today.isoformat()}.json."
        )
    return errors


def check_monday_previews(previews_dir: Path, today: date) -> list[str]:
    errors: list[str] = []
    if today.weekday() != 0:  # Monday
        return errors
    if not camp_window_active(today) and today >= CAMP_END:
        # Still enforce Monday refresh through Week 1 kickoff week; after camp end, skip.
        return errors
    monday = this_monday(today)
    if not previews_dir.is_dir():
        errors.append(f"Missing previews dir: {previews_dir}")
        return errors
    for path in sorted(previews_dir.glob("*.md")):
        # Team files are XXX.md (ARI…WAS). Skip index / readme helpers.
        if not re.fullmatch(r"[A-Z]{2,3}\.md", path.name):
            continue
        text = path.read_text(encoding="utf-8")
        parsed = parse_preview_date(text)
        if parsed is None:
            errors.append(f"{path.name}: missing **Date:** line")
            continue
        if parsed < monday:
            errors.append(
                f"{path.name}: **Date:** {parsed.isoformat()} is before "
                f"this Monday ({monday.isoformat()}). Refresh Date + Bottom line / "
                "What matters most."
            )
    return errors


def run_checks(
    *,
    desk_dir: Path = DESK_DIR,
    previews_dir: Path = PREVIEWS_DIR,
    today: date | None = None,
) -> list[str]:
    day = today or et_today()
    return check_desk(desk_dir, day) + check_monday_previews(previews_dir, day)


def self_test() -> None:
    failures = 0

    def expect(ok: bool, label: str) -> None:
        nonlocal failures
        if ok:
            print(f"  ok  {label}")
        else:
            print(f"FAIL {label}")
            failures += 1

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        desk = root / "desk"
        previews = root / "previews"
        desk.mkdir()
        previews.mkdir()

        # Missing today → fail
        (desk / "2026-08-26.json").write_text(
            json.dumps({"desk_date": "2026-08-26"}), encoding="utf-8"
        )
        errs = run_checks(
            desk_dir=desk, previews_dir=previews, today=date(2026, 8, 30)
        )
        expect(any("expected today" in e for e in errs), "missing today fails")

        # Today present → pass (Sunday — no Monday preview rule)
        (desk / "2026-08-30.json").write_text(
            json.dumps({"desk_date": "2026-08-30"}), encoding="utf-8"
        )
        errs = run_checks(
            desk_dir=desk, previews_dir=previews, today=date(2026, 8, 30)
        )
        expect(errs == [], f"today present passes ({errs})")

        # Monday with stale preview Date → fail
        (desk / "2026-08-31.json").write_text(
            json.dumps({"desk_date": "2026-08-31"}), encoding="utf-8"
        )
        (previews / "GB.md").write_text(
            "# Packers\n\n**Date:** August 26, 2026\n", encoding="utf-8"
        )
        errs = run_checks(
            desk_dir=desk, previews_dir=previews, today=date(2026, 8, 31)
        )
        expect(
            any("before this Monday" in e for e in errs),
            "Monday stale preview Date fails",
        )

        # Monday with current Date → pass
        (previews / "GB.md").write_text(
            "# Packers\n\n**Date:** August 31, 2026\n", encoding="utf-8"
        )
        errs = run_checks(
            desk_dir=desk, previews_dir=previews, today=date(2026, 8, 31)
        )
        expect(errs == [], f"Monday current Date passes ({errs})")

        # After camp end → desk rule off
        errs = run_checks(
            desk_dir=desk, previews_dir=previews, today=date(2026, 9, 10)
        )
        expect(errs == [], f"post-camp skips desk gate ({errs})")

    if failures:
        raise SystemExit(f"self-test failed: {failures}")
    print("self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        help="Override today ET as YYYY-MM-DD (for fixtures / local checks)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run unit checks against a temporary fake folder",
    )
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    today = et_today(args.as_of)
    errors = run_checks(today=today)
    if errors:
        print("Camp cadence check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    newest = newest_desk_date(DESK_DIR)
    print(
        f"Camp cadence ok — today ET {today.isoformat()}; "
        f"newest desk {newest.isoformat() if newest else 'none'}; "
        f"camp_active={camp_window_active(today)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
