"""Daily intel overrides → the one depth SoT pack (no second map).

Destinations
------------
- ``sot``: write into the pack (identity / depth / injury). QB identity changes
  flag ``research republish recommended`` (do not auto-100k).
- ``kei_only``: write injury / competition flags the frozen model missed so
  Week 1 KEI reprice can move on next fair-lines read.
- ``wait_republish``: log only; do not mutate the pack.

Approved override rows must include team, field, before, after, reason, as_of,
confidence. Twitter/X is never a sole source.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.nfl_kei_week1_reprice import (
    Week1Pack,
    week1_slate_reprice_table,
)

DESTINATIONS = frozenset({"sot", "kei_only", "wait_republish"})
IDENTITY_FIELDS = frozenset({"player_name", "player_id", "depth_order", "depth_slot"})
QB_REPUBLISH_FIELDS = IDENTITY_FIELDS | frozenset({"competition_status"})
# snap_share_prior / snap_share_package: accept-only via proposed_patch (sot).
# See ``nfl_snap_share_prior``.
# confirmation (high|med|low): stamped on committed situation events —
# see ``nfl_confirmation_variance``.
ALLOWED_FIELDS = IDENTITY_FIELDS | frozenset(
    {
        "injury_status",
        "injury_window",
        "injury_note",
        "competition_status",
        "role_confidence",
        "snap_share_prior",
        "snap_share_package",
        "confirmation",
    }
)
# Rest/weather game-card fields are remat SoT only — never note / intel overrides.
# See ``nfl_rest_weather_game_card.GAME_CARD_FIELDS``.
# One pack, three layers — skill rows + OL + defense. No second SoT / queue type.
PACK_SOT_LAYERS = ("rows", "ol_roles", "defense_roles")
DEFENSE_POSITIONS = frozenset({"EDGE", "DL", "LB", "CB", "S", "NB"})

_SERVICES = Path(__file__).resolve().parent
PACK_DEFAULT = _SERVICES / "nfl_season_engine" / "data" / "nfl_depth_chart_2026_w1.json"
SCHEDULE_DEFAULT = _SERVICES / "nfl_season_engine" / "data" / "nfl_regular_schedule_2026.json"


def _norm_team(abbr: Any) -> str:
    token = str(abbr or "").strip().upper()
    if token in {"LAR", "LA"}:
        return "LA"
    if token == "AZ":
        return "ARI"
    return token


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_override_file(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("override file must be a JSON object")
    return payload


def normalize_override(raw: Mapping[str, Any]) -> Dict[str, Any]:
    team = _norm_team(raw.get("team"))
    field = str(raw.get("field") or "").strip()
    dest = str(raw.get("destination") or "kei_only").strip().lower()
    if dest not in DESTINATIONS:
        raise ValueError(f"invalid destination {dest!r} (use sot / kei_only / wait_republish)")
    if field not in ALLOWED_FIELDS:
        # Explicit rest/weather game-card rejection (remat SoT; notes cannot write).
        from src.services.nfl_rest_weather_game_card import reject_note_game_card_write

        reject_note_game_card_write(field)
        raise ValueError(f"unsupported field {field!r}")
    if not team:
        raise ValueError("team is required")
    from src.services.nfl_confirmation_variance import normalize_confirmation

    conf_level = normalize_confirmation(raw.get("confirmation"))
    out = {
        "team": team,
        "player_name": str(raw.get("player_name") or "").strip(),
        "player_id": str(raw.get("player_id") or "").strip(),
        "position": str(raw.get("position") or "").strip().upper(),
        "layer": str(raw.get("layer") or "rows").strip().lower(),
        "field": field,
        "before": raw.get("before"),
        "after": raw.get("after"),
        "reason": str(raw.get("reason") or "").strip(),
        "as_of": str(raw.get("as_of") or "").strip(),
        "confidence": str(raw.get("confidence") or "").strip().lower(),
        "destination": dest,
        "sources": list(raw.get("sources") or []),
    }
    if conf_level:
        out["confirmation"] = conf_level
    return out


def _row_match(row: Mapping[str, Any], ov: Mapping[str, Any]) -> bool:
    if _norm_team(row.get("team")) != ov["team"]:
        return False
    pos = ov.get("position")
    if pos and str(row.get("position") or "").upper() != pos:
        return False
    pid = ov.get("player_id")
    if pid and str(row.get("player_id") or "") == pid:
        return True
    name = ov.get("player_name")
    if name and str(row.get("player_name") or "").strip() == name:
        return True
    return False


def _target_list(payload: Dict[str, Any], layer: str) -> List[Dict[str, Any]]:
    layer_n = str(layer or "rows").strip().lower() or "rows"
    if layer_n not in PACK_SOT_LAYERS:
        raise ValueError(
            f"invalid layer {layer!r} (use {' / '.join(PACK_SOT_LAYERS)})"
        )
    rows = payload.setdefault(layer_n, [])
    if not isinstance(rows, list):
        raise ValueError(f"{layer_n} must be a list")
    return rows


@dataclass
class OverrideApplyResult:
    payload: Dict[str, Any]
    applied: List[Dict[str, Any]] = field(default_factory=list)
    skipped: List[Dict[str, Any]] = field(default_factory=list)
    touched_teams: List[str] = field(default_factory=list)
    republish_recommended: bool = False
    republish_reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "applied": self.applied,
            "skipped": self.skipped,
            "touched_teams": self.touched_teams,
            "republish_recommended": self.republish_recommended,
            "republish_reasons": self.republish_reasons,
            "snapshot_id": self.payload.get("snapshot_id"),
            "as_of": self.payload.get("as_of"),
        }


def apply_intel_overrides(
    payload: Mapping[str, Any],
    overrides: Sequence[Mapping[str, Any]],
    *,
    as_of: Optional[str] = None,
) -> OverrideApplyResult:
    """Apply approved overrides onto a copy of the depth pack."""
    out = copy.deepcopy(dict(payload))
    applied: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    touched: set[str] = set()
    republish = False
    republish_reasons: List[str] = []

    for raw in overrides:
        ov = normalize_override(raw)
        if ov["destination"] == "wait_republish":
            skipped.append({**ov, "skip_reason": "wait_republish — not written"})
            republish = True
            republish_reasons.append(
                f"{ov['team']} {ov['player_name']} {ov['field']} wait_republish"
            )
            continue
        rows = _target_list(out, ov["layer"])
        matches = [r for r in rows if isinstance(r, dict) and _row_match(r, ov)]
        if not matches:
            skipped.append({**ov, "skip_reason": "no matching SoT row"})
            continue
        for row in matches:
            # Open competition stays a mixture — sleeper/notes cannot close.
            from src.services.nfl_confirmation_variance import (
                notes_or_sleeper_cannot_close_open_competition,
            )

            close_block = notes_or_sleeper_cannot_close_open_competition(ov, row)
            if close_block:
                skipped.append({**ov, "skip_reason": close_block})
                continue
            current = row.get(ov["field"])
            expected = ov.get("before")
            if expected not in (None, "") and str(current) != str(expected):
                skipped.append(
                    {
                        **ov,
                        "skip_reason": f"before mismatch (pack={current!r} expected={expected!r})",
                    }
                )
                continue
            after_val = ov["after"]
            if ov["field"] == "snap_share_prior":
                from src.services.nfl_snap_share_prior import clamp_share

                after_val = clamp_share(after_val)
            if ov["field"] == "confirmation":
                from src.services.nfl_confirmation_variance import normalize_confirmation

                after_val = normalize_confirmation(after_val) or after_val
            row[ov["field"]] = after_val
            applied.append(
                {
                    **ov,
                    "after": after_val,
                    "matched_player_id": row.get("player_id"),
                    "previous": current,
                }
            )
            touched.add(ov["team"])
            pos = str(row.get("position") or ov.get("position") or "").upper()
            if ov["destination"] == "sot" and (
                ov["field"] in IDENTITY_FIELDS
                or (pos == "QB" and ov["field"] in QB_REPUBLISH_FIELDS)
            ):
                republish = True
                republish_reasons.append(
                    f"{ov['team']} {ov['player_name']} {ov['field']} identity/QB SoT change"
                )

    # Accept out → redistribute snap_share_prior to existing committee (no crowns).
    from src.services.nfl_snap_share_prior import apply_out_redistribution_after_overrides

    snap_events = apply_out_redistribution_after_overrides(out, applied)
    if snap_events:
        out["snap_share_redistributions"] = snap_events

    # Stamp confirmation high|med|low on every committed situation event.
    from src.services.nfl_confirmation_variance import apply_confirmation_to_pack_events

    apply_confirmation_to_pack_events(out, applied)

    if as_of:
        out["daily_intel_as_of"] = as_of
        notes = list(out.get("notes") or [])
        stamp = f"Daily intel {as_of}: {len(applied)} override(s) applied"
        if stamp not in notes:
            notes.append(stamp)
        out["notes"] = notes

    return OverrideApplyResult(
        payload=out,
        applied=applied,
        skipped=skipped,
        touched_teams=sorted(touched),
        republish_recommended=republish,
        republish_reasons=republish_reasons,
    )


def kei_smoke_for_teams(
    payload: Mapping[str, Any],
    teams: Sequence[str],
    *,
    schedule: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Reprice Week 1 games involving ``teams`` from the (possibly mutated) pack."""
    pack = Week1Pack.from_payload(payload)
    wanted = {_norm_team(t) for t in teams}
    if schedule is None:
        raw = json.loads(SCHEDULE_DEFAULT.read_text(encoding="utf-8"))
        schedule = [g for g in raw.get("games") or [] if int(g.get("week") or 0) == 1]
    games = [
        g
        for g in schedule
        if _norm_team(g.get("home_team") or g.get("home_abbr")) in wanted
        or _norm_team(g.get("away_team") or g.get("away_abbr")) in wanted
    ]
    return week1_slate_reprice_table(games, pack=pack)


def format_smoke_diff(
    before_rows: Sequence[Mapping[str, Any]],
    after_rows: Sequence[Mapping[str, Any]],
) -> List[str]:
    before = {str(r.get("game")): r for r in before_rows}
    lines: List[str] = []
    for row in after_rows:
        game = str(row.get("game"))
        prev = before.get(game) or {}
        d_spread = float(row.get("spread_delta") or 0) - float(prev.get("spread_delta") or 0)
        new_factors = [f for f in (row.get("factors") or []) if f not in (prev.get("factors") or [])]
        if abs(d_spread) > 1e-9 or new_factors:
            lines.append(
                f"{game}: Δspread {d_spread:+.2f}  new={new_factors or row.get('factors')}"
            )
    if not lines:
        lines.append("no KEI point/driver movement on touched Week 1 games")
    return lines
