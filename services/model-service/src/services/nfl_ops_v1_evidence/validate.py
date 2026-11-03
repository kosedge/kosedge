"""Validate an NFL_OPS_V1 evidence manifest. No invented defaults. CERT=0."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from src.services.nfl_fixture_assembly.assemble import NON_FIXTURE_CONSUMERS
from src.services.nfl_fixture_assembly.chain import chain_digest
from src.services.nfl_hhl1_capture.constants import DECISION_OFFSET_BEFORE_KICKOFF_MINUTES
from src.services.nfl_hhl1_capture.identity import canonical_json, parse_utc, sha256_hex
from src.services.nfl_ops_v1_evidence.constants import (
    ALLOWED_TOP_LEVEL,
    BASE_DEPLOY_VERCEL,
    CERT,
    CONSUME_PENDING_KEYS,
    DATA_LABEL,
    EVIDENCE_LABELS,
    EXPECTED_COMMAND,
    JOINT_CONTRACT,
    PACKAGE,
    PINNED_AWAY,
    PINNED_CAPTURE_ID,
    PINNED_CHAIN_DIGEST,
    PINNED_DEFENSE_MULT,
    PINNED_DEFENSE_RAW,
    PINNED_FORECAST_ID,
    PINNED_GAME_ID,
    PINNED_HOME,
    PINNED_LINE,
    PINNED_N,
    PINNED_OFFENSE_MULT,
    PINNED_OFFENSE_RAW,
    PINNED_PERIOD,
    PINNED_POINT_MARGIN,
    PINNED_PRICE,
    PINNED_SEASON,
    PINNED_TEAM,
    PINNED_WEEK,
    PRE_CONSUME_REQUIRED,
    PROFILE,
    PROTOCOL,
    REQUIRED_TOP_LEVEL,
    SCHEMA_VERSION,
    STAGE_PRE_CONSUME,
    STAGE_PRE_RECEIPT,
    TYPED_REF_KINDS,
)
from src.services.nfl_ops_v1_evidence.finite import (
    require_bool,
    require_finite,
    require_int,
    require_str,
)
from src.services.nfl_ops_v1_evidence.hashes import require_sha256_hex
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.schema import schema_hash, spec_hash
from src.services.nfl_ops_v1_evidence.verify import (
    VerificationContext,
    is_git_commit_sha,
)
from src.services.nfl_ops_v1_evidence.profiles import require_active_profile
from src.services.nfl_ops_v1_evidence.worker_handoff import validate_worker_handoff


def _as_map(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceGateRefuse(
            f"{name} must be an object",
            refuse_class=RefuseClass.TYPE,
        )
    return dict(value)


def _refuse(refuse_class: str, reason: str, **detail: Any) -> None:
    raise EvidenceGateRefuse(reason, refuse_class=refuse_class, detail=detail)


def _required_present(manifest: Mapping[str, Any], keys: tuple[str, ...], *, stage: str) -> None:
    missing = [key for key in keys if key not in manifest]
    if missing:
        _refuse(RefuseClass.INCOMPLETE, f"{stage} missing required fields {missing}")


def _check_extra(manifest: Mapping[str, Any]) -> None:
    extra = sorted(set(manifest.keys()) - ALLOWED_TOP_LEVEL)
    if extra:
        _refuse(RefuseClass.EXTRA, f"unexpected top-level keys {extra}")


def _check_package_identity(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"schema_version {manifest.get('schema_version')!r} != {SCHEMA_VERSION}",
        )
    if manifest.get("package") != PACKAGE:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, f"package {manifest.get('package')!r} != {PACKAGE}")
    if manifest.get("protocol") != PROTOCOL:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"protocol {manifest.get('protocol')!r} != {PROTOCOL}",
        )
    if manifest.get("joint_contract") != JOINT_CONTRACT:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"joint_contract {manifest.get('joint_contract')!r} != {JOINT_CONTRACT}",
        )
    profile = require_active_profile(manifest.get("profile"))
    if manifest.get("authority") != profile.authority:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"authority {manifest.get('authority')!r} != {profile.authority}",
        )
    if manifest.get("owner_clear") != profile.owner_clear:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"owner_clear {manifest.get('owner_clear')!r} != {profile.owner_clear}",
        )
    if manifest.get("scope_id") != profile.scope_id:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"scope_id {manifest.get('scope_id')!r} != {profile.scope_id}",
        )
    if manifest.get("owner") != profile.owner:
        _refuse(RefuseClass.WRONG_PROFILE_IDENTITY, f"owner {manifest.get('owner')!r} != {profile.owner}")
    if type(manifest.get("cert")) is not int or manifest.get("cert") != CERT:
        _refuse(RefuseClass.TYPE, f"cert must be int {CERT} (got {manifest.get('cert')!r})")


def _check_typed_git(obj: Any, name: str) -> str:
    row = _as_map(obj, name)
    if row.get("kind") != "git_commit":
        _refuse(RefuseClass.TYPE, f"{name}.kind must be git_commit")
    value = require_str(row.get("value"), f"{name}.value")
    if not is_git_commit_sha(value):
        _refuse(
            RefuseClass.TYPE,
            f"{name}.value is not a 40-hex git commit (got {value!r})",
        )
    return value


def _check_data_label(manifest: Mapping[str, Any]) -> None:
    label = manifest.get("data_label")
    if label is None:
        _refuse(RefuseClass.INCOMPLETE, "data_label missing")
    if label != DATA_LABEL:
        _refuse(
            RefuseClass.REAL_MODE,
            f"data_label={label!r} refused before readers/model/network/DB/job",
        )


def _check_execution(manifest: Mapping[str, Any], *, stage: str) -> dict[str, Any]:
    execution = _as_map(manifest.get("execution"), "execution")
    if execution.get("import_only") is True:
        _refuse(RefuseClass.IMPORT_ONLY, "import-only is not integrated execution")
    if execution.get("saved_output_only") is True:
        _refuse(
            RefuseClass.SAVED_OUTPUT_ONLY,
            "saved-output-only is not actual produce→consume execution",
        )
    produce_here = require_bool(
        execution.get("produce_invoked_here"), "execution.produce_invoked_here"
    )
    if not produce_here:
        _refuse(
            RefuseClass.SAVED_OUTPUT_ONLY,
            "produce_fixture_chain was not invoked in this process",
        )
    consume_here = execution.get("consume_invoked_here")
    if stage == STAGE_PRE_RECEIPT:
        if consume_here is not True:
            _refuse(
                RefuseClass.SAVED_OUTPUT_ONLY,
                "consume_fixture_chain was not invoked in this process",
            )
    elif consume_here not in (False, True):
        _refuse(RefuseClass.TYPE, "execution.consume_invoked_here must be bool")
    return execution


def _check_hash_bindings(manifest: Mapping[str, Any]) -> None:
    spec = require_sha256_hex(manifest.get("spec_hash"), "spec_hash")
    schema = require_sha256_hex(manifest.get("schema_hash"), "schema_hash")
    input_h = require_sha256_hex(manifest.get("input_hash"), "input_hash")
    history_h = require_sha256_hex(manifest.get("history_hash"), "history_hash")
    config_h = require_sha256_hex(manifest.get("config_hash"), "config_hash")
    code_h = require_sha256_hex(manifest.get("code_hash"), "code_hash")
    if spec != spec_hash():
        _refuse(RefuseClass.HASH_MUTATED, "spec_hash does not match sealed spec body")
    if schema != schema_hash():
        _refuse(RefuseClass.HASH_MUTATED, "schema_hash does not match sealed schema body")
    if input_h == schema:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "input_hash must not be a copy of schema_hash",
        )
    if history_h == schema or config_h == schema or code_h == schema:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "history/config/code hash must not be a copy of schema_hash",
        )
    bindings = _as_map(manifest.get("hash_bindings"), "hash_bindings")
    for name, digest in (
        ("schema", schema),
        ("input", input_h),
        ("history", history_h),
        ("config", config_h),
        ("code", code_h),
    ):
        row = _as_map(bindings.get(name), f"hash_bindings.{name}")
        source = require_str(row.get("source"), f"hash_bindings.{name}.source")
        if name == "schema" and source != "schema_body":
            _refuse(RefuseClass.HASH_MUTATED, "schema hash source must be schema_body")
        if name == "input" and source in {"schema_body", "schema_hash"}:
            _refuse(
                RefuseClass.HASH_MUTATED,
                "input hash source cannot be schema",
            )
        require_sha256_hex(row.get("sha256"), f"hash_bindings.{name}.sha256")
        if row.get("sha256") != digest:
            _refuse(
                RefuseClass.HASH_MUTATED,
                f"hash_bindings.{name}.sha256 != top-level {name}_hash",
            )


def _check_identities(manifest: Mapping[str, Any]) -> dict[str, Any]:
    ident = _as_map(manifest.get("input_identities"), "input_identities")
    if ident.get("game_id") != PINNED_GAME_ID:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"game_id {ident.get('game_id')!r} != {PINNED_GAME_ID}",
        )
    if ident.get("team") != PINNED_TEAM:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"team {ident.get('team')!r} != {PINNED_TEAM}",
        )
    if ident.get("season") != PINNED_SEASON:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"season {ident.get('season')!r} != {PINNED_SEASON}",
        )
    if ident.get("week") != PINNED_WEEK:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"week {ident.get('week')!r} != {PINNED_WEEK}",
        )
    if ident.get("period") != PINNED_PERIOD:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"period {ident.get('period')!r} != {PINNED_PERIOD}",
        )
    if ident.get("away") != PINNED_AWAY or ident.get("home") != PINNED_HOME:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            "home/away identity mismatch vs pinned synthetic game",
        )
    freshness = ident.get("freshness")
    if freshness in (None, "", "UNKNOWN"):
        _refuse(RefuseClass.STALE, "unknown freshness refused")
    if ident.get("observation") != "OBSERVED":
        _refuse(
            RefuseClass.STALE,
            f"observation {ident.get('observation')!r} is not OBSERVED",
        )
    if ident.get("availability") != "availability":
        _refuse(
            RefuseClass.STALE,
            f"availability factor {ident.get('availability')!r} unsupported",
        )
    return ident


def _check_cohort(manifest: Mapping[str, Any]) -> None:
    cohort = _as_map(manifest.get("cohort"), "cohort")
    n = require_int(cohort.get("n"), "cohort.n")
    ids = cohort.get("game_ids")
    if not isinstance(ids, list):
        _refuse(RefuseClass.TYPE, "cohort.game_ids must be a list")
    if n != PINNED_N or len(ids) != PINNED_N:
        _refuse(
            RefuseClass.WRONG_COUNT,
            f"cohort n={n} ids={len(ids)} != pinned {PINNED_N}",
        )
    if ids != [PINNED_GAME_ID]:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"cohort.game_ids {ids!r} != [{PINNED_GAME_ID}]",
        )


def _check_labels(manifest: Mapping[str, Any]) -> None:
    labels = _as_map(manifest.get("evidence_labels"), "evidence_labels")
    if not labels:
        _refuse(RefuseClass.INCOMPLETE, "evidence_labels empty")
    for key, value in labels.items():
        if value not in EVIDENCE_LABELS:
            _refuse(
                RefuseClass.TYPE,
                f"evidence_labels.{key}={value!r} not in {sorted(EVIDENCE_LABELS)}",
            )
    if labels.get("inherited_real_outcome_tests") != "NOT_RUN":
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            "inherited real-outcome tests must stay NOT_RUN",
        )


def _check_trace(manifest: Mapping[str, Any], *, stage: str) -> dict[str, Any]:
    trace = _as_map(manifest.get("producer_consumer_trace"), "producer_consumer_trace")
    if not trace.get("producer") or not trace.get("consumer"):
        _refuse(RefuseClass.PAIRED_ARM, "paired-arm producer/consumer missing")
    producer_digest = require_sha256_hex(
        trace.get("producer_digest") or manifest.get("common_digest"),
        "producer_consumer_trace.producer_digest",
    )
    common = require_sha256_hex(manifest.get("common_digest"), "common_digest")
    if common != PINNED_CHAIN_DIGEST:
        _refuse(
            RefuseClass.HASH_MUTATED,
            f"common_digest {common} != pinned {PINNED_CHAIN_DIGEST}",
        )
    if producer_digest != common:
        _refuse(RefuseClass.PAIRED_ARM, "producer_digest != common_digest")
    if stage == STAGE_PRE_RECEIPT:
        consumer_digest = require_sha256_hex(
            trace.get("consumer_digest"), "producer_consumer_trace.consumer_digest"
        )
        if consumer_digest != producer_digest:
            _refuse(RefuseClass.PAIRED_ARM, "consumer_digest != producer_digest")
    return trace


def _check_channel(payload: Optional[Mapping[str, Any]], manifest: Mapping[str, Any]) -> None:
    if payload is None:
        return
    if "channel" not in payload:
        _refuse(RefuseClass.CHANNEL, "channel absent (malformed vs absence)")
    channel = payload.get("channel")
    if channel in (None, ""):
        _refuse(RefuseClass.CHANNEL, "malformed empty channel")
    if channel != "FIXTURE":
        _refuse(RefuseClass.CHANNEL, f"channel={channel!r} is not FIXTURE")
    if payload.get("production_mode") is True or payload.get("cacheable") is True:
        _refuse(RefuseClass.CONSUMER, "production_mode/cacheable cannot pass this gate")
    consumer = None
    if isinstance(manifest.get("producer_consumer_trace"), Mapping):
        consumer = manifest["producer_consumer_trace"].get("consumer_name")
    if isinstance(consumer, str) and consumer.strip().lower() in NON_FIXTURE_CONSUMERS:
        _refuse(
            RefuseClass.CONSUMER,
            f"direct API/consumer/cache path {consumer!r} refused",
        )


def validate_cutoff(cutoff: Mapping[str, Any]) -> None:
    """cutoff−1 / equal / +1 plus availability / observation."""
    row = _as_map(cutoff, "cutoff")
    for field in ("kickoff_ts", "decision_ts", "as_of_ts", "captured_at", "source_published_at"):
        if field not in row or row.get(field) in (None, ""):
            code = RefuseClass.CUTOFF if field in {"kickoff_ts", "decision_ts"} else RefuseClass.STALE
            _refuse(code, f"cutoff.{field} missing")
    kickoff = parse_utc(row["kickoff_ts"], field="cutoff.kickoff_ts")
    decision = parse_utc(row["decision_ts"], field="cutoff.decision_ts")
    as_of = parse_utc(row["as_of_ts"], field="cutoff.as_of_ts")
    expected = kickoff - timedelta(minutes=DECISION_OFFSET_BEFORE_KICKOFF_MINUTES)
    if decision != expected:
        delta = decision - expected
        _refuse(
            RefuseClass.CUTOFF,
            f"decision_ts {row['decision_ts']} != kickoff−90m ({expected.strftime('%Y-%m-%dT%H:%M:%SZ')}); "
            f"delta_s={delta.total_seconds()}",
        )
    if as_of > kickoff:
        _refuse(RefuseClass.STALE, "as_of_ts after kickoff_ts")


def _check_payload_hashes(payload: Optional[Mapping[str, Any]], manifest: Mapping[str, Any]) -> None:
    if payload is None:
        return
    bits = (_as_map(payload.get("capability"), "capability")).get("bits")
    if not isinstance(bits, list) or "POINT_MARGIN" not in bits:
        _refuse(RefuseClass.CAPABILITY, "POINT_MARGIN capability required")
    if "JOINT_SCORE" in bits:
        _refuse(RefuseClass.CAPABILITY, "JOINT_SCORE unsupported on this path")
    if payload.get("requested_output") not in (None, "POINT_MARGIN_SPREAD"):
        _refuse(
            RefuseClass.CAPABILITY,
            f"unsupported requested_output {payload.get('requested_output')!r}",
        )
    cutoff = payload.get("cutoff")
    if isinstance(cutoff, Mapping):
        validate_cutoff(cutoff)
    recomputed = chain_digest(payload)
    declared = require_sha256_hex(manifest.get("common_digest"), "common_digest")
    if recomputed != declared:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "recomputed chain digest != declared common_digest (content mutation)",
        )
    if recomputed != PINNED_CHAIN_DIGEST:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "recomputed chain digest != accepted #707/#706 pin",
        )
    forecast = _as_map(payload.get("forecast"), "forecast")
    if forecast.get("forecast_id") != PINNED_FORECAST_ID:
        _refuse(RefuseClass.HASH_MUTATED, "forecast_id != pinned accepted identity")
    if payload.get("admitted_capture_id") != PINNED_CAPTURE_ID:
        _refuse(RefuseClass.HASH_MUTATED, "admitted_capture_id != pinned accepted identity")


def _check_numerical(manifest: Mapping[str, Any]) -> None:
    numerical = _as_map(manifest.get("numerical_output"), "numerical_output")
    n = require_int(numerical.get("n"), "numerical_output.n")
    if n != PINNED_N:
        _refuse(RefuseClass.WRONG_COUNT, f"numerical n={n} != {PINNED_N}")
    if numerical.get("game_id") != PINNED_GAME_ID:
        _refuse(
            RefuseClass.WRONG_PROFILE_IDENTITY,
            f"numerical game_id {numerical.get('game_id')!r} != {PINNED_GAME_ID}",
        )
    margin = require_finite(numerical.get("point_margin"), "numerical_output.point_margin")
    line = require_finite(numerical.get("line"), "numerical_output.line")
    price = require_int(numerical.get("price"), "numerical_output.price")
    if margin != PINNED_POINT_MARGIN or line != PINNED_LINE or price != PINNED_PRICE:
        _refuse(
            RefuseClass.WRONG_COUNT,
            "numerical output does not match accepted synthetic fixture",
        )
    require_finite(numerical.get("offense_raw"), "numerical_output.offense_raw")
    require_finite(numerical.get("defense_raw"), "numerical_output.defense_raw")
    require_finite(numerical.get("offense_multiplier"), "numerical_output.offense_multiplier")
    require_finite(numerical.get("defense_multiplier"), "numerical_output.defense_multiplier")
    if numerical.get("offense_raw") != PINNED_OFFENSE_RAW:
        _refuse(RefuseClass.WRONG_COUNT, "offense_raw != pinned synthetic")
    if numerical.get("defense_raw") != PINNED_DEFENSE_RAW:
        _refuse(RefuseClass.WRONG_COUNT, "defense_raw != pinned synthetic")
    if numerical.get("offense_multiplier") != PINNED_OFFENSE_MULT:
        _refuse(RefuseClass.WRONG_COUNT, "offense_multiplier != pinned synthetic")
    if numerical.get("defense_multiplier") != PINNED_DEFENSE_MULT:
        _refuse(RefuseClass.WRONG_COUNT, "defense_multiplier != pinned synthetic")


def _check_controls(manifest: Mapping[str, Any]) -> None:
    positive = _as_map(manifest.get("positive_control"), "positive_control")
    if positive.get("ran") is not True or positive.get("digest_match") is not True:
        _refuse(RefuseClass.INCOMPLETE, "positive_control not executed")
    faults = _as_map(manifest.get("rehashed_faults"), "rehashed_faults")
    if faults.get("ran") is not True or faults.get("refused") is not True:
        _refuse(RefuseClass.INCOMPLETE, "rehashed_faults control not executed")
    if require_int(faults.get("gate_invoked"), "rehashed_faults.gate_invoked") < 1:
        _refuse(
            RefuseClass.INCOMPLETE,
            "rehashed_faults did not invoke the DIRECT gate",
        )
    inst = _as_map(faults.get("instrumentation_control"), "rehashed_faults.instrumentation_control")
    if inst.get("fired") is not True:
        _refuse(
            RefuseClass.INCOMPLETE,
            "rehashed_faults positive instrumentation control did not fire",
        )
    if require_int(faults.get("forbidden_calls"), "rehashed_faults.forbidden_calls") != 0:
        _refuse(
            RefuseClass.FORBIDDEN_CALL,
            "rehashed_faults recorded forbidden calls on refuse",
        )
    spy = _as_map(manifest.get("spy_positive_control"), "spy_positive_control")
    if spy.get("ran") is not True or spy.get("spy_fired") is not True:
        _refuse(RefuseClass.SPY, "spy-positive control not executed or did not fire")
    forbidden = require_int(
        manifest.get("forbidden_calls_on_refusal"), "forbidden_calls_on_refusal"
    )
    if forbidden != 0:
        _refuse(
            RefuseClass.FORBIDDEN_CALL,
            f"forbidden_calls_on_refusal={forbidden} (must be 0 on refused controls)",
        )


def _check_typed_references(manifest: Mapping[str, Any]) -> None:
    refs = manifest.get("typed_references")
    if not isinstance(refs, list) or not refs:
        _refuse(RefuseClass.INCOMPLETE, "typed_references missing")
    kinds_seen = set()
    for idx, raw in enumerate(refs):
        row = _as_map(raw, f"typed_references[{idx}]")
        kind = require_str(row.get("kind"), f"typed_references[{idx}].kind")
        if kind not in TYPED_REF_KINDS:
            _refuse(RefuseClass.TYPE, f"typed_references[{idx}].kind {kind!r} unsupported")
        require_str(row.get("value"), f"typed_references[{idx}].value")
        kinds_seen.add(kind)
    files = manifest.get("changed_files")
    if not isinstance(files, list) or not files:
        _refuse(RefuseClass.INCOMPLETE, "changed_files missing")
    for idx, raw in enumerate(files):
        row = _as_map(raw, f"changed_files[{idx}]")
        require_str(row.get("path"), f"changed_files[{idx}].path")
        require_sha256_hex(row.get("sha256"), f"changed_files[{idx}].sha256")
        kind = require_str(row.get("ref_kind"), f"changed_files[{idx}].ref_kind")
        if kind != "file_sha256":
            _refuse(
                RefuseClass.TYPE,
                f"changed_files[{idx}].ref_kind must be file_sha256 (not git_commit/receipt_id)",
            )


def _check_outputs(manifest: Mapping[str, Any]) -> None:
    paths = manifest.get("output_paths")
    hashes = manifest.get("output_hashes")
    if not isinstance(paths, list) or not paths:
        _refuse(RefuseClass.INCOMPLETE, "output_paths missing")
    if not isinstance(hashes, Mapping) or not hashes:
        _refuse(RefuseClass.INCOMPLETE, "output_hashes missing")
    for path in paths:
        require_str(path, "output_paths[]")
        if path not in hashes:
            _refuse(RefuseClass.INCOMPLETE, f"output_hashes missing {path}")
        require_sha256_hex(hashes[path], f"output_hashes[{path}]")


def _check_command_clock(manifest: Mapping[str, Any], *, stage: str) -> None:
    require_str(manifest.get("command"), "command")
    require_str(manifest.get("cwd"), "cwd")
    require_str(manifest.get("start_utc"), "start_utc")
    parse_utc(manifest.get("start_utc"), field="start_utc")
    if stage == STAGE_PRE_RECEIPT:
        require_str(manifest.get("end_utc"), "end_utc")
        parse_utc(manifest.get("end_utc"), field="end_utc")
        require_int(manifest.get("exit"), "exit")
        require_sha256_hex(manifest.get("log_hash"), "log_hash")
        start = parse_utc(manifest.get("start_utc"), field="start_utc")
        end = parse_utc(manifest.get("end_utc"), field="end_utc")
        if end < start:
            _refuse(RefuseClass.STALE, "end_utc before start_utc")


def _require_verification(verification: Optional[VerificationContext]) -> VerificationContext:
    if verification is None:
        _refuse(
            RefuseClass.MISSING_CONTEXT,
            "missing verification context at DIRECT gate — "
            "self-consistent declarations are not source proof",
        )
    return verification


def _bind_source_revision(
    manifest: Mapping[str, Any],
    verification: VerificationContext,
) -> None:
    if not is_git_commit_sha(verification.git_head):
        _refuse(RefuseClass.TYPE, "verification git_head is not a 40-hex git commit")
    if verification.source_revision != verification.git_head:
        _refuse(
            RefuseClass.STALE,
            "verification source_revision != actual git_head",
        )
    if verification.git_base != BASE_DEPLOY_VERCEL:
        _refuse(RefuseClass.STALE, "verification git_base is not pinned deploy-vercel")
    base = _check_typed_git(manifest.get("base"), "base")
    head = _check_typed_git(manifest.get("head"), "head")
    if base != BASE_DEPLOY_VERCEL:
        _refuse(
            RefuseClass.STALE,
            f"base {base} != pinned deploy-vercel {BASE_DEPLOY_VERCEL}",
        )
    if head != verification.git_head:
        _refuse(
            RefuseClass.STALE,
            f"head {head} != actual git_head {verification.git_head} "
            "(stale or unbound revision)",
        )


def _bind_canonical_hashes(
    manifest: Mapping[str, Any],
    verification: VerificationContext,
    chain_payload: Optional[Mapping[str, Any]],
) -> None:
    declared_input = require_sha256_hex(manifest.get("input_hash"), "input_hash")
    declared_history = require_sha256_hex(manifest.get("history_hash"), "history_hash")
    declared_config = require_sha256_hex(manifest.get("config_hash"), "config_hash")
    declared_code = require_sha256_hex(manifest.get("code_hash"), "code_hash")
    if declared_input != verification.actual_input_hash:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "input_hash != independently recomputed actual input bytes",
        )
    if declared_history != verification.actual_history_hash:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "history_hash != independently recomputed history binding",
        )
    if declared_config != verification.actual_config_hash:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "config_hash != independently recomputed config binding",
        )
    if declared_code != verification.actual_code_hash:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "code_hash != independently recomputed on-disk code bytes",
        )
    if chain_payload is None:
        _refuse(
            RefuseClass.MISSING_CONTEXT,
            "missing actual chain payload — cannot bind input bytes",
        )
    payload_hash = sha256_hex(canonical_json(dict(chain_payload)).encode("utf-8"))
    if payload_hash != verification.actual_input_hash:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "supplied chain payload is not the independently supplied actual input",
        )


def _bind_command_exit(
    manifest: Mapping[str, Any],
    verification: VerificationContext,
    *,
    stage: str,
) -> None:
    command = require_str(manifest.get("command"), "command")
    if command != EXPECTED_COMMAND:
        _refuse(
            RefuseClass.COMMAND,
            f"command {command!r} != expected {EXPECTED_COMMAND!r}",
        )
    if verification.actual_command != EXPECTED_COMMAND:
        _refuse(
            RefuseClass.COMMAND,
            f"actual command {verification.actual_command!r} != expected",
        )
    if command != verification.actual_command:
        _refuse(RefuseClass.COMMAND, "declared command != actual command")
    cwd = require_str(manifest.get("cwd"), "cwd")
    if cwd != verification.actual_cwd:
        _refuse(
            RefuseClass.STALE,
            f"cwd {cwd!r} != actual runtime cwd {verification.actual_cwd!r}",
        )
    if stage != STAGE_PRE_RECEIPT:
        return
    if verification.actual_exit is None:
        _refuse(
            RefuseClass.MISSING_CONTEXT,
            "verification context missing actual_exit",
        )
    if verification.actual_exit != 0:
        _refuse(
            RefuseClass.EXIT,
            f"actual exit {verification.actual_exit} is not successful",
        )
    exit_code = require_int(manifest.get("exit"), "exit")
    if exit_code != 0:
        _refuse(RefuseClass.EXIT, f"exit {exit_code} is not successful")
    if exit_code != verification.actual_exit:
        _refuse(RefuseClass.EXIT, "declared exit != actual exit")


def _recompute_output_log(
    manifest: Mapping[str, Any],
    verification: VerificationContext,
) -> None:
    if verification.log_bytes is None:
        _refuse(
            RefuseClass.MISSING_CONTEXT,
            "verification context missing log bytes",
        )
    recomputed_log = sha256_hex(verification.log_bytes)
    declared_log = require_sha256_hex(manifest.get("log_hash"), "log_hash")
    if recomputed_log != declared_log:
        _refuse(
            RefuseClass.HASH_MUTATED,
            "recomputed log bytes != declared log_hash",
        )
    if verification.output_bytes is None:
        _refuse(
            RefuseClass.MISSING_CONTEXT,
            "verification context missing output bytes",
        )
    hashes = manifest.get("output_hashes")
    paths = manifest.get("output_paths")
    if not isinstance(paths, list) or not isinstance(hashes, Mapping):
        return
    for path in paths:
        require_str(path, "output_paths[]")
        if path not in verification.output_bytes:
            _refuse(
                RefuseClass.MISSING_CONTEXT,
                f"verification context missing output bytes for {path}",
            )
        recomputed = sha256_hex(verification.output_bytes[path])
        declared = require_sha256_hex(hashes.get(path), f"output_hashes[{path}]")
        if recomputed != declared:
            _refuse(
                RefuseClass.HASH_MUTATED,
                f"recomputed output bytes != declared for {path}",
            )


def _check_ready_flag(manifest: Mapping[str, Any]) -> None:
    flag = manifest.get("ready_for_review")
    if flag is True:
        _refuse(
            RefuseClass.READY_FOR_REVIEW,
            "READY_FOR_REVIEW cannot be self-stamped on this receipt",
        )
    if flag is not False:
        _refuse(RefuseClass.TYPE, "ready_for_review must be boolean false until Chief")


def validate_manifest(
    manifest: Any,
    *,
    stage: str,
    chain_payload: Optional[Mapping[str, Any]] = None,
    verification: Optional[VerificationContext] = None,
) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        _refuse(RefuseClass.TYPE, "manifest must be an object")
    raw = dict(manifest)
    _check_extra(raw)
    if stage == STAGE_PRE_CONSUME:
        _required_present(raw, PRE_CONSUME_REQUIRED, stage=stage)
    elif stage == STAGE_PRE_RECEIPT:
        _required_present(raw, REQUIRED_TOP_LEVEL, stage=stage)
    else:
        _refuse(RefuseClass.TYPE, f"unknown gate stage {stage!r}")
    ctx = _require_verification(verification)
    _check_package_identity(raw)
    if raw.get("profile") != PROFILE:
        from src.services.nfl_ops_v1_evidence.validate_r7 import validate_r7_manifest

        return validate_r7_manifest(
            raw,
            stage=stage,
            chain_payload=chain_payload,
            verification=ctx,
        )
    _check_data_label(raw)
    _check_execution(raw, stage=stage)
    _bind_source_revision(raw, ctx)
    _check_hash_bindings(raw)
    _bind_canonical_hashes(raw, ctx, chain_payload)
    _check_identities(raw)
    _check_cohort(raw)
    _check_labels(raw)
    _check_trace(raw, stage=stage)
    _check_channel(chain_payload, raw)
    _check_payload_hashes(chain_payload, raw)
    validate_worker_handoff(raw.get("worker_handoff"))
    _check_ready_flag(raw)
    _check_command_clock(raw, stage=stage)
    _bind_command_exit(raw, ctx, stage=stage)
    _check_controls(raw)
    require_int(raw.get("review_revision"), "review_revision")
    if not isinstance(raw.get("limitations"), list) or not raw.get("limitations"):
        _refuse(RefuseClass.INCOMPLETE, "limitations missing")
    exposure = _as_map(raw.get("exposure"), "exposure")
    for key in (
        "subscriber_consumable",
        "betting_consumable",
        "production_consumable",
        "env_bypass_honored",
        "cacheable",
    ):
        if exposure.get(key) is not False:
            _refuse(RefuseClass.CONSUMER, f"exposure.{key} must be false")
    proof = _as_map(raw.get("immutable_input_proof"), "immutable_input_proof")
    if proof.get("dest_is_temp") is not True:
        _refuse(RefuseClass.WRITE_TAMPER, "immutable-input proof: dest must be temp-only")
    if proof.get("pinned_originals_unwritten") is not True:
        _refuse(RefuseClass.WRITE_TAMPER, "pinned originals were written or unproven")
    if stage == STAGE_PRE_RECEIPT:
        _check_typed_references(raw)
        _check_outputs(raw)
        _recompute_output_log(raw, ctx)
        _check_numerical(raw)
        if not isinstance(raw.get("failures"), list):
            _refuse(RefuseClass.TYPE, "failures must be a list")
    return raw


def numerical_from_consumed(payload: Mapping[str, Any]) -> dict[str, Any]:
    quote = _as_map(payload.get("quote"), "quote")
    forecast = _as_map(payload.get("forecast"), "forecast")
    return {
        "n": PINNED_N,
        "game_id": payload.get("game_id"),
        "point_margin": forecast.get("point_margin"),
        "line": quote.get("line"),
        "price": quote.get("price"),
        "offense_raw": payload.get("offense_raw"),
        "defense_raw": payload.get("defense_raw"),
        "offense_multiplier": payload.get("offense_multiplier"),
        "defense_multiplier": payload.get("defense_multiplier"),
        "admitted_capture_id": payload.get("admitted_capture_id"),
        "forecast_id": forecast.get("forecast_id"),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
