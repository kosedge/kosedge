from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query names that must never appear in logs or exception text.
_SENSITIVE_QUERY_KEYS = frozenset({"apikey", "api_key", "key", "token"})

# Defense-in-depth for already-rendered text (HTTPError embeds the request URL).
# Ticket regex: ([?&](apiKey|api_key)=)[^&\s"']+ → \1***
_API_KEY_QUERY_RE = re.compile(
    r"""([?&](apiKey|api_key)=)[^&\s"']+""",
    flags=re.IGNORECASE,
)

_FILTER_NAME = "odds_credential_sanitize"


def sanitize_url(url: str, *, mask: str = "***") -> str:
    """Mask apiKey|api_key|key|token query values. Safe for log/error text."""
    if not url:
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return _API_KEY_QUERY_RE.sub(r"\1***", url)
    if not parts.query:
        return _API_KEY_QUERY_RE.sub(r"\1***", url)
    redacted: list[str] = []
    for raw_key, raw_val in parse_qsl(parts.query, keep_blank_values=True):
        if raw_key.lower() in _SENSITIVE_QUERY_KEYS:
            redacted.append(f"{urlencode({raw_key: ''})[:-1]}={mask}")
        else:
            redacted.append(urlencode([(raw_key, raw_val)]))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, "&".join(redacted), parts.fragment)
    )


def sanitize_log_text(text: str) -> str:
    """Regex-mask apiKey/api_key query values in free-form log / traceback text."""
    if not text:
        return text
    return _API_KEY_QUERY_RE.sub(r"\1***", text)


def _sanitize_arg(value: Any) -> Any:
    if isinstance(value, str):
        if "://" in value and " " not in value.strip():
            return sanitize_url(value)
        return sanitize_log_text(value)
    if isinstance(value, BaseException):
        rendered = str(value)
        masked = sanitize_log_text(rendered)
        return masked if masked != rendered else value
    return value


def _sanitize_args(args: Any) -> Any:
    if args is None:
        return args
    if isinstance(args, dict):
        return {key: _sanitize_arg(val) for key, val in args.items()}
    if isinstance(args, tuple):
        return tuple(_sanitize_arg(item) for item in args)
    return _sanitize_arg(args)


class OddsCredentialLogFilter(logging.Filter):
    """Mask Odds API query credentials in record.msg / args / exc_text."""

    def __init__(self) -> None:
        super().__init__(name=_FILTER_NAME)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_log_text(record.msg)
        if record.args:
            record.args = _sanitize_args(record.args)
        if record.exc_info and not record.exc_text:
            try:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            except Exception:
                record.exc_text = None
        if record.exc_text:
            record.exc_text = sanitize_log_text(record.exc_text)
        return True


def _has_credential_filter(target: logging.Logger | logging.Handler) -> bool:
    return any(isinstance(item, OddsCredentialLogFilter) for item in target.filters)


def install_odds_credential_log_filter() -> OddsCredentialLogFilter:
    """Idempotent install on root + Celery loggers and their handlers."""
    filt = OddsCredentialLogFilter()
    logger_names = (
        "",
        "celery",
        "celery.task",
        "celery.worker",
        "celery.redirected",
        "celery.app.trace",
    )
    for name in logger_names:
        logger = logging.getLogger(name) if name else logging.getLogger()
        if not _has_credential_filter(logger):
            logger.addFilter(filt)
        for handler in logger.handlers:
            if not _has_credential_filter(handler):
                handler.addFilter(filt)
    last_resort = getattr(logging, "lastResort", None)
    if last_resort is not None and not _has_credential_filter(last_resort):
        last_resort.addFilter(filt)
    return filt
