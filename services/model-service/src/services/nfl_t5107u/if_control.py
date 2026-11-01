"""IF control arm — archived pin vs newly reconstructed, never silent drop.

Pin lineage (G1/G3):
- IF tip 6ca03716 / simulator 52d9e909 / framework a0051cc4
- Consume pattern: score_t4910u.py @ 19c6a4607, score_if_w7w17.py @ 8155fd194

2020–23 REG has no archived IF mus @ 6ca03716 in-repo. Reconstruction
requires a complete DERIVED_PREGAME packet (REQUIRED_FIELDS) plus the
frozen IF tree. Missing vintage → block only the IF-dependent scoring
leg and name the exact field/artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
IF_TIP_PREFIX = "6ca03716"
IF_SIMULATOR = "52d9e909"
IF_FRAMEWORK = "a0051cc4"
IF_ASOF = "cf514078"
IF_EFFICIENCY_CONTRACT = "b41f4b43"
IF_FORECAST_LABEL = "independent_fair"

LABEL_ARCHIVED = "ARCHIVED_IF_6ca03716"
LABEL_RECONSTRUCTED = "RECONSTRUCTED_IF_6ca03716"
LABEL_BLOCKED = "IF_LEG_BLOCKED"

REQUIRED_FIELDS = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)

# Exact artifacts that block 2020–23 IF reconstruction on this box.
KNOWN_MISSING_ARTIFACTS = (
    {
        "artifact": "RECON_MATRIX_2020_2023_REG",
        "detail": "only 2017 W7–W17 RECON_MATRIX exists (b56be146 / 7be71acff)",
    },
    {
        "artifact": "b41f4b43_hist_inputs",
        "detail": "IF hist inputs reconstruction MISSING (t4873u / paper §2)",
    },
    {
        "artifact": "if_tree_6ca03716",
        "detail": "frozen IF checkout 6ca03716fe52930332d5ffba302c312a651980cc not mounted",
    },
    {
        "artifact": "archived_IF_mus_2020_2023",
        "detail": "no in-repo IF mus @ 6ca03716 for 2020–23 REG (2017 only)",
    },
)


class IFRefuse(ValueError):
    """Fail-closed IF control (never invent mus, never silent drop)."""


@dataclass
class IFResolution:
    game_id: str
    status: str  # archived | reconstructed | blocked
    label: str
    margin_mu: float | None
    source: str
    missing_fields: list[str] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    parameter_status: str = "original_frozen"

    def as_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "if_status": self.status,
            "if_label": self.label,
            "if_margin_mu": self.margin_mu,
            "if_source": self.source,
            "if_tip": IF_TIP,
            "if_simulator": IF_SIMULATOR,
            "if_framework": IF_FRAMEWORK,
            "missing_fields": list(self.missing_fields),
            "missing_artifacts": list(self.missing_artifacts),
            "parameter_status": self.parameter_status,
            "notes": list(self.notes),
        }


def _tip_ok(raw: Any) -> bool:
    text = str(raw or "").strip().lower()
    return text.startswith(IF_TIP_PREFIX) or text == IF_TIP


def missing_required_fields(packet: Mapping[str, Any] | None) -> list[str]:
    if not packet:
        return list(REQUIRED_FIELDS)
    missing: list[str] = []
    for name in REQUIRED_FIELDS:
        cell = packet.get(name)
        if isinstance(cell, Mapping):
            status = str(cell.get("status") or "")
            value = cell.get("reconstructed_value", cell.get("value"))
            if status != "DERIVED_PREGAME" or value in (None, ""):
                missing.append(name)
        elif cell in (None, ""):
            missing.append(name)
    return missing


def resolve_if_margin(
    game_id: str,
    *,
    archived: Mapping[str, Any] | None = None,
    recon_packet: Mapping[str, Any] | None = None,
    reconstructed_margin_mu: float | None = None,
    if_tree_present: bool = False,
    allow_silent_drop: bool = False,
) -> IFResolution:
    """Resolve IF margin. Archived pin wins; else reconstructed; else block.

    ``allow_silent_drop`` is accepted only so tests can prove it is refused.
    """
    if allow_silent_drop:
        raise IFRefuse("G3 forbids silent IF drop; IF arm must remain labeled")

    if archived:
        tip = archived.get("if_tip") or archived.get("tip")
        label = str(archived.get("if_forecast_label") or archived.get("forecast_label") or "")
        mu = archived.get("if_margin_mu", archived.get("margin_mu"))
        if _tip_ok(tip) and label in {"", IF_FORECAST_LABEL, LABEL_ARCHIVED} and mu not in (None, ""):
            return IFResolution(
                game_id=game_id,
                status="archived",
                label=LABEL_ARCHIVED,
                margin_mu=float(mu),
                source="archived_if_mus",
                notes=["pinned archived IF output; not newly reconstructed"],
            )
        return IFResolution(
            game_id=game_id,
            status="blocked",
            label=LABEL_BLOCKED,
            margin_mu=None,
            source="archived_rejected",
            missing_artifacts=["archived_IF_pin_mismatch"],
            notes=[
                f"archived row failed pin check tip={tip!r} label={label!r}",
            ],
        )

    missing = missing_required_fields(recon_packet)
    artifacts: list[str] = []
    if missing:
        artifacts.append("RECON_MATRIX_2020_2023_REG")
        artifacts.append("b41f4b43_hist_inputs")
    if not if_tree_present:
        artifacts.append("if_tree_6ca03716")
    if reconstructed_margin_mu is None:
        artifacts.append("reconstructed_IF_margin_mu")

    if (
        not missing
        and if_tree_present
        and reconstructed_margin_mu is not None
    ):
        return IFResolution(
            game_id=game_id,
            status="reconstructed",
            label=LABEL_RECONSTRUCTED,
            margin_mu=float(reconstructed_margin_mu),
            source="reconstructed_if_consume",
            parameter_status="rebuilt_inputs_pre_2022_or_asof",
            notes=[
                "newly reconstructed IF forecast; not an archived 6ca03716 output",
                "algorithm pin frozen; inputs labeled reconstructed",
            ],
        )

    notes = [
        "IF control retained as a blocked scoring leg (not dropped).",
        "Challenger mC depends on mIF — challenger blocked for this game.",
    ]
    if missing:
        notes.append("missing DERIVED_PREGAME fields: " + ", ".join(missing))
    if not if_tree_present:
        notes.append("frozen IF tree 6ca03716 is not mounted on this worker")
    return IFResolution(
        game_id=game_id,
        status="blocked",
        label=LABEL_BLOCKED,
        margin_mu=None,
        source="blocked",
        missing_fields=missing,
        missing_artifacts=sorted(set(artifacts)),
        notes=notes,
    )


def retained_if_arm(resolutions: Sequence[IFResolution]) -> dict[str, int]:
    """G3: IF arm is always present. Report archived / reconstructed / blocked counts."""
    counts = {"archived": 0, "reconstructed": 0, "blocked": 0, "total": 0}
    for row in resolutions:
        counts["total"] += 1
        if row.status not in counts:
            raise IFRefuse(f"unknown IF status {row.status!r} — refusing silent drop")
        counts[row.status] += 1
    if counts["total"] == 0:
        raise IFRefuse("IF arm empty — refusing silent drop")
    return counts
