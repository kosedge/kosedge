"""Fail-closed timestamped NFL model forecast emit (Alex paper f1fa86e7).

Library-only. No Odds API. No seal dest writes. CERT_CANDIDATE=0.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from src.services.nfl_model_forecast_emit.schema import (
    CERT_CANDIDATE,
    CLOSE_ANCHOR_RESERVED,
    EMPTY_GRADES,
    EVAL_RECORD_PAPER_SHA8,
    FILE_MODE_READONLY,
    FORBIDDEN_CLOSE_KEYS,
    GAME_ID_FORMAT,
    LABEL,
    MARKET_KEYS,
    PURPOSE,
    RECORD_SHA256_SUFFIX,
    REQUIRED_MARKET_FIELDS,
    REQUIRED_MODEL_FIELDS,
    REQUIRED_PROVENANCE_FIELDS,
    REQUIRED_TOP_LEVEL,
    SCHEMA_VERSION,
    SEAL_BIND_HOOK,
    SEAL_BINDING_STATUS_UNBOUND,
    SEAL_DEST_MARKERS,
    SECRET_KEY_TOKENS,
    SPORT,
    SPREAD_ORIENTATION,
    SPREAD_SIGN_CONVENTION,
    UNSET_TOKENS,
)

_SHA1_40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256_64 = re.compile(r"^[0-9a-f]{64}$")
_GAME_ID_RE = re.compile(
    r"^(?P<season>\d{4})-W(?P<week>\d{2})-(?P<away>[A-Z0-9]{2,4})@(?P<home>[A-Z0-9]{2,4})$"
)


class ForecastIncompleteError(RuntimeError):
    """Inputs incomplete or violate G1–G8. Fail-closed; no artifact."""

    def __init__(self, message: str, *, gap: str = "", reason: str = "") -> None:
        super().__init__(message)
        self.gap = gap
        self.reason = reason or message


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _is_unset(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() in UNSET_TOKENS:
        return True
    return False


def _to_float(value: Any, *, field: str, gap: str) -> float:
    if _is_unset(value):
        raise ForecastIncompleteError(
            f"{field} is UNSET/empty on the real prediction path",
            gap=gap,
            reason="unset_prediction",
        )
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ForecastIncompleteError(
            f"{field} is not a real number: {value!r}",
            gap=gap,
            reason="non_numeric_prediction",
        ) from exc
    if out != out:  # NaN
        raise ForecastIncompleteError(
            f"{field} is NaN",
            gap=gap,
            reason="nan_prediction",
        )
    return out


def canonicalize(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def compute_config_sha256(config: Mapping[str, Any]) -> str:
    return sha256_hex(canonicalize(dict(config)).encode("utf-8"))


def resolve_code_tip_sha(
    provided: Any = None,
    *,
    repo_dir: Optional[Path] = None,
) -> str:
    raw = str(provided or "").strip().lower()
    if raw:
        if not _SHA1_40.match(raw):
            raise ForecastIncompleteError(
                f"code_tip_sha must be 40-hex, got {provided!r}",
                gap="G4",
                reason="code_tip_sha_not_40_hex",
            )
        return raw
    root = repo_dir or Path(__file__).resolve().parents[4]
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip().lower()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ForecastIncompleteError(
            "code_tip_sha unresolved (git rev-parse HEAD failed)",
            gap="G4",
            reason="code_tip_sha_unresolved",
        ) from exc
    if not _SHA1_40.match(out):
        raise ForecastIncompleteError(
            f"code_tip_sha from git is not 40-hex: {out!r}",
            gap="G4",
            reason="code_tip_sha_not_40_hex",
        )
    return out


def parse_game_id(game_id: str) -> Dict[str, Any]:
    match = _GAME_ID_RE.match(game_id)
    if not match:
        raise ForecastIncompleteError(
            f"game_id must match {GAME_ID_FORMAT}, got {game_id!r}",
            gap="G1",
            reason="game_id_orientation",
        )
    return {
        "season": int(match.group("season")),
        "week": int(match.group("week")),
        "away_team": match.group("away"),
        "home_team": match.group("home"),
    }


def _looks_secret_key(key: str) -> bool:
    lowered = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(token in lowered for token in SECRET_KEY_TOKENS)


def _walk_forbidden_close(payload: Any, *, trail: str = "") -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            name = str(key)
            path = f"{trail}.{name}" if trail else name
            if name in FORBIDDEN_CLOSE_KEYS and value not in (None, {}, []):
                if name in {"close_anchor", "grades"} and isinstance(value, Mapping):
                    # Nested populated close/grade values are the reject.
                    _walk_forbidden_close(value, trail=path)
                    continue
                raise ForecastIncompleteError(
                    f"emitter must not write close/grade field {path}",
                    gap="G7",
                    reason="close_or_grade_forbidden",
                )
            _walk_forbidden_close(value, trail=path)
    elif isinstance(payload, (list, tuple)):
        for idx, item in enumerate(payload):
            _walk_forbidden_close(item, trail=f"{trail}[{idx}]")


def _assert_not_seal_dest(path: Path) -> None:
    text = str(path.resolve()).replace("\\", "/").lower()
    for marker in SEAL_DEST_MARKERS:
        if marker.lower() in text:
            raise ForecastIncompleteError(
                f"refuse write into seal dest: {path}",
                gap="G6",
                reason="seal_dest_refused",
            )


def _validate_fingerprints(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, Mapping) or not raw:
        raise ForecastIncompleteError(
            "input_provenance.fingerprints required and non-empty",
            gap="G2",
            reason="provenance_missing",
        )
    out: Dict[str, str] = {}
    for key, value in raw.items():
        name = str(key).strip()
        if not name:
            raise ForecastIncompleteError(
                "fingerprint key is empty",
                gap="G2",
                reason="provenance_empty_key",
            )
        if _looks_secret_key(name):
            raise ForecastIncompleteError(
                f"fingerprint key looks like a secret: {name}",
                gap="G2",
                reason="secret_in_provenance",
            )
        if _is_unset(value):
            raise ForecastIncompleteError(
                f"fingerprint {name} is UNSET",
                gap="G2",
                reason="provenance_unset",
            )
        text = str(value).strip().lower()
        if text.startswith("sha256:"):
            text = text[7:]
        if not _SHA256_64.match(text):
            raise ForecastIncompleteError(
                f"fingerprint {name} must be sha256 hex, got {value!r}",
                gap="G2",
                reason="provenance_not_sha256",
            )
        out[name] = text
    return out


def _normalize_market(
    name: str,
    raw: Any,
    *,
    default_source: str,
) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ForecastIncompleteError(
            f"markets.{name} must be an object",
            gap="G3",
            reason="market_not_object",
        )
    pred = raw.get("prediction", raw.get("value"))
    ref = raw.get("ref_line", pred)
    if "ref_line_source" in raw:
        source = str(raw.get("ref_line_source") or "").strip()
    else:
        source = str(default_source or "").strip()
    if not source or source in UNSET_TOKENS:
        raise ForecastIncompleteError(
            f"markets.{name}.ref_line_source required",
            gap="G3",
            reason="ref_line_source_missing",
        )
    pred_f = _to_float(pred, field=f"markets.{name}.prediction", gap="G8")
    ref_f = _to_float(ref, field=f"markets.{name}.ref_line", gap="G3")
    if pred_f != ref_f:
        raise ForecastIncompleteError(
            f"markets.{name} prediction {pred_f} != ref_line {ref_f}",
            gap="G3",
            reason="ref_line_mismatch",
        )
    out: Dict[str, Any] = {
        "prediction": pred_f,
        "ref_line": ref_f,
        "ref_line_source": source,
    }
    if name == "spread":
        orientation = str(raw.get("orientation") or SPREAD_ORIENTATION).strip().lower()
        sign = str(raw.get("sign_convention") or SPREAD_SIGN_CONVENTION).strip()
        if orientation != SPREAD_ORIENTATION:
            raise ForecastIncompleteError(
                f"spread orientation must be {SPREAD_ORIENTATION!r}, got {orientation!r}",
                gap="G1",
                reason="spread_orientation",
            )
        if sign != SPREAD_SIGN_CONVENTION:
            raise ForecastIncompleteError(
                f"spread sign_convention must be {SPREAD_SIGN_CONVENTION!r}, got {sign!r}",
                gap="G1",
                reason="spread_sign_convention",
            )
        out["orientation"] = SPREAD_ORIENTATION
        out["sign_convention"] = SPREAD_SIGN_CONVENTION
    elif name == "total":
        out["orientation"] = "game"
    elif name == "moneyline":
        out["orientation"] = "home"
        if "home_ml" in raw and not _is_unset(raw.get("home_ml")):
            out["home_ml"] = _to_float(raw.get("home_ml"), field="markets.moneyline.home_ml", gap="G8")
        if "away_ml" in raw and not _is_unset(raw.get("away_ml")):
            out["away_ml"] = _to_float(raw.get("away_ml"), field="markets.moneyline.away_ml", gap="G8")
        if "away_win_prob" in raw and not _is_unset(raw.get("away_win_prob")):
            out["away_win_prob"] = _to_float(
                raw.get("away_win_prob"),
                field="markets.moneyline.away_win_prob",
                gap="G8",
            )
        if pred_f < 0.0 or pred_f > 1.0:
            raise ForecastIncompleteError(
                "markets.moneyline.prediction must be a home_win_prob in [0, 1]",
                gap="G8",
                reason="ml_prob_range",
            )
    for key in REQUIRED_MARKET_FIELDS:
        if key not in out:
            raise ForecastIncompleteError(
                f"markets.{name}.{key} missing after normalize",
                gap="G3",
                reason="market_incomplete",
            )
    return out


def emit_model_forecast(
    inputs: Mapping[str, Any],
    *,
    dest_path: Optional[os.PathLike[str] | str] = None,
    now_utc: Any = None,
    repo_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build (and optionally persist) a G1–G8 forecast artifact.

    Returns the artifact dict. When dest_path is set, also writes 0444 JSON
    plus a ``.record_sha256`` sidecar and refuses overwrite / seal dests.
    """
    if not isinstance(inputs, Mapping):
        raise ForecastIncompleteError("inputs must be a mapping", gap="G8", reason="inputs_type")
    _walk_forbidden_close(inputs)

    game_id = str(inputs.get("game_id") or "").strip().upper()
    if not game_id:
        raise ForecastIncompleteError("game_id required", gap="G1", reason="game_id_missing")
    parsed = parse_game_id(game_id)
    home = str(inputs.get("home_team") or parsed["home_team"]).strip().upper()
    away = str(inputs.get("away_team") or parsed["away_team"]).strip().upper()
    if not home or not away:
        raise ForecastIncompleteError(
            "home_team and away_team required",
            gap="G1",
            reason="home_away_missing",
        )
    if home == away:
        raise ForecastIncompleteError(
            "home_team and away_team must differ",
            gap="G1",
            reason="home_away_identical",
        )
    if home != parsed["home_team"] or away != parsed["away_team"]:
        raise ForecastIncompleteError(
            f"game_id {game_id} orientation is {parsed['away_team']}@{parsed['home_team']}, "
            f"got away={away} home={home}",
            gap="G1",
            reason="home_away_mismatch",
        )

    kickoff = parse_utc(inputs.get("kickoff_utc"))
    if kickoff is None:
        raise ForecastIncompleteError(
            "kickoff_utc required (G1)",
            gap="G1",
            reason="kickoff_missing",
        )
    forecast_ts = parse_utc(inputs.get("forecast_ts_utc") or inputs.get("emitted_at_utc") or now_utc)
    if forecast_ts is None:
        forecast_ts = _utc_now()
    lead_seconds = int((kickoff - forecast_ts).total_seconds())
    if lead_seconds <= 0:
        raise ForecastIncompleteError(
            f"forecast must be before kickoff (lead_seconds={lead_seconds})",
            gap="G2",
            reason="not_pre_kickoff",
        )

    latest_input = parse_utc(inputs.get("latest_input_as_of"))
    if latest_input is None:
        raise ForecastIncompleteError(
            "latest_input_as_of required and must be <= forecast_ts_utc (G2)",
            gap="G2",
            reason="latest_input_as_of_missing",
        )
    if latest_input > forecast_ts:
        raise ForecastIncompleteError(
            "latest_input_as_of must be <= forecast_ts_utc",
            gap="G2",
            reason="latest_input_after_forecast",
        )

    model = inputs.get("model")
    if not isinstance(model, Mapping):
        model = {
            "identity": inputs.get("model_identity"),
            "version": inputs.get("model_version") or inputs.get("engine_version"),
        }
    identity = str(model.get("identity") or "").strip()
    version = str(model.get("version") or "").strip()
    if not identity or identity in UNSET_TOKENS:
        raise ForecastIncompleteError("model.identity required", gap="G4", reason="model_identity_missing")
    if not version or version in UNSET_TOKENS:
        raise ForecastIncompleteError("model.version required", gap="G4", reason="model_version_missing")
    for key in REQUIRED_MODEL_FIELDS:
        if key not in ("identity", "version"):
            continue

    raw_markets = inputs.get("markets")
    if not isinstance(raw_markets, Mapping) or not raw_markets:
        raise ForecastIncompleteError("markets required", gap="G8", reason="markets_missing")
    default_source = str(
        inputs.get("ref_line_source")
        or f"{identity}:{version}"
    ).strip()
    markets: Dict[str, Any] = {}
    for name in MARKET_KEYS:
        if name not in raw_markets:
            continue
        markets[name] = _normalize_market(
            name,
            raw_markets[name],
            default_source=default_source,
        )
    if not markets:
        raise ForecastIncompleteError(
            "at least one of spread/total/moneyline required",
            gap="G8",
            reason="no_markets",
        )

    provenance = inputs.get("input_provenance")
    if not isinstance(provenance, Mapping):
        provenance = {"fingerprints": inputs.get("fingerprints") or {}}
    fingerprints = _validate_fingerprints(provenance.get("fingerprints"))
    for key in REQUIRED_PROVENANCE_FIELDS:
        if key != "fingerprints":
            continue

    extra_prov = {
        k: v
        for k, v in provenance.items()
        if k != "fingerprints" and not _looks_secret_key(str(k))
    }

    code_tip_sha = resolve_code_tip_sha(inputs.get("code_tip_sha"), repo_dir=repo_dir)
    config = dict(inputs.get("config") or {})
    config.setdefault("schema_version", SCHEMA_VERSION)
    config.setdefault("model_identity", identity)
    config.setdefault("model_version", version)
    config.setdefault("eval_record_paper_sha8", EVAL_RECORD_PAPER_SHA8)
    config_sha = str(inputs.get("config_sha256") or "").strip().lower()
    if config_sha.startswith("sha256:"):
        config_sha = config_sha[7:]
    if not config_sha:
        config_sha = compute_config_sha256(config)
    if not _SHA256_64.match(config_sha):
        raise ForecastIncompleteError(
            f"config_sha256 must be 64-hex, got {inputs.get('config_sha256')!r}",
            gap="G4",
            reason="config_sha256_invalid",
        )

    forecast_ts_s = format_utc(forecast_ts)
    artifact: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "purpose": PURPOSE,
        "sport": SPORT,
        "eval_record_paper_sha8": EVAL_RECORD_PAPER_SHA8,
        "forecast_ts_utc": forecast_ts_s,
        "emitted_at_utc": forecast_ts_s,
        "game_id": game_id,
        "season": parsed["season"],
        "week": parsed["week"],
        "home_team": home,
        "away_team": away,
        "kickoff_utc": format_utc(kickoff),
        "lead_seconds": lead_seconds,
        "pre_kickoff": True,
        "latest_input_as_of": format_utc(latest_input),
        "code_tip_sha": code_tip_sha,
        "config_sha256": config_sha,
        "model": {"identity": identity, "version": version},
        "orientation": {
            "game_id_format": GAME_ID_FORMAT,
            "spread": SPREAD_ORIENTATION,
            "spread_sign_convention": SPREAD_SIGN_CONVENTION,
            "total": "game",
            "moneyline": "home",
        },
        "markets": markets,
        "input_provenance": {
            "fingerprints": fingerprints,
            **extra_prov,
        },
        "grades": dict(EMPTY_GRADES),
        "close_anchor": dict(CLOSE_ANCHOR_RESERVED),
        "seal_binding": {
            "status": SEAL_BINDING_STATUS_UNBOUND,
            "cert_candidate": CERT_CANDIDATE,
            "hook": SEAL_BIND_HOOK,
            "note": (
                "Later bind a prospective Odds seal by matching game_id + "
                "forecast_ts_utc + record_sha256. Emitter does not write close "
                "or seal dests. F2 PHI@WAS / #641 tip 385767a2 stay untouched."
            ),
        },
    }
    for key in REQUIRED_TOP_LEVEL:
        if key not in artifact:
            raise ForecastIncompleteError(
                f"internal: missing {key}",
                gap="G5",
                reason="schema_hole",
            )
    if dest_path is not None:
        write_forecast_artifact(artifact, dest_path)
    return artifact


