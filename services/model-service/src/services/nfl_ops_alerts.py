"""NFL ops alerting (webhook + durable event log)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from sqlalchemy import text

from src.db import SessionLocal

log = logging.getLogger("kosedge.nfl_ops_alerts")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def alert_webhook_url() -> str:
    return (
        (os.getenv("NFL_ALERT_WEBHOOK_URL") or "").strip()
        or (os.getenv("OPS_ALERT_WEBHOOK_URL") or "").strip()
        or (os.getenv("MLB_ALERT_WEBHOOK_URL") or "").strip()
    )


def persist_nfl_alert_event(
    *,
    alert_type: str,
    severity: str,
    payload: Dict[str, Any],
    webhook_delivered: bool,
) -> None:
    session = SessionLocal()
    try:
        session.execute(
            text(
                """
                INSERT INTO nfl_ops_alert_events (
                  alert_type, severity, source, payload, webhook_delivered, created_at
                ) VALUES (
                  :alert_type, :severity, 'nfl', CAST(:payload AS jsonb), :webhook_delivered, :created_at
                )
                """
            ),
            {
                "alert_type": alert_type,
                "severity": severity,
                "payload": json.dumps(payload),
                "webhook_delivered": webhook_delivered,
                "created_at": _now_utc(),
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        log.exception("Failed persisting NFL alert event")
    finally:
        session.close()


def send_nfl_alert(
    *,
    alert_type: str,
    severity: str,
    payload: Dict[str, Any],
) -> bool:
    url = alert_webhook_url()
    delivered = False
    if url:
        body = {
            "alert_type": alert_type,
            "severity": severity,
            "payload": payload,
            "service": "model-service",
            "sport": "nfl",
            "at": _now_utc().isoformat(),
        }
        try:
            response = requests.post(url, json=body, timeout=8)
            response.raise_for_status()
            delivered = True
        except Exception:
            log.exception("Failed sending NFL alert webhook")
    persist_nfl_alert_event(
        alert_type=alert_type,
        severity=severity,
        payload=payload,
        webhook_delivered=delivered,
    )
    return delivered
