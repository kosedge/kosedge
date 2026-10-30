"""Build a snap-share `_5g` exposure ledger from an explicit IF window.

No scoring, no impact weights, no nowcast, no IF wiring, no data fetch.
Callers supply the situational grain, schedule join, participation bundles,
and PFR→GSIS map. Missing any of those fails closed.
"""

from __future__ import annotations

import math
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_snap_share_exposure_ledger.identity import (
    assert_as_of_not_after,
    canonicalize_as_of_ts,
    fingerprint_payload,
    make_ledger_id,
    mapping_to_sorted_pairs,
    parse_ledger_ts,
)
from src.services.nfl_snap_share_exposure_ledger.schema import (
    ALLOWED_SNAP_SOURCE_IDS,
    FORBIDDEN_IMPORT_NAMES,
    IF_5G_WINDOW_CONTRACT,
    LEDGER_SCHEMA_VERSION,
    REJECT_AS_OF_VIOLATION,
    REJECT_ID_UNMAPPED,
    REJECT_IDENTITY_COLLISION,
    REJECT_INPUT_INVALID,
    REJECT_INVALID_SNAP_DENOMINATOR,
    REJECT_POSITION_UNKNOWN,
    REJECT_SNAPS_INCOMPLETE,
    REJECT_SNAPS_MISSING,
    REJECT_SOURCE_UNSUPPORTED,
    SOURCE_SYNTH_SNAP_COUNTS,
    STARTER_LABEL_THRESHOLD,
    WINDOW_LABEL_5G,
    ExposureLedger,
    ExposureLedgerReject,
    ExposureLedgerRow,
    GameExposure,
    GameParticipationBundle,
    IdentityLink,
    ResolvedIf5gWindow,
    ScheduleGameRow,
    SideName,
    SituationalWeekRow,
    SnapFact,
    normalize_position,
    normalize_team,
    require_nonempty_str,
    side_for_position,
)
from src.services.nfl_snap_share_exposure_ledger.window import resolve_if_5g_window


def build_snap_share_5g_exposure_ledger(
    *,
    season: int,
    target_week: int,
    team: str,
    situational_rows: Sequence[SituationalWeekRow],
    schedule_rows: Sequence[ScheduleGameRow],
    participation_bundles: Sequence[GameParticipationBundle],
    identity_links: Sequence[IdentityLink],
    as_of_ts: str,
    rating_week: Optional[int] = None,
    declared_games_in_window_5: Optional[int] = None,
    target_game_id: Optional[str] = None,
    forecast_cutoff_ts: Optional[str] = None,
) -> ExposureLedger:
    """Return the `_5g` snap-share exposure ledger or raise fail-closed."""
    as_of = canonicalize_as_of_ts(as_of_ts)
    if forecast_cutoff_ts is not None:
        cutoff = canonicalize_as_of_ts(forecast_cutoff_ts)
        if parse_ledger_ts(as_of) > parse_ledger_ts(cutoff):
            raise ExposureLedgerReject(
                REJECT_AS_OF_VIOLATION,
                f"as_of_ts {as_of} is after forecast_cutoff_ts {cutoff}",
            )
        bound_ts = cutoff
    else:
        bound_ts = as_of
    window = resolve_if_5g_window(
        season=season,
        target_week=target_week,
        team=team,
        situational_rows=situational_rows,
        schedule_rows=schedule_rows,
        rating_week=rating_week,
        declared_games_in_window_5=declared_games_in_window_5,
        target_game_id=target_game_id,
        forecast_cutoff_ts=forecast_cutoff_ts,
    )
    pfr_to_gsis = _identity_index(identity_links)
    bundles = _index_bundles(
        window=window,
        bundles=participation_bundles,
        as_of_ts=bound_ts,
    )
    players = _collect_player_sides(window=window, bundles=bundles, pfr_to_gsis=pfr_to_gsis)
    rows = tuple(
        _build_player_row(
            window=window,
            bundles=bundles,
            pfr_to_gsis=pfr_to_gsis,
            player=player,
        )
        for player in players
    )
    input_fingerprint = fingerprint_payload(
        {
            "as_of_ts": as_of,
            "forecast_cutoff_ts": forecast_cutoff_ts,
            "bundles": [_bundle_fingerprint_payload(bundles[g.game_id]) for g in window.games],
            "identity_links": mapping_to_sorted_pairs(pfr_to_gsis),
            "schema_version": LEDGER_SCHEMA_VERSION,
            "target_week": window.target_week,
            "target_game_id": window.target_game_id,
            "window_fingerprint": window.window_fingerprint,
        }
    )
    output_fingerprint = fingerprint_payload(
        {
            "ledger": {
                "as_of_ts": as_of,
                "rating_week": window.rating_week,
                "target_week": window.target_week,
                "rows": [r.to_public_dict() for r in rows],
                "schema_version": LEDGER_SCHEMA_VERSION,
                "season": window.season,
                "team": window.team,
                "window": WINDOW_LABEL_5G,
                "window_fingerprint": window.window_fingerprint,
                "window_game_ids": list(window.game_ids),
            }
        }
    )
    notes = (
        "window=5g; CURRENT ROW at rating_week (completed-data week)",
        "pregame as-of: rating_week = target_week - 1; target/future games excluded",
        "verified_zero != UNKNOWN; incomplete source fails closed",
        "starter_label_derived is descriptive only (e_p >= 0.50)",
        "no player_impact / no point estimation / not wired to Independent Fair",
    )
    return ExposureLedger(
        schema_version=LEDGER_SCHEMA_VERSION,
        window=WINDOW_LABEL_5G,
        season=window.season,
        rating_week=window.rating_week,
        target_week=window.target_week,
        team=window.team,
        window_contract=IF_5G_WINDOW_CONTRACT,
        window_game_ids=window.game_ids,
        window_fingerprint=window.window_fingerprint,
        input_fingerprint=input_fingerprint,
        output_fingerprint=output_fingerprint,
        ledger_id=make_ledger_id(
            input_fingerprint=input_fingerprint,
            output_fingerprint=output_fingerprint,
        ),
        as_of_ts=as_of,
        rows=rows,
        notes=notes,
    )


