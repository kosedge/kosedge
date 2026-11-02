"""t5151u Package A — cohort enforcement (identity / membership only).

Shared hooks for the integration owner to call:

- before feature-output finalization
- before target-outcome loading

Reuses #698 ``last_played_cohort`` and accepted #698/#693/#5115 identity
records. Does not rebuild those systems. Does not score, fit, or run EVAL.
Numerical strengthening of ``metric_cohorts`` / ``eval_result_contract``
is Worker B.

Allowed lists come from the frozen task manifest — never from the output
under check. CERT=0. DRAFT≠merge.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .last_played_cohort import (
    EXPECTED_REG,
    EXPECTED_REG_TOTAL,
    ORIGINAL_502_PATH,
    ORIGINAL_502_SHA256,
    SCHEDULE_PATH,
    SCHEDULE_SHA256,
)
from .metric_cohorts import WILDCARD_2020_W18, cohort_sha256
from .recon_driver import sha256_file

SCHEMA = "nfl-t5151u-task-manifest-v1"
TICKET = "t5151u"
PACKAGE = "A_COHORT_ENFORCEMENT"
CERT_CANDIDATE = 0
OWNER_CLEAR_SHA8 = "d6aa1ef5"
COS_ORDER_A_SHA8 = "78db0e76"
R4_496_ACCEPTED_TIP = "bc1b62fc13a1c16ba1e39ccce39fb60180dc565e"
R4_496_STAMP = "c58ec422204406950d5605cdff5c172b54bd1a82"
ALEX_PASS_RO = "274cf246"
COS_ACCEPT = "12570bcb"

PROFILE_FEATURE_RECON_REG496 = "FEATURE_RECON_REG496"
PROFILE_DEV_IF437 = "DEV_IF437"
PROFILE_DEV_MARKET72 = "DEV_MARKET72"
PROFILES = (
    PROFILE_FEATURE_RECON_REG496,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
)
FORBIDDEN_SUBSTITUTION_COUNTS = (496, 437, 94, 72)
NORMALIZED_94_N = 94
NORMALIZED_94_TIP_REFUSED = "0a49afa3"

REG496_N = EXPECTED_REG_TOTAL
REG496_BY_SEASON = {str(k): v for k, v in EXPECTED_REG.items()}
DEV_IF437_N = 437
DEV_IF437_BY_SEASON = {"2020": 210, "2021": 227}
DEV_MARKET72_N = 72
DEV_MARKET72_BY_SEASON = {"2020": 35, "2021": 37}

REG496_IDENTITY_SHA256 = (
    "6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640"
)
DEV_IF437_IDENTITY_SHA256 = (
    "92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49"
)
DEV_MARKET72_FILE_SHA256 = (
    "9f754b0e1c7680a0051b119ec59e2f0603236be447c483491b90a70af61b81e6"
)
DEV_MARKET72_IDENTITY_SHA256 = (
    "bcf90863d8b5ffccd67c1d69e058e9174a9cdaa2a701aff9134a9ef6d9ab62b2"
)
FEATURE_RECON_REG496_ARTIFACT_PATH = (
    "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_REG.json"
)
FEATURE_RECON_REG496_ARTIFACT_SHA256 = (
    "282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c"
)
METRIC_COHORTS_PATH = "data/ops/nfl-forecast-builder-t5107u/METRIC_COHORTS_t5115u.json"
ACCEPTED_MARKET72_PATH = (
    "data/ops/nfl-t5151u-cohort-enforcement/ACCEPTED_DEV_MARKET72_IDS.json"
)
TASK_MANIFEST_NAME = "TASK_MANIFEST.json"
OUT_DIR = Path("data/ops/nfl-t5151u-cohort-enforcement")
TASK_MANIFEST_REL = f"{OUT_DIR.as_posix()}/{TASK_MANIFEST_NAME}"
# Pinned after freeze — never derive from an output under check.
TASK_MANIFEST_SHA256 = (
    "c61ca6948ecfd1ea79f785e63117cc3399725fc893be2ea398b4b91ece42bb14"
)
REG_W18_2021_N = 16

LIMITATIONS = {
    "publication_timestamp_status": "unverified",
    "observation_timestamp_status": "unverified",
    "fit_label": "RETRO_FIT",
    "label": "RECONSTRUCTED",
    "production_causal_claim": False,
    "nfl_green": False,
    "eval": None,
    "cert_candidate": CERT_CANDIDATE,
}


class CohortEnforcementRefuse(ValueError):
    """Fail-closed cohort membership / identity gate. Not a retune. Not EVAL."""


class OutcomeReadSpy:
    """Test spy: counts target-outcome reads. Hooks must not invoke this."""

    def __init__(
        self, fn: Callable[[], Mapping[str, Mapping[str, Any]]] | None = None
    ) -> None:
        self.reads = 0
        self.ids_returned: list[str] = []
        self._fn = fn

    def __call__(self) -> Mapping[str, Mapping[str, Any]]:
        self.reads += 1
        loaded = self._fn() if self._fn is not None else {}
        self.ids_returned = list(loaded)
        return loaded


def cohort_identity_sha256(game_ids: Sequence[str]) -> str:
    """Reuse the t5115u identity hash (not a new cohort system)."""
    return cohort_sha256(list(game_ids))


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def _n_by_season(game_ids: Sequence[str]) -> dict[str, int]:
    counts = Counter(str(gid).split("_", 1)[0] for gid in game_ids)
    return dict(sorted(counts.items()))


def _as_ids(values: Sequence[str] | None) -> list[str]:
    return [str(v) for v in (values or [])]


def assert_unique(game_ids: Sequence[str], *, label: str) -> None:
    ids = _as_ids(game_ids)
    if len(ids) != len(set(ids)):
        dupes = sorted({g for g in ids if ids.count(g) > 1})
        raise CohortEnforcementRefuse(f"{label}: duplicate game_id {dupes[:8]}")


def assert_exact_membership(
    candidate_ids: Sequence[str],
    expected_ids: Sequence[str],
    *,
    label: str,
) -> None:
    got = _as_ids(candidate_ids)
    want = _as_ids(expected_ids)
    assert_unique(got, label=f"{label} candidate")
    assert_unique(want, label=f"{label} expected")
    extra = sorted(set(got) - set(want))
    missing = sorted(set(want) - set(got))
    if extra or missing or len(got) != len(want):
        raise CohortEnforcementRefuse(
            f"{label}: exact set mismatch extra={extra[:8]} missing={missing[:8]} "
            f"n={len(got)} expected_n={len(want)}"
        )


def assert_not_substitution(profile: str, candidate_ids: Sequence[str]) -> None:
    """Forbid swapping 496 / 437 / 94 / 72 for one another."""
    n = len(candidate_ids)
    expected = {
        PROFILE_FEATURE_RECON_REG496: REG496_N,
        PROFILE_DEV_IF437: DEV_IF437_N,
        PROFILE_DEV_MARKET72: DEV_MARKET72_N,
    }[profile]
    if n == NORMALIZED_94_N:
        raise CohortEnforcementRefuse(
            f"{profile}: refusing #694 normalized 94-DEV substitution "
            f"({NORMALIZED_94_TIP_REFUSED})"
        )
    if n != expected and n in FORBIDDEN_SUBSTITUTION_COUNTS:
        raise CohortEnforcementRefuse(
            f"{profile}: refusing substitution of {n} for expected {expected}"
        )
    if n != expected:
        raise CohortEnforcementRefuse(
            f"{profile}: n={n} != expected {expected}"
        )


def build_task_manifest(
    *,
    reg496_ids: Sequence[str],
    if437_ids: Sequence[str],
    market72_ids: Sequence[str],
) -> dict[str, Any]:
    """Assemble the versioned SoT. Caller writes bytes; checks load those bytes."""
    reg = _as_ids(reg496_ids)
    if437 = _as_ids(if437_ids)
    market72 = _as_ids(market72_ids)
    if len(reg) != REG496_N or _n_by_season(reg) != REG496_BY_SEASON:
        raise CohortEnforcementRefuse("FEATURE_RECON_REG496 freeze counts drifted")
    if len(if437) != DEV_IF437_N or _n_by_season(if437) != DEV_IF437_BY_SEASON:
        raise CohortEnforcementRefuse("DEV_IF437 freeze counts drifted")
    if len(market72) != DEV_MARKET72_N or _n_by_season(market72) != DEV_MARKET72_BY_SEASON:
        raise CohortEnforcementRefuse("DEV_MARKET72 freeze counts drifted")
    if cohort_identity_sha256(reg) != REG496_IDENTITY_SHA256:
        raise CohortEnforcementRefuse("FEATURE_RECON_REG496 identity hash drifted")
    if cohort_identity_sha256(if437) != DEV_IF437_IDENTITY_SHA256:
        raise CohortEnforcementRefuse("DEV_IF437 identity hash drifted vs 92b91585")
    if cohort_identity_sha256(market72) != DEV_MARKET72_IDENTITY_SHA256:
        raise CohortEnforcementRefuse("DEV_MARKET72 identity hash drifted vs bcf90863")
    if set(WILDCARD_2020_W18) & set(reg):
        raise CohortEnforcementRefuse("REG496 freeze contains 2020 Wild Cards")
    w18 = [g for g in reg if g.startswith("2021_18_")]
    if len(w18) != REG_W18_2021_N:
        raise CohortEnforcementRefuse("2021 REG week 18 not retained in REG496 freeze")
    if not set(if437) <= set(reg):
        raise CohortEnforcementRefuse("DEV_IF437 is not a subset of FEATURE_RECON_REG496")
    if not set(market72) <= set(reg):
        raise CohortEnforcementRefuse("DEV_MARKET72 is not a subset of FEATURE_RECON_REG496")
    return {
        "schema_version": SCHEMA,
        "ticket": TICKET,
        "package": PACKAGE,
        "cert_candidate": CERT_CANDIDATE,
        "draft": True,
        "frozen_before_verification": True,
        "allowed_list_source": "this_manifest_not_output_under_check",
        "owner_clear_sha8": OWNER_CLEAR_SHA8,
        "cos_order_a_sha8": COS_ORDER_A_SHA8,
        "reuse": {
            "r4_496_accepted_tip": R4_496_ACCEPTED_TIP,
            "r4_496_stamp": R4_496_STAMP,
            "pr_698_draft": True,
            "alex_pass_ro": ALEX_PASS_RO,
            "cos_accept": COS_ACCEPT,
            "last_played_cohort": "services/model-service/src/services/nfl_t5107u/last_played_cohort.py",
            "metric_cohorts_starting_point": "services/model-service/src/services/nfl_t5107u/metric_cohorts.py",
            "eval_result_contract_starting_point": (
                "PR #693 eval_result_contract.py — numerical strengthening is Worker B"
            ),
            "do_not_rebuild_duplicate_cohort_systems": True,
        },
        "authoritative_reg_schedule": {
            "path": SCHEDULE_PATH,
            "sha256": SCHEDULE_SHA256,
            "membership_rule": (
                "season_type=REG AND season in {2020,2021} AND week>=2 — not week<=18"
            ),
        },
        "original_502_preserved": {
            "path": ORIGINAL_502_PATH,
            "sha256": ORIGINAL_502_SHA256,
            "historical_only": True,
            "do_not_accept_as_regular_season_coverage": True,
            "deviation": "6x2020 Wild Card (NON_REG_WILDCARD)",
        },
        "exclusions": {
            "kind": "NON_REG_WILDCARD",
            "game_ids": list(WILDCARD_2020_W18),
            "n": 6,
            "source": "metric_cohorts.WILDCARD_2020_W18",
        },
        "retain": {
            "reg_2021_week_18": True,
            "n_2021_week_18": REG_W18_2021_N,
        },
        "forbid_substitution": list(FORBIDDEN_SUBSTITUTION_COUNTS),
        "normalized_94_tip_refused": NORMALIZED_94_TIP_REFUSED,
        "profiles": {
            PROFILE_FEATURE_RECON_REG496: {
                "n": REG496_N,
                "n_by_season": REG496_BY_SEASON,
                "identity_sha256": REG496_IDENTITY_SHA256,
                "accepted_artifact_path": FEATURE_RECON_REG496_ARTIFACT_PATH,
                "accepted_artifact_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
                "source": "authoritative REG schedule membership (not the 496 output under check)",
                "game_ids": reg,
            },
            PROFILE_DEV_IF437: {
                "n": DEV_IF437_N,
                "n_by_season": DEV_IF437_BY_SEASON,
                "identity_sha256": DEV_IF437_IDENTITY_SHA256,
                "source": f"{METRIC_COHORTS_PATH}#dev_reg",
                "game_ids": if437,
            },
            PROFILE_DEV_MARKET72: {
                "n": DEV_MARKET72_N,
                "n_by_season": DEV_MARKET72_BY_SEASON,
                "accepted_file_path": ACCEPTED_MARKET72_PATH,
                "accepted_file_sha256": DEV_MARKET72_FILE_SHA256,
                "identity_sha256": DEV_MARKET72_IDENTITY_SHA256,
                "source": "accepted matched72 identity 9f754b0e (not #694 94-DEV)",
                "game_ids": market72,
            },
        },
        "limitations": dict(LIMITATIONS),
        "hooks": {
            "before_feature_output_finalization": (
                "check_cohort_before_feature_output_finalization"
            ),
            "before_target_outcome_loading": (
                "check_cohort_before_target_outcome_loading"
            ),
            "wired_by": "integration_owner_worker_B",
        },
        "stop": "PACKAGE_A_IMPLEMENTED_AWAITING_WORKER_B_INTEGRATION",
    }


def load_frozen_manifest(root: Path | None = None) -> dict[str, Any]:
    """Load the pinned task manifest. Refuse if bytes changed."""
    repo = _repo_root(root)
    path = repo / TASK_MANIFEST_REL
    digest = sha256_file(path)
    if TASK_MANIFEST_SHA256.startswith("PENDING_"):
        raise CohortEnforcementRefuse("task manifest hash not pinned — freeze first")
    if digest != TASK_MANIFEST_SHA256:
        raise CohortEnforcementRefuse(
            f"task manifest sha {digest} != pinned {TASK_MANIFEST_SHA256}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA:
        raise CohortEnforcementRefuse("task manifest schema drifted")
    if payload.get("allowed_list_source") != "this_manifest_not_output_under_check":
        raise CohortEnforcementRefuse("allowed list must come from the frozen manifest")
    return payload


def expected_profile_ids(profile: str, root: Path | None = None) -> list[str]:
    manifest = load_frozen_manifest(root)
    body = (manifest.get("profiles") or {}).get(profile)
    if not isinstance(body, Mapping):
        raise CohortEnforcementRefuse(f"unknown profile {profile}")
    return _as_ids(body.get("game_ids"))


def _schedule_index(root: Path) -> dict[str, dict[str, Any]]:
    path = root / SCHEDULE_PATH
    digest = sha256_file(path)
    if digest != SCHEDULE_SHA256:
        raise CohortEnforcementRefuse(f"schedule sha {digest} != pin {SCHEDULE_SHA256}")
    out: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            gid = str(row["game_id"])
            out[gid] = {
                "game_id": gid,
                "season": int(row["season"]),
                "week": int(row["week"]),
                "season_type": str(row["season_type"]).upper(),
            }
    return out


def assert_season_type(
    game_ids: Sequence[str],
    root: Path | None = None,
    *,
    label: str,
) -> None:
    repo = _repo_root(root)
    index = _schedule_index(repo)
    for gid in _as_ids(game_ids):
        row = index.get(gid)
        if row is None:
            raise CohortEnforcementRefuse(f"{label}: {gid} not on frozen REG schedule extract")
        if row["season"] not in (2020, 2021):
            raise CohortEnforcementRefuse(f"{label}: {gid} season {row['season']} outside 2020-21")
        if row["season_type"] != "REG":
            raise CohortEnforcementRefuse(
                f"{label}: {gid} season_type={row['season_type']} (REG required)"
            )
        if row["week"] < 2:
            raise CohortEnforcementRefuse(f"{label}: {gid} week {row['week']} < 2")


def assert_exclusions(game_ids: Sequence[str], *, label: str) -> None:
    leaked = [g for g in _as_ids(game_ids) if g in set(WILDCARD_2020_W18)]
    if leaked:
        raise CohortEnforcementRefuse(f"{label}: 2020 Wild Card leaked {leaked}")


def assert_2021_reg_w18_retained(game_ids: Sequence[str], *, profile: str) -> None:
    if profile != PROFILE_FEATURE_RECON_REG496:
        return
    w18 = [g for g in _as_ids(game_ids) if g.startswith("2021_18_")]
    if len(w18) != REG_W18_2021_N:
        raise CohortEnforcementRefuse(
            f"{profile}: 2021 REG week 18 count {len(w18)} != {REG_W18_2021_N}"
        )


def assert_matching_sample(
    *,
    profile: str,
    expected_ids: Sequence[str],
    requested_arm_ids: Mapping[str, Sequence[str]] | None,
    joined_ids: Sequence[str] | None,
) -> None:
    want = _as_ids(expected_ids)
    if requested_arm_ids:
        for arm, ids in requested_arm_ids.items():
            if arm not in PROFILES:
                raise CohortEnforcementRefuse(f"unknown requested arm {arm}")
            if arm == profile:
                assert_exact_membership(ids, want, label=f"requested arm {arm}")
            else:
                assert_not_substitution(arm, ids)
        if joined_ids is not None and profile in requested_arm_ids:
            assert_exact_membership(
                joined_ids,
                requested_arm_ids[profile],
                label=f"{profile} requested-vs-joined",
            )
    if joined_ids is not None:
        assert_exact_membership(joined_ids, want, label=f"{profile} joined")


def _assert_bytes(
    *,
    candidate_bytes_sha: str | None,
    expected_bytes_sha: str | None,
    label: str,
) -> None:
    if candidate_bytes_sha is None or expected_bytes_sha is None:
        return
    if candidate_bytes_sha != expected_bytes_sha:
        raise CohortEnforcementRefuse(
            f"{label}: changed frozen bytes {candidate_bytes_sha} != {expected_bytes_sha}"
        )


def _never_call_loader(outcome_loader: Any) -> None:
    """Hooks run BEFORE target-outcome loading. Never invoke the loader."""
    if outcome_loader is not None and getattr(outcome_loader, "reads", None) not in (None, 0):
        raise CohortEnforcementRefuse("outcome loader already read — refuse (join-before-gate)")


def check_cohort_before_feature_output_finalization(
    profile: str,
    candidate_ids: Sequence[str],
    *,
    joined_ids: Sequence[str] | None = None,
    requested_arm_ids: Mapping[str, Sequence[str]] | None = None,
    candidate_bytes_sha: str | None = None,
    expected_bytes_sha: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Gate feature-output finalization. Allowed IDs come from the manifest."""
    if profile not in PROFILES:
        raise CohortEnforcementRefuse(f"unknown profile {profile}")
    expected = expected_profile_ids(profile, root)
    assert_unique(candidate_ids, label=profile)
    assert_not_substitution(profile, candidate_ids)
    assert_exact_membership(candidate_ids, expected, label=profile)
    assert_season_type(candidate_ids, root, label=profile)
    assert_exclusions(candidate_ids, label=profile)
    assert_2021_reg_w18_retained(candidate_ids, profile=profile)
    assert_matching_sample(
        profile=profile,
        expected_ids=expected,
        requested_arm_ids=requested_arm_ids,
        joined_ids=joined_ids,
    )
    _assert_bytes(
        candidate_bytes_sha=candidate_bytes_sha,
        expected_bytes_sha=expected_bytes_sha,
        label=f"{profile} feature-output",
    )
    return {
        "ok": True,
        "gate": "before_feature_output_finalization",
        "profile": profile,
        "n": len(expected),
        "n_by_season": _n_by_season(expected),
        "identity_sha256": cohort_identity_sha256(expected),
        "limitations": dict(LIMITATIONS),
        "cert_candidate": CERT_CANDIDATE,
    }