def write_forecast_artifact(
    artifact: Mapping[str, Any],
    dest_path: os.PathLike[str] | str,
) -> Dict[str, str]:
    """Write canonical JSON at 0444 plus record_sha256 sidecar. Refuse overwrite."""
    path = Path(dest_path)
    _assert_not_seal_dest(path)
    sidecar = path.with_name(path.name + RECORD_SHA256_SUFFIX)
    _assert_not_seal_dest(sidecar)
    if path.exists():
        raise ForecastIncompleteError(
            f"refuse overwrite: {path}",
            gap="G6",
            reason="refuse_overwrite",
        )
    if sidecar.exists():
        raise ForecastIncompleteError(
            f"refuse overwrite sidecar: {sidecar}",
            gap="G6",
            reason="refuse_overwrite_sidecar",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = (canonicalize(artifact) + "\n").encode("utf-8")
    # G5: label + cert_candidate must exist in the written bytes.
    if b'"cert_candidate":0' not in blob and b'"cert_candidate": 0' not in blob:
        raise ForecastIncompleteError(
            "cert_candidate=0 missing from artifact bytes",
            gap="G5",
            reason="cert_candidate_missing_from_bytes",
        )
    if f'"label":"{LABEL}"'.encode("utf-8") not in blob:
        raise ForecastIncompleteError(
            "label missing from artifact bytes",
            gap="G5",
            reason="label_missing_from_bytes",
        )
    digest = sha256_hex(blob)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(blob)
    os.chmod(tmp, FILE_MODE_READONLY)
    tmp.replace(path)
    # replace may drop mode on some FS; re-assert 0444.
    os.chmod(path, FILE_MODE_READONLY)
    side_blob = (digest + "\n").encode("utf-8")
    side_tmp = sidecar.with_name(sidecar.name + ".tmp")
    side_tmp.write_bytes(side_blob)
    os.chmod(side_tmp, FILE_MODE_READONLY)
    side_tmp.replace(sidecar)
    os.chmod(sidecar, FILE_MODE_READONLY)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != FILE_MODE_READONLY:
        raise ForecastIncompleteError(
            f"artifact mode {oct(mode)} is not 0444",
            gap="G6",
            reason="mode_not_0444",
        )
    return {
        "path": str(path),
        "sidecar": str(sidecar),
        "record_sha256": digest,
    }


def assert_no_odds_import(module_source: str) -> None:
    lowered = module_source.lower()
    if "odds_api" in lowered or "the-odds-api" in lowered:
        raise ForecastIncompleteError(
            "forecast emit must not import Odds API",
            gap="G8",
            reason="odds_api_forbidden",
        )
