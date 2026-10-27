"""Alert delivery for missing / stale / partial W8 coverage.

Disabled by default. Webhook delivery is fail-closed while Odds hold is on
(H-1a/H-1c). File sink still writes into the hash-chained bundle.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.cadence import CoverageAlert
from src.services.nfl_w8_capture.hold import odds_api_hold_is_on
from src.services.nfl_w8_capture.store import ALERTS_NAME, BundleStore

ENV_ALERTS_ENABLED = "NFL_W8_ALERTS_ENABLED"
ENV_ALERT_WEBHOOK = "NFL_W8_ALERT_WEBHOOK_URL"


@dataclass
class AlertDelivery:
    kind: str
    channel: str
    status: str
    detail: str
    webhook_attempted: bool = False


def alerts_enabled(env: Optional[Mapping[str, str]] = None) -> bool:
    source = env if env is not None else os.environ
    raw = str(source.get(ENV_ALERTS_ENABLED) or "").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def webhook_url(env: Optional[Mapping[str, str]] = None) -> str:
    source = env if env is not None else os.environ
    return str(source.get(ENV_ALERT_WEBHOOK) or "").strip()


def deliver_alert(
    alert: CoverageAlert,
    store: BundleStore,
    *,
    actor: str = "nfl_w8_capture",
    env: Optional[Mapping[str, str]] = None,
) -> AlertDelivery:
    payload = asdict(alert)
    store.append_chained_jsonl(
        ALERTS_NAME,
        {"alert": payload},
        actor=actor,
        note=f"alert:{alert.kind}:{alert.game_id}:{alert.market}",
    )

    if alert.kind == "ok":
        return AlertDelivery(
            kind=alert.kind,
            channel="bundle",
            status="logged",
            detail="ok coverage; no page",
        )

    if not alerts_enabled(env):
        return AlertDelivery(
            kind=alert.kind,
            channel="bundle",
            status="disabled",
            detail=f"{ENV_ALERTS_ENABLED} default off; logged to {ALERTS_NAME}",
        )

    if odds_api_hold_is_on(env):
        return AlertDelivery(
            kind=alert.kind,
            channel="webhook",
            status="hold_blocked",
            detail="H-1a/H-1c Odds hold: webhook fail-closed; file sink only",
            webhook_attempted=False,
        )

    # Hold is always on in this draft; keep a dead branch that still never
    # posts unless a future hold-lift changes odds_api_hold_is_on.
    url = webhook_url(env)
    if not url:
        return AlertDelivery(
            kind=alert.kind,
            channel="webhook",
            status="no_webhook",
            detail=f"{ENV_ALERT_WEBHOOK} unset",
        )
    return AlertDelivery(
        kind=alert.kind,
        channel="webhook",
        status="refused",
        detail="draft will not POST; hold path is the only live branch",
        webhook_attempted=False,
    )