def check_cohort_before_target_outcome_loading(
    profile: str,
    candidate_ids: Sequence[str],
    *,
    frozen_bytes_sha: str | None = None,
    expected_bytes_sha: str | None = None,
    coverage_blocked: bool = False,
    outcome_loader: OutcomeReadSpy | Callable[[], Any] | None = None,
    joined_ids: Sequence[str] | None = None,
    requested_arm_ids: Mapping[str, Sequence[str]] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Gate target-outcome loading. Never reads scoring outcomes itself."""
    _never_call_loader(outcome_loader)
    if coverage_blocked:
        raise CohortEnforcementRefuse(
            "blocked coverage — refuse before target-outcome loading"
        )
    if (
        frozen_bytes_sha is not None
        and expected_bytes_sha is not None
        and frozen_bytes_sha != expected_bytes_sha
    ):
        raise CohortEnforcementRefuse(
            "changed frozen bytes — refuse before target-outcome loading"
        )
    result = check_cohort_before_feature_output_finalization(
        profile,
        candidate_ids,
        joined_ids=joined_ids,
        requested_arm_ids=requested_arm_ids,
        candidate_bytes_sha=frozen_bytes_sha,
        expected_bytes_sha=expected_bytes_sha,
        root=root,
    )
    result["gate"] = "before_target_outcome_loading"
    result["outcome_loader_invoked"] = False
    if outcome_loader is not None and getattr(outcome_loader, "reads", 0) != 0:
        raise CohortEnforcementRefuse("outcome loader invoked during gate — refuse")
    return result


def load_artifact_game_ids(path: Path) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return _as_ids(payload)
    if "game_ids" in payload:
        return _as_ids(payload["game_ids"])
    if "identities" in payload:
        return _as_ids(row["game_id"] for row in payload["identities"])
    raise CohortEnforcementRefuse(f"no game_ids in {path}")
