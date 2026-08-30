"""Shared error-formatting helper — keeps diagnostic detail without leaking secrets."""

from __future__ import annotations
import re

_REDACT_PATTERNS = [
    re.compile(r"Bearer [^\s\\'\"]+"),
    re.compile(r"gsk_[A-Za-z0-9]+"),
]


def safe_error_detail(e: Exception) -> str:
    """Format an exception with its cause chain, redacting anything that looks like a credential."""
    detail = f"{e!r}"
    if e.__cause__:
        detail += f" caused by {e.__cause__!r}"
    for pattern in _REDACT_PATTERNS:
        detail = pattern.sub("[REDACTED]", detail)
    return detail
