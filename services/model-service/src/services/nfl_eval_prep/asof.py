"""LC-1: per-feature as-of proofs. Proof is ``as_of < kickoff_utc``.

A failing row is EXCLUDED with its reason. Unprovable timestamps are not
available (fail closed). Same spirit as ``cfb_warehouse.leakage``; this module
is the NFL eval-prep contract and does not open a warehouse.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence


PROOF_RULE = "as_of_strictly_before_kickoff_utc"


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


def _reason_for(proof: AsOfProof) -> Optional[str]:
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
        )
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


def proofs_from_feature_row(
    row: Mapping[str, Any],
    *,
    feature_names: Sequence[str],
    kickoff_utc: str,
    as_of_key: str = "as_of",
    source_key: str = "source",
) -> list[AsOfProof]:
    """One proof per named feature on a row. Missing as_of stays unprovable."""
    as_of = str(row.get(as_of_key) or "")
    source = str(row.get(source_key) or "")
    game_id = str(row.get("game_id") or "")
    return [
        AsOfProof(
            game_id=game_id,
            feature_name=name,
            as_of=as_of,
            kickoff_utc=kickoff_utc,
            source=source,
        )
        for name in feature_names
        if name in row
    ]
