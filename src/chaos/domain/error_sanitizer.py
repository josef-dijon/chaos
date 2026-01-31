"""Sanitize error details to avoid leaking sensitive data."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Mapping

REDACTED_VALUE = "<redacted>"
DEFAULT_MAX_STRING_LENGTH = 256
DEFAULT_MAX_ITEMS = 25
DEFAULT_MAX_DEPTH = 3

_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "token",
    "secret",
    "password",
    "prompt",
    "messages",
    "message",
    "content",
    "input",
    "output",
    "completion",
    "payload",
    "schema",
)

_TOKEN_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{10,}"),
    re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{10,}"),
)


def sanitize_text(value: str, max_length: int = DEFAULT_MAX_STRING_LENGTH) -> str:
    """Redact secrets and cap a string value.

    Args:
        value: Input text value.
        max_length: Maximum length of the returned string.

    Returns:
        A redacted, length-capped string.
    """

    sanitized = _redact_tokens(value)
    if len(sanitized) <= max_length:
        return sanitized
    return f"{sanitized[:max_length]}...[truncated]"


def sanitize_error_details(
    details: Mapping[str, Any],
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_string_length: int = DEFAULT_MAX_STRING_LENGTH,
) -> Dict[str, Any]:
    """Sanitize a structured error details mapping.

    Args:
        details: Mapping of error details to sanitize.
        max_depth: Maximum recursion depth.
        max_items: Maximum items per collection.
        max_string_length: Maximum length for string values.

    Returns:
        A sanitized error details dictionary.
    """

    return _sanitize_value(
        details,
        depth=max_depth,
        max_items=max_items,
        max_string_length=max_string_length,
    )


def build_exception_details(
    error: Exception,
    max_string_length: int = DEFAULT_MAX_STRING_LENGTH,
) -> Dict[str, Any]:
    """Build a sanitized error detail mapping from an exception.

    Args:
        error: Exception to summarize.
        max_string_length: Maximum length for message fields.

    Returns:
        A sanitized error detail dictionary.
    """

    details: Dict[str, Any] = {
        "error_class": error.__class__.__name__,
    }
    message = str(error)
    if message:
        details["message"] = sanitize_text(message, max_length=max_string_length)
    cause = getattr(error, "__cause__", None)
    if isinstance(cause, Exception):
        details["cause_class"] = cause.__class__.__name__
        cause_message = str(cause)
        if cause_message:
            details["cause_message"] = sanitize_text(
                cause_message, max_length=max_string_length
            )
    return details


def _redact_tokens(text: str) -> str:
    """Redact common secret/token patterns from text."""

    redacted = text
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub(REDACTED_VALUE, redacted)
    return redacted


def _is_sensitive_key(key: str) -> bool:
    """Return True when a key is likely to contain sensitive data."""

    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _sanitize_iterable(
    items: Iterable[Any],
    depth: int,
    max_items: int,
    max_string_length: int,
) -> list[Any]:
    """Sanitize list-like values with item caps."""

    sanitized: list[Any] = []
    for index, item in enumerate(items):
        if index >= max_items:
            sanitized.append(REDACTED_VALUE)
            break
        sanitized.append(
            _sanitize_value(
                item,
                depth=depth - 1,
                max_items=max_items,
                max_string_length=max_string_length,
            )
        )
    return sanitized


def _sanitize_value(
    value: Any,
    depth: int,
    max_items: int,
    max_string_length: int,
) -> Any:
    """Sanitize nested values recursively."""

    if depth <= 0:
        return REDACTED_VALUE
    if isinstance(value, str):
        return sanitize_text(value, max_length=max_string_length)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, Mapping):
        sanitized: Dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                sanitized["_truncated"] = True
                break
            key_text = str(key)
            if _is_sensitive_key(key_text):
                sanitized[key_text] = REDACTED_VALUE
            else:
                sanitized[key_text] = _sanitize_value(
                    item,
                    depth=depth - 1,
                    max_items=max_items,
                    max_string_length=max_string_length,
                )
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return _sanitize_iterable(
            list(value),
            depth=depth,
            max_items=max_items,
            max_string_length=max_string_length,
        )
    return sanitize_text(str(value), max_length=max_string_length)