def assert_builder_isolated() -> None:
    """Fail closed if this package imports a forbidden live module."""
    from pathlib import Path

    root = Path(__file__).resolve().parent
    offenders: List[str] = []
    for path in sorted(root.glob("*.py")):
        for module in _imported_modules(path.read_text(encoding="utf-8")):
            for name in FORBIDDEN_IMPORT_NAMES:
                if name == "nflverse" and module.startswith("src.services"):
                    continue
                if name in module.split("."):
                    offenders.append(f"{path.name}:{module}")
    if offenders:
        raise ExposureLedgerReject(
            REJECT_SOURCE_UNSUPPORTED,
            "builder isolation violated: " + ", ".join(sorted(set(offenders))),
        )


def _imported_modules(text: str) -> List[str]:
    modules: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("from "):
            rest = stripped[len("from ") :]
            target = rest.split(" import ", 1)[0].strip()
            if target:
                modules.append(target)
        elif stripped.startswith("import "):
            target = stripped[len("import ") :].split(" as ", 1)[0].split(",", 1)[0].strip()
            if target:
                modules.append(target)
    return modules


def _identity_index(links: Sequence[IdentityLink]) -> Dict[str, str]:
    if not links:
        raise ExposureLedgerReject(
            REJECT_ID_UNMAPPED, "identity map empty (no silent name match)"
        )
    out: Dict[str, str] = {}
    for link in links:
        pfr = require_nonempty_str(link.player_pfr_id, field_name="player_pfr_id")
        gsis = require_nonempty_str(link.player_gsis_id, field_name="player_gsis_id")
        prior = out.get(pfr)
        if prior is not None and prior != gsis:
            raise ExposureLedgerReject(
                REJECT_IDENTITY_COLLISION,
                f"pfr {pfr} maps to both {prior} and {gsis}",
            )
        out[pfr] = gsis
    return out


