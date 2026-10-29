#!/usr/bin/env python3
"""G4 / C10 isolation: model-service push must not auto railway-up api/worker/beat.

Stdlib-only static check of GitHub Actions YAML. Fails if any workflow can run
``railway up`` for api/worker/beat on a bare push to ``deploy-vercel``.

Live file: ``.github/workflows/deploy-railway.yml``
Fixtures below prove the pre-isolation (dangerous) trigger is rejected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/deploy-railway.yml"
WORKFLOWS_DIR = REPO / ".github" / "workflows"

# Historical hole: push of model-service (or this workflow) to deploy-vercel
# ran Deploy api / worker / beat unconditionally. Merge of #655 would hit it.
DANGEROUS_PUSH_AUTO_DEPLOY = """
name: Deploy Railway model-service
on:
  push:
    branches: [deploy-vercel]
    paths:
      - "services/model-service/**"
      - ".github/workflows/deploy-railway.yml"
  workflow_dispatch:
jobs:
  deploy:
    name: Railway up (api / worker / beat)
    runs-on: ubuntu-latest
    steps:
      - name: Deploy api
        run: railway up services/model-service --path-as-root --ci --service model-service
      - name: Deploy worker
        run: railway up services/model-service --path-as-root --ci --service model-service-worker
      - name: Deploy beat
        run: railway up services/model-service --path-as-root --ci --service model-service-beat
"""

DISPATCH_ONLY_SAFE = """
name: Deploy Railway model-service
on:
  workflow_dispatch:
    inputs:
      confirm_c10_clear:
        required: true
        type: string
      confirm_services:
        required: true
        type: string
jobs:
  deploy:
    name: Railway up (api / worker / beat)
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.confirm_c10_clear == 'CLEAR' && inputs.confirm_services == 'api,worker,beat' }}
    runs-on: ubuntu-latest
    steps:
      - name: Deploy api
        if: ${{ github.event_name == 'workflow_dispatch' && inputs.confirm_c10_clear == 'CLEAR' && inputs.confirm_services == 'api,worker,beat' }}
        run: railway up services/model-service --path-as-root --ci --service model-service
      - name: Deploy worker
        if: ${{ github.event_name == 'workflow_dispatch' && inputs.confirm_c10_clear == 'CLEAR' && inputs.confirm_services == 'api,worker,beat' }}
        run: railway up services/model-service --path-as-root --ci --service model-service-worker
      - name: Deploy beat
        if: ${{ github.event_name == 'workflow_dispatch' && inputs.confirm_c10_clear == 'CLEAR' && inputs.confirm_services == 'api,worker,beat' }}
        run: railway up services/model-service --path-as-root --ci --service model-service-beat
"""

# Push exists but railway-up is still gated — also acceptable.
PUSH_WITH_HARD_GATE = """
name: Deploy Railway model-service
on:
  push:
    branches: [deploy-vercel]
    paths:
      - "services/model-service/**"
  workflow_dispatch:
    inputs:
      confirm_c10_clear:
        required: true
        type: string
jobs:
  deploy:
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.confirm_c10_clear == 'CLEAR' }}
    steps:
      - name: Deploy api
        if: ${{ github.event_name == 'workflow_dispatch' && inputs.confirm_c10_clear == 'CLEAR' }}
        run: railway up services/model-service --ci
