#!/usr/bin/env python3
"""CI gate: HISTORY_AUDIT_PR_B must match final B stack (Phase 2.6F CR5-3).

Ryan LOCKED comparison (against the PR head tip, NOT the merge commit):
  recorded audited_parent_tip == git rev-parse <pr-head>^
  recorded audited_commits    == git rev-list --reverse A..<pr-head>^

On pull_request workflows, actions/checkout yields a merge commit where HEAD^
is the base branch — callers MUST pass --head-ref $PR_HEAD_SHA.

Fails closed on drift. Does not invent coverage.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List

REPO = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT = (
    REPO
    / "data"
    / "ops"
    / "lab"
    / "ncaam"
    / "holdout_2024_25"
    / "r2_object_refs"
    / "HISTORY_AUDIT_PR_B.json"
)
DEFAULT_A_BRANCH = "cursor/ncaam-26f-foundation-fix-8a49"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def expected_from_git(*, a_ref: str, head_ref: str = "HEAD") -> dict:
    parent = _git("rev-parse", f"{head_ref}^")
    # Oldest-first exclusive of the audit tip (HEAD).
    commits = (
        _git("rev-list", "--reverse", f"{a_ref}..{head_ref}^").splitlines()
        if _git("rev-list", "--count", f"{a_ref}..{head_ref}^") != "0"
        else []
    )
    a_tip = _git("rev-parse", a_ref)
    return {
        "audited_parent_tip": parent,
        "audited_commits": commits,
        "expected_n_audited_commits": len(commits),
        "stacked_on_a_head": a_tip,
    }


def check_audit(audit_path: Path, *, a_ref: str, head_ref: str = "HEAD") -> int:
    if not audit_path.exists():
        print(f"MISSING audit file: {audit_path}", file=sys.stderr)
        return 2
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected = expected_from_git(a_ref=a_ref, head_ref=head_ref)

    errors: List[str] = []
    if audit.get("audited_parent_tip") != expected["audited_parent_tip"]:
        errors.append(
            "audited_parent_tip drift: "
            f"recorded={audit.get('audited_parent_tip')} "
            f"expected_HEAD^={expected['audited_parent_tip']}"
        )
    recorded = list(audit.get("audited_commits") or [])
    if recorded != expected["audited_commits"]:
        errors.append(
            "audited_commits drift vs git rev-list --reverse A..HEAD^: "
            f"recorded_n={len(recorded)} expected_n={len(expected['audited_commits'])}"
        )
        # Show first mismatch for CI logs.
        for i, (a, b) in enumerate(zip(recorded, expected["audited_commits"])):
            if a != b:
                errors.append(f"  first_sha_mismatch index={i} recorded={a} expected={b}")
                break
        if len(recorded) != len(expected["audited_commits"]):
            errors.append(
                f"  recorded={recorded[:3]}... expected={expected['audited_commits'][:3]}..."
            )
    if int(audit.get("expected_n_audited_commits") or -1) != expected[
        "expected_n_audited_commits"
    ]:
        errors.append(
            "expected_n_audited_commits drift: "
            f"recorded={audit.get('expected_n_audited_commits')} "
            f"expected={expected['expected_n_audited_commits']}"
        )
    if audit.get("stacked_on_a_head") != expected["stacked_on_a_head"]:
        errors.append(
            "stacked_on_a_head drift: "
            f"recorded={audit.get('stacked_on_a_head')} "
            f"expected={expected['stacked_on_a_head']}"
        )

    # Parent must be an ancestor of HEAD.
    try:
        _git("merge-base", "--is-ancestor", expected["audited_parent_tip"], head_ref)
    except subprocess.CalledProcessError:
        errors.append(
            f"audited_parent_tip {expected['audited_parent_tip']} is not an ancestor of {head_ref}"
        )

    if errors:
        print("HISTORY_AUDIT_PR_B CI GATE FAILED", file=sys.stderr)
        for e in errors:
            print(f" - {e}", file=sys.stderr)
        print(
            json.dumps({"status": "FAIL", "expected": expected}, indent=2, sort_keys=True)
        )
        return 1

    print(
        json.dumps(
            {
                "status": "PASS",
                "audited_parent_tip": expected["audited_parent_tip"],
                "expected_n_audited_commits": expected["expected_n_audited_commits"],
                "stacked_on_a_head": expected["stacked_on_a_head"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument(
        "--a-ref",
        default=DEFAULT_A_BRANCH,
        help="Foundation A ref (branch or SHA) for A..HEAD^ range",
    )
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument(
        "--print-expected",
        action="store_true",
        help="Print expected audit fields from git and exit 0",
    )
    args = parser.parse_args(argv)
    if args.print_expected:
        print(json.dumps(expected_from_git(a_ref=args.a_ref, head_ref=args.head_ref), indent=2))
        return 0
    return check_audit(args.audit, a_ref=args.a_ref, head_ref=args.head_ref)


if __name__ == "__main__":
    raise SystemExit(main())
