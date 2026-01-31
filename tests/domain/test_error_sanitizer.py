"""Tests for error sanitization utilities."""

from __future__ import annotations

from chaos.domain.error_sanitizer import (
    REDACTED_VALUE,
    build_exception_details,
    sanitize_error_details,
    sanitize_text,
)


def test_sanitize_text_redacts_tokens_and_truncates() -> None:
    """Redacts token-like strings and truncates long text."""
    text = "sk-1234567890 " + ("x" * 300)

    sanitized = sanitize_text(text, max_length=32)

    assert REDACTED_VALUE in sanitized
    assert sanitized.endswith("...[truncated]")


def test_sanitize_error_details_redacts_sensitive_keys() -> None:
    """Redacts sensitive keys while preserving safe values."""
    details = {
        "api_key": "sk-1234567890",
        "info": {"note": "ok", "count": 2},
        "items": ["ok", {"token": "abc"}, "third"],
    }

    sanitized = sanitize_error_details(details)

    assert sanitized["api_key"] == REDACTED_VALUE
    assert sanitized["info"]["note"] == "ok"
    assert sanitized["items"][0] == "ok"
    assert sanitized["items"][1]["token"] == REDACTED_VALUE
    assert sanitized["items"][2] == "third"


def test_sanitize_error_details_caps_list_items() -> None:
    """Caps list sizes to avoid unbounded details."""
    details = {"items": [1, 2, 3]}

    sanitized = sanitize_error_details(details, max_items=2)

    assert sanitized["items"] == [1, 2, REDACTED_VALUE]


def test_build_exception_details_includes_cause() -> None:
    """Includes error and cause metadata when present."""
    try:
        try:
            raise ValueError("inner error")
        except ValueError as exc:
            raise RuntimeError("outer error") from exc
    except RuntimeError as exc:
        details = build_exception_details(exc)

    assert details["error_class"] == "RuntimeError"
    assert "outer error" in details.get("message", "")
    assert details["cause_class"] == "ValueError"
    assert "inner error" in details.get("cause_message", "")
