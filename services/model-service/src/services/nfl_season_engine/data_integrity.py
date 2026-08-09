"""Formal NFL depth/roster data-integrity gate (Phase 1).

Hard-fail validators for the packaged depth SoT. Names are display-only;
``player_id`` (nflverse GSIS when available) is the join key for sim roles.

See ``data/ops/nfl-data-integrity-gate-20260809.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import ENGINE_VERSION

_PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"
# Keep team list local to avoid circular import with loaders.
NFL_TEAMS: List[str] = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
]

# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

SKILL_POSITIONS = ("QB", "RB", "WR", "TE")
CRITICAL_STARTER_ROLES = ("QB", "RB", "WR", "TE")  # depth_order == 1 required
# Camp / in-season: pack must be refreshed within this many days.
DEFAULT_MAX_AGE_DAYS = 7
# After residual-other clipping, share_integrity_summary.ok must be True.
# Pre-clip named sums may exceed 1.0 - floor (locked pass-pool contract); only
# absurd pre-clip blow-ups fail (indicates depth prior corruption).
SHARE_NAMED_HARD_MAX = 1.50

SNAPSHOTS_DIR = _PACKAGE_DATA_DIR / "snapshots"


class DataIntegrityError(RuntimeError):
    """Raised when the depth SoT fails a hard gate."""


@dataclass
class IntegrityFinding:
    check: str
    severity: str  # "fail" only for Phase 1 hard gates
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityReport:
    ok: bool
    snapshot_id: str
    pack_path: str
    pack_sha256: str
    as_of: str
    findings: List[IntegrityFinding] = field(default_factory=list)
    teams_touched: List[str] = field(default_factory=list)
    checks_run: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "snapshot_id": self.snapshot_id,
            "pack_path": self.pack_path,
            "pack_sha256": self.pack_sha256,
            "as_of": self.as_of,
            "teams_touched": list(self.teams_touched),
            "checks_run": list(self.checks_run),
            "findings": [
                {
                    "check": f.check,
                    "severity": f.severity,
                    "message": f.message,
                    "details": f.details,
                }
                for f in self.findings
            ],
        }


def compute_snapshot_id(
    *,
    season: int,
    week: int,
    as_of: str,
    as_of_timestamp: str = "",
    content_sha12: str = "",
) -> str:
    """Stable snapshot id: ``nfl-depth-{season}-w{week}-{as_of}[-{sha12}]``."""
    as_of_token = (as_of or "unknown").replace(":", "").replace(" ", "T")
    if as_of_timestamp:
        # Prefer ISO date portion already in as_of; append compact time if useful.
        try:
            ts = as_of_timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            as_of_token = dt.strftime("%Y%m%dT%H%M%SZ")
        except ValueError:
            as_of_token = as_of_token.replace("-", "")
    else:
        as_of_token = as_of_token.replace("-", "")
    base = f"nfl-depth-{int(season)}-w{int(week)}-{as_of_token}"
    if content_sha12:
        return f"{base}-{content_sha12}"
    return base


def pack_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_snapshot_metadata(payload: Dict[str, Any], *, pack_path: Path) -> Dict[str, Any]:
    """Return payload with snapshot_id / content hash filled (does not write)."""
    out = dict(payload)
    sha = pack_sha256(pack_path)
    sha12 = sha[:12]
    season = int(out.get("season") or 2026)
    week = int(out.get("week") or 1)
    as_of = str(out.get("as_of") or "")
    as_of_ts = str(out.get("as_of_timestamp") or "")
    snap = str(out.get("snapshot_id") or "").strip()
    if not snap:
        snap = compute_snapshot_id(
            season=season,
            week=week,
            as_of=as_of,
            as_of_timestamp=as_of_ts,
            content_sha12=sha12,
        )
    out["snapshot_id"] = snap
    out["content_sha256"] = sha
    out.setdefault("identity_scheme", "nflverse_gsis_player_id")
    out.setdefault(
        "identity_notes",
        "player_id is the SoT join key (GSIS 00-####### when known). "
        "player_name / team strings are display or match-assist only.",
    )
    return out


def archive_snapshot(pack_path: Path, payload: Mapping[str, Any]) -> Path:
    """Write an immutable copy under data/snapshots/{snapshot_id}.json."""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    snap = str(payload.get("snapshot_id") or "unknown")
    dest = SNAPSHOTS_DIR / f"{snap}.json"
    if not dest.exists():
        dest.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    # Also keep a pointer to "active"
    active = SNAPSHOTS_DIR / "ACTIVE_SNAPSHOT.json"
    active.write_text(
        json.dumps(
            {
                "snapshot_id": snap,
                "pack_path": str(pack_path.name),
                "as_of": payload.get("as_of"),
                "daily_intel_as_of": payload.get("daily_intel_as_of"),
                "archived_at_utc": datetime.now(timezone.utc).isoformat(),
                "archive_file": dest.name,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def _parse_as_of(raw: str) -> Optional[date]:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text[:8], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _skill_rows(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for r in payload.get("rows") or []:
        if not isinstance(r, Mapping):
            continue
        pos = str(r.get("position") or "").strip().upper()
        if pos not in SKILL_POSITIONS:
            continue
        team = str(r.get("team") or "").strip().upper()
        if team == "LAR":
            team = "LA"
        if team == "WSH":
            team = "WAS"
        try:
            depth = int(r.get("depth_order") or 0)
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "team": team,
                "position": pos,
                "depth_order": depth,
                "player_id": str(r.get("player_id") or "").strip(),
                "player_name": str(r.get("player_name") or "").strip(),
                "injury_status": str(r.get("injury_status") or "active").strip().lower(),
            }
        )
    return rows


def validate_depth_sot_pack(
    payload: Mapping[str, Any],
    *,
    pack_path: Optional[Path] = None,
    reference_date: Optional[date] = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    sim_teams: Optional[Sequence[str]] = None,
    check_stale: bool = True,
    check_shares: bool = True,
    check_engine_web_agreement: bool = True,
) -> IntegrityReport:
    """Run hard-fail integrity checks on a depth pack payload.

    Returns a report; does not raise. Use :func:`assert_depth_sot_integrity` to raise.
    """
    path = pack_path or Path("in-memory")
    sha = pack_sha256(path) if path.is_file() else hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    as_of = str(payload.get("as_of") or "")
    snapshot_id = str(payload.get("snapshot_id") or "").strip() or compute_snapshot_id(
        season=int(payload.get("season") or 2026),
        week=int(payload.get("week") or 1),
        as_of=as_of,
        as_of_timestamp=str(payload.get("as_of_timestamp") or ""),
        content_sha12=sha[:12],
    )
    findings: List[IntegrityFinding] = []
    checks: List[str] = []
    teams = list(sim_teams) if sim_teams is not None else list(NFL_TEAMS)
    rows = _skill_rows(payload)

    # --- 1. Stable identity: player_id present + unique across teams ---
    checks.append("stable_identity_player_id")
    missing_ids = [
        f"{r['team']}-{r['position']}{r['depth_order']}-{r['player_name']}"
        for r in rows
        if not r["player_id"]
    ]
    if missing_ids:
        findings.append(
            IntegrityFinding(
                check="stable_identity_player_id",
                severity="fail",
                message=f"{len(missing_ids)} skill row(s) missing player_id",
                details={"examples": missing_ids[:12]},
            )
        )

    checks.append("duplicate_active_assignment")
    by_id: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        pid = r["player_id"]
        if not pid:
            continue
        # Treat cut/waived as inactive for cross-team uniqueness.
        if r["injury_status"] in {"cut", "waived", "released"}:
            continue
        by_id.setdefault(pid, []).append(r)
    dups = {
        pid: rs
        for pid, rs in by_id.items()
        if len({r["team"] for r in rs}) > 1
    }
    if dups:
        examples = {
            pid: [
                f"{r['team']}-{r['position']}{r['depth_order']}:{r['player_name']}"
                for r in rs
            ]
            for pid, rs in list(dups.items())[:8]
        }
        findings.append(
            IntegrityFinding(
                check="duplicate_active_assignment",
                severity="fail",
                message=f"{len(dups)} player_id(s) active on multiple teams",
                details={"examples": examples},
            )
        )

    # --- 2. Missing QB1 + critical starters ---
    checks.append("missing_qb1")
    missing_qb1 = []
    for team in teams:
        qb1 = [
            r
            for r in rows
            if r["team"] == team and r["position"] == "QB" and r["depth_order"] == 1
        ]
        if not qb1:
            missing_qb1.append(team)
    if missing_qb1:
        findings.append(
            IntegrityFinding(
                check="missing_qb1",
                severity="fail",
                message=f"Missing QB1 for {len(missing_qb1)} team(s)",
                details={"teams": missing_qb1},
            )
        )

    checks.append("critical_role_gaps")
    role_gaps: Dict[str, List[str]] = {}
    for team in teams:
        for pos in CRITICAL_STARTER_ROLES:
            hit = [
                r
                for r in rows
                if r["team"] == team and r["position"] == pos and r["depth_order"] == 1
            ]
            if not hit:
                role_gaps.setdefault(pos + "1", []).append(team)
    # Also duplicate (team, pos, depth)
    slot_map: Dict[Tuple[str, str, int], List[str]] = {}
    for r in rows:
        key = (r["team"], r["position"], r["depth_order"])
        slot_map.setdefault(key, []).append(r["player_name"])
    dup_slots = {f"{t}-{p}{d}": names for (t, p, d), names in slot_map.items() if len(names) > 1}
    if role_gaps or dup_slots:
        findings.append(
            IntegrityFinding(
                check="critical_role_gaps",
                severity="fail",
                message="Critical starter gaps or duplicate depth slots",
                details={"missing_starters": role_gaps, "duplicate_slots": dup_slots},
            )
        )

    # --- 3. Stale policy ---
    if check_stale:
        checks.append("stale_snapshot")
        ref = reference_date or datetime.now(timezone.utc).date()
        pack_day = _parse_as_of(as_of) or _parse_as_of(
            str(payload.get("daily_intel_as_of") or "")
        )
        if pack_day is None:
            findings.append(
                IntegrityFinding(
                    check="stale_snapshot",
                    severity="fail",
                    message="Pack missing parseable as_of / daily_intel_as_of",
                    details={"as_of": as_of},
                )
            )
        else:
            age = (ref - pack_day).days
            if age > int(max_age_days):
                findings.append(
                    IntegrityFinding(
                        check="stale_snapshot",
                        severity="fail",
                        message=(
                            f"Snapshot age {age}d exceeds policy max_age_days={max_age_days}"
                        ),
                        details={
                            "as_of": as_of,
                            "reference_date": ref.isoformat(),
                            "age_days": age,
                            "max_age_days": max_age_days,
                        },
                    )
                )

    # --- 4. Usage share blow-up (engine roster book) ---
    if check_shares:
        checks.append("usage_share_limits")
        share_failures = _check_usage_shares(payload, teams=teams)
        if share_failures:
            findings.append(
                IntegrityFinding(
                    check="usage_share_limits",
                    severity="fail",
                    message=f"Usage share limits breached on {len(share_failures)} team(s)",
                    details={"teams": share_failures[:16]},
                )
            )

    # --- 5. Engine vs web/BFF sampled agreement (same snapshot file) ---
    if check_engine_web_agreement and path.is_file():
        checks.append("engine_web_roster_agreement")
        disagree = _sample_engine_web_agreement(payload, path=path, teams=teams)
        if disagree:
            findings.append(
                IntegrityFinding(
                    check="engine_web_roster_agreement",
                    severity="fail",
                    message="Engine vs web/BFF sample disagree on same snapshot",
                    details={"mismatches": disagree[:12]},
                )
            )

    # Require snapshot_id present once metadata expected
    checks.append("snapshot_id_present")
    if not str(payload.get("snapshot_id") or "").strip():
        # Soft-fill is done by ensure_snapshot_metadata; hard-fail if caller
        # asked us to validate a production active pack without id.
        findings.append(
            IntegrityFinding(
                check="snapshot_id_present",
                severity="fail",
                message="Pack missing snapshot_id (run ensure_snapshot_metadata / archive)",
                details={},
            )
        )

    teams_touched = sorted({r["team"] for r in rows if r["team"] in teams})
    ok = not any(f.severity == "fail" for f in findings)
    return IntegrityReport(
        ok=ok,
        snapshot_id=snapshot_id,
        pack_path=str(path),
        pack_sha256=sha,
        as_of=as_of,
        findings=findings,
        teams_touched=teams_touched,
        checks_run=checks,
    )


def _check_usage_shares(
    payload: Mapping[str, Any],
    *,
    teams: Sequence[str],
) -> List[Dict[str, Any]]:
    """Build prior shares from depth rows the same way the loader does, then sum."""
    # Import locally to avoid circular import at module load in some test paths.
    from src.services.nfl_season_engine.loaders import _role_from_depth_row
    from src.services.nfl_season_engine.player_usage import share_integrity_summary
    from src.services.nfl_season_engine.usage_roles import annotate_roster_book

    failures: List[Dict[str, Any]] = []
    book: Dict[str, List[Any]] = {t: [] for t in teams}
    for r in _skill_rows(payload):
        team = r["team"]
        if team not in book:
            continue
        role, _ = _role_from_depth_row(
            team=team,
            pos=r["position"],
            depth=r["depth_order"],
            name=r["player_name"] or "Unknown",
            source="integrity_gate",
        )
        book[team].append(role)
    book = annotate_roster_book(book)
    for team in teams:
        roles = book.get(team) or []
        if not roles:
            failures.append({"team": team, "reason": "empty_roster"})
            continue
        summary = share_integrity_summary(roles, script="neutral", pass_rate=0.58)
        rush = float(summary["named_rush_share_sum"])
        tgt = float(summary["named_target_share_sum"])
        modeled_r = float(summary["modeled_rush_plus_other"])
        modeled_t = float(summary["modeled_target_plus_other"])
        blow = rush > SHARE_NAMED_HARD_MAX or tgt > SHARE_NAMED_HARD_MAX
        off_one = abs(modeled_r - 1.0) > 1e-3 or abs(modeled_t - 1.0) > 1e-3
        if blow or not summary.get("ok") or off_one:
            failures.append(
                {
                    "team": team,
                    "named_rush_share_sum": rush,
                    "named_target_share_sum": tgt,
                    "modeled_rush_plus_other": modeled_r,
                    "modeled_target_plus_other": modeled_t,
                    "share_ok": bool(summary.get("ok")),
                    "named_hard_max": SHARE_NAMED_HARD_MAX,
                }
            )
    return failures


def _sample_engine_web_agreement(
    payload: Mapping[str, Any],
    *,
    path: Path,
    teams: Sequence[str],
    sample_n: int = 8,
) -> List[Dict[str, Any]]:
    """Re-read the JSON as the web BFF would and compare QB1 player_id samples."""
    try:
        web_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [{"error": f"web_reload_failed: {exc}"}]

    eng_rows = _skill_rows(payload)
    web_rows = _skill_rows(web_payload)
    sample = list(teams)[:sample_n]
    mismatches: List[Dict[str, Any]] = []

    eng_snap = str(payload.get("snapshot_id") or "")
    web_snap = str(web_payload.get("snapshot_id") or "")
    if eng_snap and web_snap and eng_snap != web_snap:
        mismatches.append(
            {
                "field": "snapshot_id",
                "engine": eng_snap,
                "web": web_snap,
            }
        )

    for team in sample:
        def qb1(rows: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
            hits = [
                r
                for r in rows
                if r["team"] == team and r["position"] == "QB" and int(r["depth_order"]) == 1
            ]
            return hits[0] if hits else None

        e = qb1(eng_rows)
        w = qb1(web_rows)
        if e is None or w is None:
            mismatches.append({"team": team, "engine": e, "web": w, "reason": "missing_qb1"})
            continue
        if e.get("player_id") != w.get("player_id") or e.get("player_name") != w.get(
            "player_name"
        ):
            mismatches.append(
                {
                    "team": team,
                    "engine": {
                        "player_id": e.get("player_id"),
                        "player_name": e.get("player_name"),
                    },
                    "web": {
                        "player_id": w.get("player_id"),
                        "player_name": w.get("player_name"),
                    },
                }
            )
    return mismatches


def assert_depth_sot_integrity(
    payload: Mapping[str, Any],
    *,
    pack_path: Optional[Path] = None,
    **kwargs: Any,
) -> IntegrityReport:
    report = validate_depth_sot_pack(payload, pack_path=pack_path, **kwargs)
    if not report.ok:
        msgs = "; ".join(f"{f.check}: {f.message}" for f in report.findings)
        raise DataIntegrityError(
            f"Depth SoT integrity FAILED snapshot_id={report.snapshot_id}: {msgs}"
        )
    return report


def build_run_lineage(
    *,
    snapshot_id: str,
    engine_version: str = ENGINE_VERSION,
    pack_sha256: str = "",
    roster_as_of: str = "",
    daily_intel_as_of: str = "",
    n_team_sims: Optional[int] = None,
    n_player_sims: Optional[int] = None,
    seed: Optional[int] = None,
    injury_paths_count: int = 0,
    run_config: Optional[Mapping[str, Any]] = None,
    deferred_gaps: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Lineage block attached to run_summary / survivor / game_query outputs."""
    cfg: Dict[str, Any] = dict(run_config or {})
    if n_team_sims is not None:
        cfg.setdefault("n_team_sims", n_team_sims)
    if n_player_sims is not None:
        cfg.setdefault("n_player_sims", n_player_sims)
    if seed is not None:
        cfg.setdefault("seed", seed)
    cfg.setdefault("injury_paths_count", injury_paths_count)
    return {
        "snapshot_id": snapshot_id,
        "engine_version": engine_version,
        "pack_sha256": pack_sha256,
        "roster_as_of": roster_as_of,
        "daily_intel_as_of": daily_intel_as_of,
        "run_config": cfg,
        "deferred_gaps": list(
            deferred_gaps
            or [
                "PlayerRole still keys sim math on synthetic player_key; GSIS joined at export/lineage only",
                "OL→EPA power remains stub (documented_not_magical); ol_roles tracked but not calibrated",
                "Fantasy season aggregates on web may omit lineage until board writers pass snapshot_id",
                "player_season_totals.json remains a bare list; lineage lives on sibling run_summary.json",
            ]
        ),
    }