"""

RAILWAY_UP_RE = re.compile(r"\brailway\s+up\b", re.I)
DEPLOY_STEP_RE = re.compile(r"^Deploy (api|worker|beat)$")
DISPATCH_RE = re.compile(r"workflow_dispatch")
CLEAR_RE = re.compile(r"\bCLEAR\b")
PUSH_KEY_RE = re.compile(r"^push\s*:")
ON_KEY_RE = re.compile(r"^on\s*:")


def _strip_full_line_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _top_level_block(text: str, key: str) -> str:
    """Return the body of a top-level YAML mapping key (indent 0)."""
    lines = text.splitlines()
    start = None
    key_re = re.compile(rf"^{re.escape(key)}\s*:")
    for i, line in enumerate(lines):
        if key_re.match(line):
            start = i
            break
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            body.append(line)
            continue
        if _indent(line) == 0 and not line.startswith(" "):
            break
        body.append(line)
    return "\n".join(body)


def _on_trigger_keys(on_body: str) -> set[str]:
    """Keys directly under ``on:`` (push, pull_request, workflow_dispatch, ...)."""
    keys: set[str] = set()
    stripped = on_body.strip()
    if not stripped:
        return keys
    # Short form: on: [push] or on: push
    if stripped.startswith("["):
        inner = stripped.strip("[]")
        for part in inner.split(","):
            token = part.strip().strip("\"'")
            if token:
                keys.add(token)
        return keys
    if "\n" not in stripped and ":" not in stripped:
        keys.add(stripped)
        return keys
    for line in on_body.splitlines():
        if not line.strip():
            continue
        if _indent(line) == 2 and re.match(r"^[A-Za-z_][\w-]*\s*:", line.strip()):
            keys.add(line.strip().split(":", 1)[0])
    return keys


def _job_blocks(jobs_body: str) -> list[tuple[str, str]]:
    """Return (job_id, job_body) for each job under ``jobs:``."""
    jobs: list[tuple[str, str]] = []
    lines = jobs_body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() and _indent(line) == 2 and re.match(
            r"^[A-Za-z_][\w-]*\s*:", line.strip()
        ):
            job_id = line.strip().split(":", 1)[0]
            body: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and _indent(nxt) == 2 and re.match(
                    r"^[A-Za-z_][\w-]*\s*:", nxt.strip()
                ):
                    break
                body.append(nxt)
                i += 1
            jobs.append((job_id, "\n".join(body)))
            continue
        i += 1
    return jobs


def _job_if(job_body: str) -> str:
    for line in job_body.splitlines():
        if _indent(line) == 4 and line.strip().startswith("if:"):
            return line.strip().split(":", 1)[1].strip()
    return ""


def _step_blocks(job_body: str) -> list[str]:
    """Split the ``steps:`` sequence into individual step texts."""
    lines = job_body.splitlines()
    start = None
    for i, line in enumerate(lines):
        if _indent(line) == 4 and line.strip() == "steps:":
            start = i + 1
            break
    if start is None:
        return []
    steps: list[list[str]] = []
    current: list[str] = []
    for line in lines[start:]:
        if line.strip() and _indent(line) == 4 and not line.startswith(" " * 5):
            # next job-level key
            break
        if line.strip().startswith("- ") and _indent(line) == 6:
            if current:
                steps.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        steps.append(current)
    return ["\n".join(s) for s in steps]


def _step_name(step: str) -> str:
    for line in step.splitlines():
        m = re.search(r"\bname:\s*(.+)$", line)
        if m:
            return m.group(1).strip().strip("\"'")
    return ""


def _step_if(step: str) -> str:
    for line in step.splitlines():
        if re.match(r"^\s+if:\s*", line):
            return line.split(":", 1)[1].strip()
    return ""


def _step_run(step: str) -> str:
    return step


def _if_is_dispatch_clear_gate(expr: str) -> bool:
    if not expr:
        return False
    return bool(DISPATCH_RE.search(expr) and CLEAR_RE.search(expr))


def _push_targets_deploy_vercel(on_body: str) -> bool:
    """True when ``on.push`` exists and is not clearly limited away from deploy-vercel."""
    keys = _on_trigger_keys(on_body)
    if "push" not in keys:
        return False
    # Extract the push: subtree at indent 2.
    lines = on_body.splitlines()
    body: list[str] = []
    in_push = False
    for line in lines:
        if _indent(line) == 2 and PUSH_KEY_RE.match(line.strip()):
            in_push = True
            body.append(line)
            continue
        if in_push:
            if line.strip() and _indent(line) == 2:
                break
            body.append(line)
    push_text = "\n".join(body)
    if re.search(r"branches:\s*\[", push_text) or re.search(
        r"^\s+-\s+deploy-vercel\s*$", push_text, re.M
    ):
        return "deploy-vercel" in push_text
    # No branch filter = all branches, including deploy-vercel.
    if "branches:" not in push_text:
        return True
    return "deploy-vercel" in push_text or "'**'" in push_text or '"**"' in push_text


def analyze_workflow_text(text: str, *, source: str) -> list[str]:
    """Return human-readable violations. Empty list = isolated."""
    raw = _strip_full_line_comments(text)
    errors: list[str] = []
    on_body = _top_level_block(raw, "on")
    if not on_body and not ON_KEY_RE.search(raw):
        errors.append(f"{source}: missing top-level on:")
        return errors

    jobs_body = _top_level_block(raw, "jobs")
    push_can_start = _push_targets_deploy_vercel(on_body)
    trigger_keys = _on_trigger_keys(on_body)

    for job_id, job_body in _job_blocks(jobs_body):
        job_if = _job_if(job_body)
        job_gated = _if_is_dispatch_clear_gate(job_if)
        for step in _step_blocks(job_body):
            run_text = _step_run(step)
            if not RAILWAY_UP_RE.search(run_text):
                continue
            name = _step_name(step)
            step_if = _step_if(step)
            step_gated = _if_is_dispatch_clear_gate(step_if)
            # A railway-up step is unsafe on push unless BOTH job and step
            # require workflow_dispatch + CLEAR, or the workflow has no push.
            if push_can_start and not (job_gated and step_gated):
                errors.append(
                    f"{source}: job {job_id!r} step {name or '(unnamed)'} runs "
                    "`railway up` on a workflow that still starts from push to "
                    "deploy-vercel without a dispatch+CLEAR gate on both the "
                    "job and the step"
                )
            if not step_gated and not job_gated:
                errors.append(
                    f"{source}: job {job_id!r} step {name or '(unnamed)'} has "
                    "unconditional `railway up` (need job or step if: "
                    "workflow_dispatch + CLEAR)"
                )
            if DEPLOY_STEP_RE.match(name) and not step_gated:
                errors.append(
                    f"{source}: {name!r} must be dispatch-only "
                    "(step if: must include workflow_dispatch and CLEAR)"
                )

    # Live contract for deploy-railway.yml: no push trigger at all (strongest).
    if source.endswith("deploy-railway.yml") or source == str(WORKFLOW):
        if "push" in trigger_keys:
            errors.append(
                f"{source}: on.push is present; C10/G4 requires removing the "
                "push trigger so merge of model-service (#655) cannot start "
                "this workflow"
            )
        if "workflow_dispatch" not in trigger_keys:
            errors.append(f"{source}: on.workflow_dispatch is required")
        if "confirm_c10_clear" not in text:
            errors.append(f"{source}: missing confirm_c10_clear hard-gate input")
        if "confirm_services" not in text:
            errors.append(f"{source}: missing confirm_services hard-gate input")

    return errors


def analyze_workflow_file(path: Path) -> list[str]:
    return analyze_workflow_text(path.read_text(encoding="utf-8"), source=str(path))


def scan_all_workflows() -> list[str]:
    errors: list[str] = []
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        errors.extend(analyze_workflow_file(path))
    return errors


def run_fixture_tests() -> list[str]:
    errors: list[str] = []
    dangerous = analyze_workflow_text(
        DANGEROUS_PUSH_AUTO_DEPLOY, source="fixture:dangerous-push-auto-deploy"
    )
    if not dangerous:
        errors.append(
            "fixture:dangerous-push-auto-deploy was accepted; checker is blind "
            "to the G4 hole (unconditional Deploy api on push)"
        )
    else:
        joined = "\n".join(dangerous)
        if "railway up" not in joined and "on.push" not in joined and "push" not in joined:
            errors.append(
                "fixture:dangerous-push-auto-deploy failed for the wrong reason: "
                + joined
            )

    safe = analyze_workflow_text(DISPATCH_ONLY_SAFE, source="fixture:dispatch-only-safe")
    # The live-file extra assertions (confirm inputs) are present in this fixture.
    # It is not named deploy-railway.yml so on.push absence is not extra-enforced
    # beyond railway-up gating — and it has no push, so it should be clean.
    if safe:
        errors.append(
            "fixture:dispatch-only-safe was rejected:\n  " + "\n  ".join(safe)
        )

    gated_push = analyze_workflow_text(
        PUSH_WITH_HARD_GATE, source="fixture:push-with-hard-gate"
    )
    if gated_push:
        errors.append(
            "fixture:push-with-hard-gate was rejected (job+step CLEAR gate "
            "should isolate railway-up from push):\n  " + "\n  ".join(gated_push)
        )

    return errors


def main() -> int:
    errors = run_fixture_tests()
    if not WORKFLOW.is_file():
        errors.append(f"missing {WORKFLOW}")
    else:
        errors.extend(analyze_workflow_file(WORKFLOW))
        # Re-scan every workflow so a second auto railway-up cannot hide.
        extra = scan_all_workflows()
        # analyze_workflow_file(WORKFLOW) is already included; keep unique.
        seen = set(errors)
        for e in extra:
            if e not in seen:
                errors.append(e)
                seen.add(e)

    if errors:
        print("Railway deploy isolation FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("Railway deploy isolation PASS")
    print("- fixture:dangerous-push-auto-deploy rejected (G4 hole closed in checker)")
    print("- fixture:dispatch-only-safe accepted")
    print("- fixture:push-with-hard-gate accepted")
    print(f"- live {WORKFLOW.relative_to(REPO)}: no on.push; railway-up is dispatch+CLEAR")
    print("- no other workflow auto railway-up on push to deploy-vercel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
