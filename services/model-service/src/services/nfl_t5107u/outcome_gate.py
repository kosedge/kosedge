"""SOURCE READ vs TARGET JOIN sequencing (t5119u R2-B).

t5116u exposure (Alex PASS_RO 09fa4cc1, notes): ``load_outcomes`` read 2022–23
EVAL scores into memory before the G5 HOLD gate. They were not joined or
printed, and no metrics were produced, but the target loader ran pre-HOLD.

R2 path: the scoring-outcome loader is a callable invoked only after
HOLD / hash / claim have passed (EVAL) or after metadata eligibility
freeze + deterministic game pick (DEV_RESEARCH). Quote/forecast/metadata
reads are SOURCE READ and are not target joins.

CERT=0. No EVAL EXEC. DRAFT≠merge.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

PHASE_SOURCE_READ = "SOURCE_READ"
PHASE_TARGET_JOIN = "TARGET_JOIN"

# Files the R2-B path must never overwrite.
PRESERVED_T5116U = frozenset(
    {
        "ONE_RUN.json",
        "ONE_EXEC_RESULT_t5116u.json",
        "CURSOR_ONE_EXEC_RESULT_t5116u.md",
    }
)
PRESERVED_T5119U_FIRST_CASE = frozenset({"DEV_RESEARCH_t5119u_R2B.json"})
FIRST_CASE_RECORD_SHA256 = "621f0f843da8ac219d284448ac1cd3124bbcdba629c6df49a54b3b518fad30fc"
FIRST_CASE_FILE_SHA256 = "8cb9a2a1dbde5be9f27370622ab46934117b86e3e0597daf78374b9c5fe27a82"
FIRST_CASE_GAME_ID = "2020_02_CIN_CLE"


class OutcomeGateRefuse(ValueError):
    """Fail-closed sequencing: target join is not a source read."""


class ScoringOutcomeLoader:
    """Countable target-outcome loader. Call count is the join-phase proof."""

    def __init__(self, fn: Callable[[], Mapping[str, Mapping[str, Any]]]):
        if not callable(fn):
            raise OutcomeGateRefuse("scoring-outcome loader must be callable")
        self._fn = fn
        self.call_count = 0
        self.phase = PHASE_TARGET_JOIN

    def __call__(self) -> Mapping[str, Mapping[str, Any]]:
        self.call_count += 1
        loaded = self._fn()
        if loaded is None:
            raise OutcomeGateRefuse("scoring-outcome loader returned no target outcomes")
        return loaded


def refuse_both_preload_and_loader(outcomes: Any, outcome_loader: Any) -> None:
    if outcomes is not None and outcome_loader is not None:
        raise OutcomeGateRefuse(
            "pass outcome_loader or preloaded outcomes, not both — "
            "source READ ≠ JOIN/metrics (t5116u exposure)"
        )


def invoke_after_gates(
    outcomes: Mapping[str, Mapping[str, Any]] | None,
    outcome_loader: ScoringOutcomeLoader | Callable[[], Mapping[str, Mapping[str, Any]]] | None,
) -> Mapping[str, Mapping[str, Any]]:
    """TARGET JOIN only. Caller must have passed HOLD/hash/claim (or DEV pick)."""
    refuse_both_preload_and_loader(outcomes, outcome_loader)
    if outcome_loader is not None:
        loaded = outcome_loader()
        if loaded is None:
            raise OutcomeGateRefuse("scoring-outcome loader returned no target outcomes")
        return loaded
    if outcomes is None:
        raise OutcomeGateRefuse("scoring-outcome loader required after claim/eligibility")
    return outcomes


def refuse_preserved_t5116u_path(path: Any) -> None:
    if path is None:
        return
    name = getattr(path, "name", None) or str(path).rsplit("/", 1)[-1]
    if name in PRESERVED_T5116U:
        raise OutcomeGateRefuse(
            f"refusing write to preserved t5116u artifact {name} — look SPENT"
        )


def refuse_preloaded_scoring_outcomes(outcomes: Any) -> None:
    """R2 runner rule: preloaded scoring outcomes are forbidden (t5116u exposure)."""
    if outcomes is not None:
        raise OutcomeGateRefuse(
            "R2 runner refuses preloaded scoring outcomes — pass outcome_loader only "
            "(outcomes=None required)"
        )


def refuse_overwrite_first_case_record(path: Any) -> None:
    """Refuse the sealed first-case repo file (any dest that resolves to it)."""
    if path is None:
        return
    from pathlib import Path

    dest = Path(path).resolve()
    sealed = (
        Path(__file__).resolve().parents[5]
        / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5119u_R2B.json"
    )
    if dest == sealed.resolve():
        raise OutcomeGateRefuse(
            "refusing overwrite of preserved first-case DEV_RESEARCH_t5119u_R2B.json"
        )
