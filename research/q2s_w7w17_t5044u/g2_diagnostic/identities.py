"""141-identity restriction. Forecast-side only. No outcome parse."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from constants import (
    ACCEPT_TIP,
    ELIGIBLE_SEASON,
    IF_MUS_PATH,
    JOINT_JSON_PATH,
    LOOK_CONSUMED_SHA8,
    LOOK_TIP,
    N_GAMES,
    OTHER_EVAL_SEASONS,
    PROTECTED_SEASONS,
    Q2S_ROWS_PATH,
    Q2_EVAL_CLOSED,
    WEEK_BLOCKS,
)


class IdentityRefuse(RuntimeError):
    pass


Identity = tuple[int, int, str, str]


def identity_key(row: Mapping[str, Any]) -> Identity:
    return (
        int(row["season"]),
        int(row["week"]),
        str(row.get("home") or row.get("home_team")),
        str(row.get("away") or row.get("away_team")),
    )


def assert_eligible_identity(key: Identity, *, context: str) -> None:
    season, week, home, away = key
    if season in PROTECTED_SEASONS:
        raise IdentityRefuse(
            f"{context}: protected season {season} refused (no 2024–25 open)"
        )
    if season in OTHER_EVAL_SEASONS:
        raise IdentityRefuse(
            f"{context}: EVAL season {season} refused (no other eval)"
        )
    if season != ELIGIBLE_SEASON:
        raise IdentityRefuse(
            f"{context}: season {season} != {ELIGIBLE_SEASON} — other-season refuse"
        )
    if int(week) not in WEEK_BLOCKS:
        raise IdentityRefuse(
            f"{context}: week {week} outside W7–W17"
        )
    if not home or not away:
        raise IdentityRefuse(f"{context}: empty team code")


def assert_not_q2_eval_reopen(flag: bool | None) -> None:
    if flag:
        raise IdentityRefuse(
            f"Q2 EVAL {Q2_EVAL_CLOSED} CLOSED — examined-70 reopen refused"
        )


def _rows_from_payload(payload: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise IdentityRefuse(f"{label} missing rows[]")
    return rows


def extract_forecast_identities(
    joint_payload: Mapping[str, Any],
    q2s_payload: Mapping[str, Any],
    if_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Align 141 identities across joint / q2s / IF_MUS. No outcomes."""
    j_rows = _rows_from_payload(joint_payload, "joint")
    q_rows = _rows_from_payload(q2s_payload, "q2s")
    i_rows = _rows_from_payload(if_payload, "if_mus")
    if len(j_rows) != N_GAMES:
        raise IdentityRefuse(f"joint n={len(j_rows)} != {N_GAMES}")
    if len(q_rows) != N_GAMES:
        raise IdentityRefuse(f"q2s n={len(q_rows)} != {N_GAMES}")
    if len(i_rows) != N_GAMES:
        raise IdentityRefuse(f"if_mus n={len(i_rows)} != {N_GAMES}")

    q_by_id = {str(r["game_id"]): r for r in q_rows}
    i_by_id = {str(r["game_id"]): r for r in i_rows}
    if len(q_by_id) != N_GAMES or len(i_by_id) != N_GAMES:
        raise IdentityRefuse("duplicate forecast game_id")

    out: list[dict[str, Any]] = []
    seen: set[Identity] = set()
    weeks: set[int] = set()
    for row in j_rows:
        gid = str(row["game_id"])
        if gid not in q_by_id or gid not in i_by_id:
            raise IdentityRefuse(f"forecast identity miss {gid}")
        key = identity_key(row)
        qkey = identity_key(q_by_id[gid])
        ikey = identity_key(i_by_id[gid])
        if key != qkey or key != ikey:
            raise IdentityRefuse(
                f"forecast identity mismatch {gid}: joint={key} q2s={qkey} if={ikey}"
            )
        assert_eligible_identity(key, context=gid)
        if key in seen:
            raise IdentityRefuse(f"duplicate identity {key}")
        seen.add(key)
        weeks.add(int(key[1]))
        out.append(
            {
                "game_id": gid,
                "season": key[0],
                "week": key[1],
                "home": key[2],
                "away": key[3],
            }
        )
    if len(out) != N_GAMES:
        raise IdentityRefuse(f"identity n={len(out)} != {N_GAMES}")
    if weeks != set(WEEK_BLOCKS):
        raise IdentityRefuse(f"forecast weeks {sorted(weeks)} != W7–W17")
    return out


def identities_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    canonical = json.dumps(list(records), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def keys_from_records(records: Sequence[Mapping[str, Any]]) -> list[Identity]:
    return [identity_key(r) for r in records]


def require_exact_141(keys: Iterable[Identity], *, context: str) -> list[Identity]:
    out = list(keys)
    if len(out) != N_GAMES:
        raise IdentityRefuse(f"{context}: n={len(out)} != {N_GAMES}")
    seen: set[Identity] = set()
    for key in out:
        assert_eligible_identity(key, context=context)
        if key in seen:
            raise IdentityRefuse(f"{context}: duplicate {key}")
        seen.add(key)
    return out


def load_forecast_identities_from_disk() -> list[dict[str, Any]]:
    """Read forecast artifacts only. Does not open 50bda875."""
    joint = json.loads(JOINT_JSON_PATH.read_text())
    q2s = json.loads(Q2S_ROWS_PATH.read_text())
    if_mus = json.loads(IF_MUS_PATH.read_text())
    return extract_forecast_identities(joint, q2s, if_mus)


def identity_boundary_cite() -> dict[str, str]:
    return {
        "look_tip": LOOK_TIP,
        "accept_tip": ACCEPT_TIP,
        "look_consumed_sha8": LOOK_CONSUMED_SHA8,
        "q2_eval": f"{Q2_EVAL_CLOSED} CLOSED",
        "note": (
            "Cited identity boundary only. No LOOK invocation. "
            "No Q2 EVAL reopen. No counter rewrite."
        ),
    }
