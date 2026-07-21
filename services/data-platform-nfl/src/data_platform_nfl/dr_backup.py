"""Enterprise DR backups: compressed pg_dump, verify, retention, optional remote upload."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote

from sqlalchemy import text

from .db import SessionLocal, DATABASE_URL
from .source_matrix import source_matrix_payload


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def parse_database_url(url: Optional[str] = None) -> Dict[str, str]:
    raw = (url or os.environ.get("DATABASE_URL") or DATABASE_URL).strip()
    # sqlalchemy dialect prefixes
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://", "postgres://"):
        if raw.startswith(prefix):
            raw = "postgresql://" + raw[len(prefix) :]
            break
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
        "dbname": (parsed.path or "/kosedge").lstrip("/") or "kosedge",
    }


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _pg_env(db: Dict[str, str]) -> Dict[str, str]:
    env = os.environ.copy()
    if db["password"]:
        env["PGPASSWORD"] = db["password"]
    return env


def _find_pg_bin(name: str) -> str:
    configured = os.getenv(f"NFL_PG_{name.upper()}_BIN") or os.getenv("NFL_PG_BIN_DIR")
    if configured:
        candidate = Path(configured)
        if candidate.is_dir():
            path = candidate / name
            if path.exists():
                return str(path)
        elif candidate.exists():
            return str(candidate)
    which = shutil.which(name)
    if which:
        return which
    # Homebrew PostgreSQL@16 common path
    brew = Path(f"/usr/local/opt/postgresql@16/bin/{name}")
    if brew.exists():
        return str(brew)
    brew_opt = Path(f"/opt/homebrew/opt/postgresql@16/bin/{name}")
    if brew_opt.exists():
        return str(brew_opt)
    raise FileNotFoundError(f"{name} not found on PATH; set NFL_PG_BIN_DIR")


def default_backup_dir() -> Path:
    configured = os.getenv("NFL_DR_BACKUP_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (_repo_root() / "data" / "backups" / "nfl").resolve()


def run_pg_dump(
    *,
    output_path: Path,
    db: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    db_info = db or parse_database_url()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pg_dump = _find_pg_bin("pg_dump")
    cmd = [
        pg_dump,
        "--format=custom",
        "--compress=9",
        "--no-owner",
        "--no-acl",
        "--verbose",
        "--host",
        db_info["host"],
        "--port",
        db_info["port"],
        "--username",
        db_info["user"],
        "--dbname",
        db_info["dbname"],
        "--file",
        str(output_path),
    ]
    proc = subprocess.run(
        cmd,
        env=_pg_env(db_info),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"pg_dump failed ({proc.returncode}): {proc.stderr[-4000:] or proc.stdout[-4000:]}"
        )
    checksum = _sha256_file(output_path)
    return {
        "dump_path": str(output_path),
        "dump_bytes": output_path.stat().st_size,
        "dump_checksum": checksum,
        "pg_dump_bin": pg_dump,
    }


def verify_pg_dump(
    *,
    dump_path: Path,
    db: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Restore into an ephemeral verify database and smoke-check critical tables."""
    db_info = db or parse_database_url()
    pg_restore = _find_pg_bin("pg_restore")
    psql = _find_pg_bin("psql")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    verify_db = f"kosedge_dr_verify_{stamp}"
    env = _pg_env(db_info)
    created = False
    try:
        create = subprocess.run(
            [
                psql,
                "--host",
                db_info["host"],
                "--port",
                db_info["port"],
                "--username",
                db_info["user"],
                "--dbname",
                "postgres",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                f'CREATE DATABASE "{verify_db}"',
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if create.returncode != 0:
            raise RuntimeError(f"verify DB create failed: {create.stderr}")
        created = True
        restore = subprocess.run(
            [
                pg_restore,
                "--host",
                db_info["host"],
                "--port",
                db_info["port"],
                "--username",
                db_info["user"],
                "--dbname",
                verify_db,
                "--no-owner",
                "--no-acl",
                str(dump_path),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        # pg_restore can return 1 for non-fatal warnings; treat only hard failures.
        if restore.returncode not in (0, 1):
            raise RuntimeError(f"pg_restore failed: {restore.stderr[-4000:]}")

        checks_sql = """
        SELECT json_build_object(
          'schedules', (SELECT COUNT(*) FROM nfl_dp_schedules),
          'pbp', (SELECT COUNT(*) FROM nfl_dp_play_by_play),
          'raw_objects', (SELECT COUNT(*) FROM nfl_dp_raw_objects),
          'player_stats', (SELECT COUNT(*) FROM nfl_dp_player_game_stats),
          'injuries', (SELECT COUNT(*) FROM nfl_dp_injuries)
        );
        """
        probe = subprocess.run(
            [
                psql,
                "--host",
                db_info["host"],
                "--port",
                db_info["port"],
                "--username",
                db_info["user"],
                "--dbname",
                verify_db,
                "-v",
                "ON_ERROR_STOP=1",
                "-t",
                "-A",
                "-c",
                checks_sql,
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            raise RuntimeError(f"verify probe failed: {probe.stderr}")
        counts = json.loads(probe.stdout.strip() or "{}")
        required_positive = ["schedules", "pbp", "raw_objects"]
        missing = [k for k in required_positive if int(counts.get(k) or 0) <= 0]
        status = "ok" if not missing else "failed"
        return {
            "status": status,
            "verify_db": verify_db,
            "table_counts": counts,
            "missing_required": missing,
            "pg_restore_returncode": restore.returncode,
        }
    finally:
        if created:
            subprocess.run(
                [
                    psql,
                    "--host",
                    db_info["host"],
                    "--port",
                    db_info["port"],
                    "--username",
                    db_info["user"],
                    "--dbname",
                    "postgres",
                    "-c",
                    f'DROP DATABASE IF EXISTS "{verify_db}" WITH (FORCE)',
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )


def upload_dump_if_configured(dump_path: Path, *, checksum: str) -> Optional[str]:
    """Optional S3/R2 upload via AWS CLI when NFL_DR_REMOTE_URI is set.

    Example:
      NFL_DR_REMOTE_URI=s3://my-bucket/kosedge/nfl-dr
    Requires `aws` CLI + credentials in the environment.
    """
    remote_base = (os.getenv("NFL_DR_REMOTE_URI") or "").strip().rstrip("/")
    if not remote_base:
        return None
    aws = shutil.which("aws")
    if not aws:
        raise RuntimeError(
            "NFL_DR_REMOTE_URI is set but `aws` CLI was not found. "
            "Install AWS CLI or unset NFL_DR_REMOTE_URI for local-only backups."
        )
    remote_key = f"{remote_base}/{dump_path.name}"
    proc = subprocess.run(
        [aws, "s3", "cp", str(dump_path), remote_key, "--only-show-errors"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"remote upload failed: {proc.stderr or proc.stdout}")
    # sidecar checksum
    with tempfile.NamedTemporaryFile("w", suffix=".sha256", delete=False) as tmp:
        tmp.write(f"{checksum}  {dump_path.name}\n")
        sidecar = Path(tmp.name)
    try:
        subprocess.run(
            [aws, "s3", "cp", str(sidecar), f"{remote_key}.sha256", "--only-show-errors"],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        sidecar.unlink(missing_ok=True)
    return remote_key


def apply_retention(*, backup_dir: Path, keep: int) -> List[str]:
    keep = max(1, int(keep))
    dumps = sorted(backup_dir.glob("kosedge-nfl-*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed: List[str] = []
    for stale in dumps[keep:]:
        try:
            stale.unlink()
            sidecar = Path(str(stale) + ".sha256")
            if sidecar.exists():
                sidecar.unlink()
            removed.append(str(stale))
        except OSError:
            continue
    return removed


def _persist_backup_row(manifest: Dict[str, Any]) -> None:
    session = SessionLocal()
    try:
        session.execute(
            text(
                """
                INSERT INTO nfl_data_ownership_backups (
                  backup_key, artifact_dir, manifest, created_at,
                  backup_type, dump_path, dump_checksum, dump_bytes,
                  remote_uri, verify_status, verify_details
                ) VALUES (
                  :backup_key, :artifact_dir, CAST(:manifest AS jsonb), NOW(),
                  :backup_type, :dump_path, :dump_checksum, :dump_bytes,
                  :remote_uri, :verify_status, CAST(:verify_details AS jsonb)
                )
                ON CONFLICT (backup_key) DO UPDATE SET
                  artifact_dir = EXCLUDED.artifact_dir,
                  manifest = EXCLUDED.manifest,
                  backup_type = EXCLUDED.backup_type,
                  dump_path = EXCLUDED.dump_path,
                  dump_checksum = EXCLUDED.dump_checksum,
                  dump_bytes = EXCLUDED.dump_bytes,
                  remote_uri = EXCLUDED.remote_uri,
                  verify_status = EXCLUDED.verify_status,
                  verify_details = EXCLUDED.verify_details
                """
            ),
            {
                "backup_key": manifest["backup_key"],
                "artifact_dir": manifest.get("artifact_dir"),
                "manifest": json.dumps(manifest),
                "backup_type": manifest.get("backup_type", "pg_dump"),
                "dump_path": manifest.get("dump_path"),
                "dump_checksum": manifest.get("dump_checksum"),
                "dump_bytes": manifest.get("dump_bytes"),
                "remote_uri": manifest.get("remote_uri"),
                "verify_status": manifest.get("verify_status"),
                "verify_details": json.dumps(manifest.get("verify_details") or {}),
            },
        )
        session.commit()
    finally:
        session.close()


def run_dr_backup(
    *,
    verify: bool = True,
    upload: bool = True,
    keep: Optional[int] = None,
    backup_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Full warehouse DR backup suitable for subscription ops."""
    out_dir = Path(backup_dir).expanduser().resolve() if backup_dir else default_backup_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_key = f"nfl-dr-{stamp}"
    dump_path = out_dir / f"kosedge-nfl-{stamp}.dump"

    dump_meta = run_pg_dump(output_path=dump_path)
    checksum_path = Path(str(dump_path) + ".sha256")
    checksum_path.write_text(f"{dump_meta['dump_checksum']}  {dump_path.name}\n", encoding="utf-8")

    verify_details: Dict[str, Any] = {"skipped": not verify}
    verify_status = "skipped"
    if verify:
        verify_details = verify_pg_dump(dump_path=dump_path)
        verify_status = str(verify_details.get("status") or "failed")

    remote_uri = None
    if upload:
        remote_uri = upload_dump_if_configured(dump_path, checksum=dump_meta["dump_checksum"])

    keep_n = int(keep if keep is not None else os.getenv("NFL_DR_BACKUP_KEEP", "3"))
    removed = apply_retention(backup_dir=out_dir, keep=keep_n)

    manifest: Dict[str, Any] = {
        "backup_key": backup_key,
        "backup_type": "pg_dump",
        "created_at": _now_iso(),
        "artifact_dir": str(out_dir),
        "dump_path": dump_meta["dump_path"],
        "dump_bytes": dump_meta["dump_bytes"],
        "dump_checksum": dump_meta["dump_checksum"],
        "checksum_path": str(checksum_path),
        "remote_uri": remote_uri,
        "verify_status": verify_status,
        "verify_details": verify_details,
        "retention": {"keep": keep_n, "removed": removed},
        "source_matrix_version": source_matrix_payload()["version"],
        "database": parse_database_url()["dbname"],
    }
    _persist_backup_row(manifest)

    if verify_status == "failed":
        raise RuntimeError(f"DR backup verify failed: {json.dumps(verify_details)}")
    return manifest