def _index_bundles(
    *,
    window: ResolvedIf5gWindow,
    bundles: Sequence[GameParticipationBundle],
    as_of_ts: str,
) -> Dict[str, GameParticipationBundle]:
    by_game: Dict[str, GameParticipationBundle] = {}
    for raw in bundles:
        game_id = require_nonempty_str(raw.game_id, field_name="game_id")
        team = normalize_team(require_nonempty_str(raw.team, field_name="team"))
        if team != window.team:
            continue
        if game_id in by_game:
            raise ExposureLedgerReject(
                REJECT_INPUT_INVALID, f"duplicate participation bundle for {game_id}"
            )
        by_game[game_id] = raw

    indexed: Dict[str, GameParticipationBundle] = {}
    for game in window.games:
        bundle = by_game.get(game.game_id)
        if bundle is None or bundle.completeness == "missing":
            raise ExposureLedgerReject(
                REJECT_SNAPS_MISSING,
                f"snap source missing for {window.team} game {game.game_id} "
                f"(UNKNOWN — not written as 0)",
            )
        if bundle.completeness != "complete":
            raise ExposureLedgerReject(
                REJECT_SNAPS_INCOMPLETE,
                f"snap source incomplete for {window.team} game {game.game_id} "
                f"(UNKNOWN — not interchangeable with verified 0)",
            )
        source_id = require_nonempty_str(bundle.source_id, field_name="source_id")
        if source_id not in ALLOWED_SNAP_SOURCE_IDS:
            raise ExposureLedgerReject(
                REJECT_SOURCE_UNSUPPORTED,
                f"unsupported snap source_id {source_id!r} for {game.game_id}",
            )
        bundle_as_of = canonicalize_as_of_ts(bundle.as_of_ts)
        assert_as_of_not_after(
            fact_ts=bundle_as_of, bound_ts=as_of_ts, field_name="bundle"
        )
        if not bundle.facts:
            raise ExposureLedgerReject(
                REJECT_SNAPS_INCOMPLETE,
                f"complete bundle for {game.game_id} has zero snap facts "
                f"(empty-complete is invalid)",
            )
        checked_facts: List[SnapFact] = []
        for fact in bundle.facts:
            if require_nonempty_str(fact.game_id, field_name="fact.game_id") != game.game_id:
                raise ExposureLedgerReject(
                    REJECT_INPUT_INVALID,
                    f"fact game_id {fact.game_id!r} != bundle {game.game_id}",
                )
            if normalize_team(fact.team) != window.team:
                raise ExposureLedgerReject(
                    REJECT_INPUT_INVALID,
                    f"fact team {fact.team!r} != window team {window.team}",
                )
            fact_source = require_nonempty_str(fact.source_id, field_name="fact.source_id")
            if fact_source != source_id:
                raise ExposureLedgerReject(
                    REJECT_SOURCE_UNSUPPORTED,
                    f"fact source_id {fact_source!r} != bundle {source_id!r}",
                )
            fact_as_of = canonicalize_as_of_ts(fact.as_of_ts)
            assert_as_of_not_after(
                fact_ts=fact_as_of, bound_ts=as_of_ts, field_name="snap_fact"
            )
            checked_facts.append(fact)
        indexed[game.game_id] = GameParticipationBundle(
            game_id=game.game_id,
            team=window.team,
            source_id=source_id,
            as_of_ts=bundle_as_of,
            completeness="complete",
            facts=tuple(checked_facts),
        )
    return indexed