def lineage_from_universe_meta(
    meta: Mapping[str, Any],
    *,
    engine_version: str = ENGINE_VERSION,
    n_team_sims: Optional[int] = None,
    n_player_sims: Optional[int] = None,
    seed: Optional[int] = None,
    injury_paths_count: int = 0,
) -> Dict[str, Any]:
    return build_run_lineage(
        snapshot_id=str(meta.get("snapshot_id") or ""),
        engine_version=engine_version,
        pack_sha256=str(meta.get("pack_sha256") or meta.get("depth_sha256") or ""),
        roster_as_of=str(meta.get("roster_as_of") or meta.get("depth_as_of") or ""),
        daily_intel_as_of=str(meta.get("daily_intel_as_of") or ""),
        n_team_sims=n_team_sims,
        n_player_sims=n_player_sims,
        seed=seed,
        injury_paths_count=injury_paths_count,
    )


def packaged_depth_path(season: int = 2026) -> Path:
    """Active packaged depth path for ``season`` (raises if unknown)."""
    mapping = {
        2026: _PACKAGE_DATA_DIR / "nfl_depth_chart_2026_w1.json",
    }
    path = mapping.get(int(season))
    if path is None:
        raise FileNotFoundError(f"No packaged depth mapping for season={season}")
    return path


def validate_packaged_depth_file(
    season: int = 2026,
    *,
    reference_date: Optional[date] = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    require_archive: bool = False,
) -> IntegrityReport:
    """Load active packaged depth for ``season`` and run the gate."""
    path = packaged_depth_path(season)
    if not path.is_file():
        raise FileNotFoundError(f"No packaged depth for season={season}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Allow structural pass when snapshot_id was just ensured in-memory for CI.
    if not payload.get("snapshot_id"):
        payload = ensure_snapshot_metadata(payload, pack_path=path)
    report = validate_depth_sot_pack(
        payload,
        pack_path=path,
        reference_date=reference_date,
        max_age_days=max_age_days,
    )
    if require_archive:
        snap = SNAPSHOTS_DIR / f"{report.snapshot_id}.json"
        if not snap.is_file():
            report.findings.append(
                IntegrityFinding(
                    check="snapshot_archive",
                    severity="fail",
                    message=f"Missing archive {snap.name}",
                )
            )
            report.ok = False
            report.checks_run.append("snapshot_archive")
    return report
