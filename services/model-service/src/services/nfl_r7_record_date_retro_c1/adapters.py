"""Fictional SYNTHETIC adapters for the shared RETRO_C1 engine. CERT=0.

Labels live in a vault that denies reads until every forecast is sealed.
Index values and packet stamps are adapter-supplied, not invented by the engine.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from src.services.nfl_r7_correctness_v1.franchise import key_packet_and_history_for_q2
from src.services.nfl_r7_correctness_v1.packets import DEFAULT_INDEX_VALUES
from src.services.nfl_r7_correctness_v1.produce import consume_effective_config
from src.services.nfl_r7_record_date_retro_c1.fixtures import (
    SYNTHETIC_ARCHIVE,
    SYNTHETIC_LABELS,
    synthetic_cohort,
    synthetic_history,
    synthetic_schedule,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse
from src.services.nfl_t5208u.caller import call_r6_point_margin

LABEL_KEYS = frozenset(
    {
        "y_margin",
        "y_margin_held",
        "y_source",
        "abs_c_minus_y",
        "signed_c_minus_y",
        "home_score",
        "away_score",
        "actual_margin",
        "actual_total",
    }
)


def strip_labels(row: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in dict(row).items() if k not in LABEL_KEYS}


def synthetic_packet_stamps(kickoff_utc: str) -> dict[str, str]:
    """Visibly SYNTHETIC cell stamps for the fictional adapter only."""
    text = kickoff_utc[:-1] + "+00:00" if kickoff_utc.endswith("Z") else kickoff_utc
    ko = datetime.fromisoformat(text).astimezone(timezone.utc)
    return {
        "available_at": (ko - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observed_at": (ko - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stamp_kind": "SYNTHETIC_ADAPTER_NOT_ACTUAL_PUBLICATION",
    }


class LabelVault:
    """Outcome labels. First read allowed only after forecasts are sealed."""

    def __init__(self, labels: Mapping[str, float]) -> None:
        self._labels = {str(k): float(v) for k, v in labels.items()}
        self._open = False
        self.reads = 0

    def allow_after_seal(self) -> None:
        self._open = True

    def read(self, ids: list[str]) -> dict[str, float]:
        if not self._open:
            raise RetroRefuse("labels denied before forecast seal")
        self.reads += 1
        missing = [gid for gid in ids if gid not in self._labels]
        if missing:
            raise RetroRefuse(f"outcome identity mismatch / missing labels {missing}")
        extra = [gid for gid in self._labels if gid not in set(ids)]
        if extra:
            raise RetroRefuse(f"outcome identity extra labels {extra}")
        return {gid: self._labels[gid] for gid in ids}


def fictional_targets() -> list[dict[str, Any]]:
    out = []
    for row in synthetic_cohort():
        clean = strip_labels(row)
        clean["index_values"] = dict(DEFAULT_INDEX_VALUES)
        clean["stamps"] = synthetic_packet_stamps(str(clean["nominal_kickoff_utc"]))
        out.append(clean)
    return out


def fictional_model(packet: Mapping[str, Any], history: list[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    _keyed_packet, keyed_history = key_packet_and_history_for_q2(packet, history)
    return call_r6_point_margin(packet, keyed_history, mode="SYNTHETIC", effective_config=cfg)


def build_synthetic_readers(*, labels: Mapping[str, float] | None = None) -> dict[str, Any]:
    vault = LabelVault(labels if labels is not None else SYNTHETIC_LABELS)
    return {
        "channel": "SYNTHETIC",
        "targets": fictional_targets,
        "schedule": synthetic_schedule,
        "history": synthetic_history,
        "outcomes": vault,
        "archive": lambda: dict(SYNTHETIC_ARCHIVE),
        "model": fictional_model,
        "config": consume_effective_config,
        "index_source": "SYNTHETIC_ADAPTER_DEFAULT_INDEX",
        "stamp_source": "SYNTHETIC_ADAPTER_NOT_ACTUAL_PUBLICATION",
    }


EngineReaders = dict[str, Any]
ModelFn = Callable[[Mapping[str, Any], list[Mapping[str, Any]], Mapping[str, Any]], dict[str, Any]]