def _collect_player_sides(
    *,
    window: ResolvedIf5gWindow,
    bundles: Mapping[str, GameParticipationBundle],
    pfr_to_gsis: Mapping[str, str],
) -> Tuple[Tuple[str, SideName, str, Tuple[str, ...]], ...]:
    """Universe = players who appear in any complete window snap list.

    Entire-window absences are not invented from an incomplete roster.
    A player who appears in some games is assigned verified 0 on other
    complete window games (they are in the participation universe).
    """
    found: Dict[Tuple[str, SideName], Dict[str, object]] = {}
    for game in window.games:
        seen_pfr: set[str] = set()
        for fact in bundles[game.game_id].facts:
            pfr = require_nonempty_str(fact.player_pfr_id, field_name="player_pfr_id")
            if pfr in seen_pfr:
                raise ExposureLedgerReject(
                    REJECT_INPUT_INVALID,
                    f"duplicate snap fact for {pfr} in {game.game_id}",
                )
            seen_pfr.add(pfr)
            gsis = pfr_to_gsis.get(pfr)
            if not gsis:
                raise ExposureLedgerReject(
                    REJECT_ID_UNMAPPED,
                    f"pfr {pfr} has no GSIS mapping (no name fallback)",
                )
            pos = normalize_position(fact.position)
            if not pos:
                raise ExposureLedgerReject(
                    REJECT_POSITION_UNKNOWN,
                    f"position missing for {pfr} in {game.game_id}",
                )
            side = side_for_position(pos)
            rec = found.setdefault(
                (gsis, side),
                {"name": fact.player_name or "", "pfr_ids": set()},
            )
            rec["pfr_ids"].add(pfr)  # type: ignore[union-attr]
            if not rec["name"] and fact.player_name:
                rec["name"] = fact.player_name
        _assert_gsis_unique_per_game(
            facts=bundles[game.game_id].facts,
            pfr_to_gsis=pfr_to_gsis,
            game_id=game.game_id,
        )

    players: List[Tuple[str, SideName, str, Tuple[str, ...]]] = []
    for (gsis, side), rec in sorted(found.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        pfr_ids = tuple(sorted(rec["pfr_ids"]))  # type: ignore[arg-type]
        name = str(rec["name"] or "")
        players.append((gsis, side, name, pfr_ids))
    return tuple(players)


def _assert_gsis_unique_per_game(
    *,
    facts: Sequence[SnapFact],
    pfr_to_gsis: Mapping[str, str],
    game_id: str,
) -> None:
    """Two PFR ids mapping to one GSIS in the same game is an identity change fail."""
    gsis_to_pfr: Dict[str, str] = {}
    for fact in facts:
        pfr = fact.player_pfr_id
        gsis = pfr_to_gsis[pfr]
        prior = gsis_to_pfr.get(gsis)
        if prior is not None and prior != pfr:
            raise ExposureLedgerReject(
                REJECT_IDENTITY_COLLISION,
                f"gsis {gsis} bound to both {prior} and {pfr} in {game_id}",
            )
        gsis_to_pfr[gsis] = pfr


def _build_player_row(
    *,
    window: ResolvedIf5gWindow,
    bundles: Mapping[str, GameParticipationBundle],
    pfr_to_gsis: Mapping[str, str],
    player: Tuple[str, SideName, str, Tuple[str, ...]],
) -> ExposureLedgerRow:
    gsis, side, name, pfr_ids = player
    exposures: List[GameExposure] = []
    source_ids: List[str] = []
    source_as_ofs: List[str] = []
    positions: List[str] = []
    for game in window.games:
        bundle = bundles[game.game_id]
        source_ids.append(bundle.source_id)
        source_as_ofs.append(bundle.as_of_ts)
        fact = _fact_for_player(bundle.facts, pfr_to_gsis, gsis)
        if fact is None:
            exposures.append(
                GameExposure(
                    game_id=game.game_id,
                    week=game.week,
                    snap_pct=0.0,
                    participation_status="verified_zero",
                    position=None,
                )
            )
            continue
        pos = normalize_position(fact.position)
        fact_side = side_for_position(pos)
        if fact_side != side:
            # Same GSIS on the other side this game: 0 on this side.
            exposures.append(
                GameExposure(
                    game_id=game.game_id,
                    week=game.week,
                    snap_pct=0.0,
                    participation_status="verified_zero",
                    position=pos,
                )
            )
            continue
        snap_pct = _measured_snap_pct(fact, side=side)
        positions.append(pos)
        exposures.append(
            GameExposure(
                game_id=game.game_id,
                week=game.week,
                snap_pct=snap_pct,
                participation_status="measured",
                position=pos,
            )
        )
    if not exposures or len(exposures) != len(window.games):
        raise ExposureLedgerReject(
            REJECT_INPUT_INVALID, f"exposure alignment failed for {gsis}"
        )
    embedded = sum(e.snap_pct for e in exposures) / float(len(exposures))
    position = positions[-1] if positions else side_for_position  # type: ignore[assignment]
    if not isinstance(position, str) or not position:
        raise ExposureLedgerReject(
            REJECT_POSITION_UNKNOWN, f"no measured position for {gsis} {side}"
        )
    row_no_hash = {
        "embedded_snap_share": embedded,
        "game_exposures": [
            {
                "game_id": e.game_id,
                "participation_status": e.participation_status,
                "position": e.position,
                "snap_pct": e.snap_pct,
                "week": e.week,
            }
            for e in exposures
        ],
        "game_ids": list(window.game_ids),
        "player_gsis_id": gsis,
        "player_name": name,
        "player_pfr_ids": list(pfr_ids),
        "position": position,
        "rating_week": window.rating_week,
        "target_week": window.target_week,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "season": window.season,
        "side": side,
        "source_as_of_ts": source_as_ofs,
        "source_ids": source_ids,
        "starter_label_derived": embedded >= STARTER_LABEL_THRESHOLD,
        "team": window.team,
        "window": WINDOW_LABEL_5G,
        "window_fingerprint": window.window_fingerprint,
    }
    return ExposureLedgerRow(
        window=WINDOW_LABEL_5G,
        season=window.season,
        rating_week=window.rating_week,
        target_week=window.target_week,
        team=window.team,
        player_gsis_id=gsis,
        player_pfr_ids=pfr_ids,
        player_name=name,
        position=position,
        side=side,
        game_ids=window.game_ids,
        game_exposures=tuple(exposures),
        embedded_snap_share=embedded,
        starter_label_derived=embedded >= STARTER_LABEL_THRESHOLD,
        source_ids=tuple(source_ids),
        source_as_of_ts=tuple(source_as_ofs),
        schema_version=LEDGER_SCHEMA_VERSION,
        row_fingerprint=fingerprint_payload(row_no_hash),
    )


def _fact_for_player(
    facts: Sequence[SnapFact],
    pfr_to_gsis: Mapping[str, str],
    gsis: str,
) -> Optional[SnapFact]:
    matched = [f for f in facts if pfr_to_gsis.get(f.player_pfr_id) == gsis]
    if not matched:
        return None
    if len(matched) > 1:
        raise ExposureLedgerReject(
            REJECT_IDENTITY_COLLISION,
            f"multiple snap facts for gsis {gsis} in one game",
        )
    return matched[0]


def _measured_snap_pct(fact: SnapFact, *, side: SideName) -> float:
    raw = fact.offense_pct if side == "offense" else fact.defense_pct
    snaps = fact.offense_snaps if side == "offense" else fact.defense_snaps
    if raw is None:
        raise ExposureLedgerReject(
            REJECT_INVALID_SNAP_DENOMINATOR,
            f"{side}_pct missing for {fact.player_pfr_id} in {fact.game_id} "
            f"(UNKNOWN — not written as 0)",
        )
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ExposureLedgerReject(
            REJECT_INVALID_SNAP_DENOMINATOR,
            f"{side}_pct non-numeric for {fact.player_pfr_id} in {fact.game_id}",
        )
    pct = float(raw)
    if not math.isfinite(pct):
        raise ExposureLedgerReject(
            REJECT_INVALID_SNAP_DENOMINATOR,
            f"{side}_pct non-finite for {fact.player_pfr_id} in {fact.game_id}",
        )
    if pct < 0.0:
        raise ExposureLedgerReject(
            REJECT_INVALID_SNAP_DENOMINATOR,
            f"{side}_pct {pct} < 0 for {fact.player_pfr_id} in {fact.game_id}",
        )
    if pct > 100.0:
        raise ExposureLedgerReject(
            REJECT_INVALID_SNAP_DENOMINATOR,
            f"{side}_pct {pct} > 100 for {fact.player_pfr_id} in {fact.game_id}",
        )
    # Match snap_depth_ingest._normalize_pct: 0-100 → 0-1; (1, 1.5] stays as fraction.
    if pct > 1.5:
        pct = pct / 100.0
    if pct > 1.0:
        raise ExposureLedgerReject(
            REJECT_INVALID_SNAP_DENOMINATOR,
            f"{side}_pct {raw} not a valid fraction for {fact.player_pfr_id} "
            f"in {fact.game_id}",
        )
    if snaps is not None:
        if isinstance(snaps, bool) or not isinstance(snaps, (int, float)):
            raise ExposureLedgerReject(
                REJECT_INVALID_SNAP_DENOMINATOR,
                f"{side}_snaps non-numeric for {fact.player_pfr_id} in {fact.game_id}",
            )
        snap_n = float(snaps)
        if not math.isfinite(snap_n) or snap_n < 0.0:
            raise ExposureLedgerReject(
                REJECT_INVALID_SNAP_DENOMINATOR,
                f"{side}_snaps {snaps} invalid for {fact.player_pfr_id} in {fact.game_id}",
            )
        if snap_n == 0.0 and pct > 0.0:
            raise ExposureLedgerReject(
                REJECT_INVALID_SNAP_DENOMINATOR,
                f"{side} snaps=0 but pct={pct} for {fact.player_pfr_id} in {fact.game_id}",
            )
        if snap_n > 0.0 and pct == 0.0:
            raise ExposureLedgerReject(
                REJECT_INVALID_SNAP_DENOMINATOR,
                f"{side} snaps={snap_n} but pct=0 for {fact.player_pfr_id} in {fact.game_id}",
            )
    return pct


def _bundle_fingerprint_payload(bundle: GameParticipationBundle) -> Dict[str, object]:
    facts = [
        {
            "as_of_ts": canonicalize_as_of_ts(f.as_of_ts),
            "defense_pct": f.defense_pct,
            "defense_snaps": f.defense_snaps,
            "game_id": f.game_id,
            "offense_pct": f.offense_pct,
            "offense_snaps": f.offense_snaps,
            "player_name": f.player_name,
            "player_pfr_id": f.player_pfr_id,
            "position": f.position,
            "source_id": f.source_id,
            "team": normalize_team(f.team),
        }
        for f in sorted(bundle.facts, key=lambda x: x.player_pfr_id)
    ]
    return {
        "as_of_ts": bundle.as_of_ts,
        "completeness": bundle.completeness,
        "facts": facts,
        "game_id": bundle.game_id,
        "source_id": bundle.source_id,
        "team": bundle.team,
    }


def default_synth_source_id() -> str:
    return SOURCE_SYNTH_SNAP_COUNTS
