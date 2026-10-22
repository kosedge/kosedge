"""LC-1: per-feature as-of proofs. Proof is ``as_of < kickoff_utc``.

A failing row is EXCLUDED with its reason. Unprovable timestamps are not
available (fail closed). Same spirit as ``cfb_warehouse.leakage``; this module
is the NFL eval-prep contract and does not open a warehouse.

C-6: as-of values are **self-declared**. This module does not verify them
against an external clock or a source capture time. An archived source must
carry a snapshot id or sha (``archive:snapshot:<id>`` or ``archive:sha256:<hex>``),
not a free-form ``archive:<name>``. Whole-row as-of fallback is forbidden.
Close, result, and score columns are not features.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence


PROOF_RULE = "as_of_strictly_before_kickoff_utc"
ASOF_IS_SELF_DECLARED = True
# C-6: snapshot id or sha only. Free-form archive:<name> is refused.
ARCHIVED_SOURCE_RE = re.compile(
    r"^archive:(?:sha256:[0-9a-fA-F]{64}|snapshot:[A-Za-z0-9._-]{8,})$"
)

# Never accepted as rebuild features (labels / closes / grades / results).
FORBIDDEN_FEATURE_COLUMNS = frozenset(
    {
        "home_score",
        "away_score",
        "home_team_score",
        "away_team_score",
        "final_total",
        "final_total_points",
        "home_team_won",
        "spread_line",
        "total_line",
        "market_spread",
        "market_total",
        "market_spread_home",
        "market_total_home",
        "close",
        "close_spread",
        "close_total",
        "closing_spread",
        "closing_total",
        "actual_spread",
        "actual_total",
        "actual_spread_home",
        "closes",
        "result",
    }
)
FORBIDDEN_FEATURE_PREFIXES = ("close", "final_", "grade")


def parse_utc(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
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
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class AsOfProof:
    game_id: str
    feature_name: str
    as_of: str
    kickoff_utc: str
    source: str
    cutoff: Optional[str] = None
    asof_self_declared: bool = True

    def as_of_dt(self) -> Optional[datetime]:
        return parse_utc(self.as_of)

    def kickoff_dt(self) -> Optional[datetime]:
        return parse_utc(self.kickoff_utc)

    def cutoff_dt(self) -> Optional[datetime]:
        return parse_utc(self.cutoff) if self.cutoff else self.kickoff_dt()


@dataclass(frozen=True)
class AsOfViolation:
    game_id: str
    feature_name: str
    reason: str
    as_of: Optional[str] = None
    kickoff_utc: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AsOfValidationResult:
    kept: list[AsOfProof] = field(default_factory=list)
    excluded: list[AsOfViolation] = field(default_factory=list)

    @property
    def kept_n(self) -> int:
        return len(self.kept)

    @property
    def excluded_n(self) -> int:
        return len(self.excluded)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": PROOF_RULE,
            "kept": [asdict(p) for p in self.kept],
            "excluded": [v.to_dict() for v in self.excluded],
            "kept_n": self.kept_n,
            "excluded_n": self.excluded_n,
        }


def named_archived_source(source: str) -> Optional[str]:
    """Return None if ``source`` carries an archive snapshot id or sha."""
    text = str(source or "").strip()
    if not ARCHIVED_SOURCE_RE.fullmatch(text):
        return "source_not_archive_snapshot_or_sha"
    return None


def is_forbidden_feature_column(name: str) -> bool:
    """C-6: exact denylist plus close* / final_* / grade* prefixes."""
    token = str(name or "")
    if token in FORBIDDEN_FEATURE_COLUMNS:
        return True
    return any(token.startswith(prefix) for prefix in FORBIDDEN_FEATURE_PREFIXES)


def _reason_for(proof: AsOfProof) -> Optional[str]:
    source_reason = named_archived_source(proof.source)
    if source_reason:
        return source_reason
    as_of = proof.as_of_dt()
    cutoff = proof.cutoff_dt()
    if as_of is None:
        return "unprovable_as_of"
    if cutoff is None:
        return "unprovable_kickoff_or_cutoff"
    if as_of >= cutoff:
        return "as_of_not_before_cutoff"
    return None


def validate_asof_proofs(
    proofs: Iterable[AsOfProof | Mapping[str, Any]],
) -> AsOfValidationResult:
    """Check each feature-game proof. Failures are excluded, never repaired."""
    result = AsOfValidationResult()
    for raw in proofs:
        proof = raw if isinstance(raw, AsOfProof) else AsOfProof(
            game_id=str(raw.get("game_id") or ""),
            feature_name=str(raw.get("feature_name") or ""),
            as_of=str(raw.get("as_of") or ""),
            kickoff_utc=str(raw.get("kickoff_utc") or ""),
            source=str(raw.get("source") or ""),
            cutoff=(str(raw["cutoff"]) if raw.get("cutoff") else None),
            asof_self_declared=bool(raw.get("asof_self_declared", True)),
        )
        if is_forbidden_feature_column(proof.feature_name):
            result.excluded.append(
                AsOfViolation(
                    game_id=proof.game_id,
                    feature_name=proof.feature_name,
                    reason="close_or_score_column_refused_as_feature",
                    as_of=proof.as_of or None,
                    kickoff_utc=proof.kickoff_utc or None,
                )
            )
            continue
        if not proof.game_id or not proof.feature_name:
            result.excluded.append(
                AsOfViolation(
                    game_id=proof.game_id,
                    feature_name=proof.feature_name,
                    reason="missing_game_or_feature_id",
                    as_of=proof.as_of or None,
                    kickoff_utc=proof.kickoff_utc or None,
                )
            )
            continue
        reason = _reason_for(proof)
        if reason:
            result.excluded.append(
                AsOfViolation(
                    game_id=proof.game_id,
                    feature_name=proof.feature_name,
                    reason=reason,
                    as_of=proof.as_of or None,
                    kickoff_utc=proof.kickoff_utc or None,
                )
            )
            continue
        result.kept.append(proof)
    return result


def forbidden_feature_columns_present(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(key for key in row if is_forbidden_feature_column(str(key))))


def proofs_from_feature_row(
    row: Mapping[str, Any],
    *,
    feature_names: Sequence[str],
    kickoff_utc: str,
    source_key: str = "source",
    allow_row_as_of: bool = False,
) -> list[AsOfProof]:
    """One proof per named feature. Per-feature ``{name}_as_of`` is required.

    Whole-row ``as_of`` is never copied onto features (C-6). ``allow_row_as_of``
    exists only to fail closed.
    """
    if allow_row_as_of:
        raise ValueError("C-6: whole-row as-of fallback is forbidden")
    source = str(row.get(source_key) or "")
    game_id = str(row.get("game_id") or "")
    proofs: list[AsOfProof] = []
    for name in feature_names:
        if name not in row:
            continue
        if is_forbidden_feature_column(name):
            continue
        as_of = str(row.get(f"{name}_as_of") or "")
        feat_source = str(row.get(f"{name}_source") or source)
        proofs.append(
            AsOfProof(
                game_id=game_id,
                feature_name=name,
                as_of=as_of,
                kickoff_utc=kickoff_utc,
                source=feat_source,
                asof_self_declared=True,
            )
        )
    return proofs
