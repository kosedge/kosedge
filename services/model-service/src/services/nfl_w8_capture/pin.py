"""AC-4 pin / manifest shape. Placeholders allowed; no fabricated SHAs."""

from __future__ import annotations

from typing import Any, Mapping

UNSET_SHA = ""
UNSET = "UNSET"

REQUIRED_MANIFEST_FIELDS = (
    "spec_id",
    "spec_sha8",
    "part_b_sha8",
    "part_b_freeze_sha8",
    "decision_rd7_id",
    "code_commit_sha",
    "model_weights_params_sha",
    "blend_weight",
    "hfa",
    "priors_sha",
    "calibration_sha",
    "feature_schema_sha",
    "input_shas",
    "interpreter_path",
    "interpreter_version",
    "interpreter_freeze_sha",
    "host_id",
    "runner_id",
    "s_ind_forbidden_input_check",
    "odds_api_hold",
    "nfl_no_go",
    "coming_soon_unchanged",
    "seal_ack",
)


def build_pin_manifest(
    *,
    code_commit_sha: str = UNSET_SHA,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the AC-4 field shape. Empty sha strings mean not pinned yet."""
    if code_commit_sha and _looks_invented(code_commit_sha):
        raise ValueError("do not invent fake shas; pass a real commit or leave UNSET")

    manifest: dict[str, Any] = {
        "spec_id": "IMV_SPEC_W8_PROSPECTIVE_CAPTURE_ACCEPTANCE_t4191u_v2",
        "spec_sha8": "08808adf",
        "part_b_sha8": "0448042a",
        "part_b_freeze_sha8": "2e40ead4",
        "decision_rd7_id": "DECISION_RYAN_t4445u_RD7_CURSOR_W8_BUILDER_v1",
        "decision_rd7_ops_cite_sha8": "91aebe69",
        "pr_unblock_sha8": "0511c346",
        "code_commit_sha": code_commit_sha or UNSET_SHA,
        "model_weights_params_sha": UNSET_SHA,
        "blend_weight": UNSET,
        "hfa": UNSET,
        "priors_sha": UNSET_SHA,
        "calibration_sha": UNSET_SHA,
        "feature_schema_sha": UNSET_SHA,
        "input_shas": {
            "pbp": UNSET_SHA,
            "schedule": UNSET_SHA,
            "injury": UNSET_SHA,
            "weather": UNSET_SHA,
            "odds_vintage": UNSET_SHA,
        },
        "interpreter_path": UNSET,
        "interpreter_version": UNSET,
        "interpreter_freeze_sha": UNSET_SHA,
        "host_id": UNSET,
        "runner_id": UNSET,
        "s_ind_forbidden_input_check": "src.services.nfl_w8_capture.streams.check_s_ind_forbidden_inputs",
        "odds_api_hold": True,
        "nfl_no_go": True,
        "coming_soon_unchanged": True,
        "seal_ack": "CURSOR_CANNOT_SEAL_ACK",
        "t4447u_parallel": True,
    }
    if extra:
        manifest.update(dict(extra))
    return manifest


def validate_pin_manifest(manifest: Mapping[str, Any]) -> list[str]:
    missing = [field for field in REQUIRED_MANIFEST_FIELDS if field not in manifest]
    issues = [f"missing:{field}" for field in missing]
    for field in (
        "code_commit_sha",
        "model_weights_params_sha",
        "feature_schema_sha",
        "interpreter_freeze_sha",
    ):
        value = manifest.get(field)
        if value and _looks_invented(str(value)):
            issues.append(f"invented_sha:{field}")
    inputs = manifest.get("input_shas")
    if not isinstance(inputs, dict):
        issues.append("input_shas_not_object")
    else:
        for name in ("pbp", "schedule", "injury", "weather", "odds_vintage"):
            if name not in inputs:
                issues.append(f"missing_input_sha:{name}")
            elif inputs[name] and _looks_invented(str(inputs[name])):
                issues.append(f"invented_sha:input_shas.{name}")
    if manifest.get("seal_ack") not in {None, "", "CURSOR_CANNOT_SEAL_ACK"}:
        issues.append("seal_ack_must_remain_blocked")
    if manifest.get("odds_api_hold") is not True:
        issues.append("odds_api_hold_must_remain_true")
    if manifest.get("nfl_no_go") is not True:
        issues.append("nfl_no_go_must_remain_true")
    return issues


def _looks_invented(value: str) -> bool:
    """Reject obvious placeholder hex that is not a real recorded pin."""
    text = value.strip().lower()
    if not text or text in {"unset", "todo", "tbd", "pending"}:
        return False
    if text in {"deadbeef", "cafebabe", "0123456789abcdef"}:
        return True
    if text.startswith("fake") or text.startswith("dummy"):
        return True
    return False
