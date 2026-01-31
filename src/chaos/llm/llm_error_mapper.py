from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

try:
    from pydantic import ValidationError
except ImportError:  # pragma: no cover
    ValidationError = None  # type: ignore

try:
    from pydantic_ai import UnexpectedModelBehavior
except ImportError:  # pragma: no cover
    UnexpectedModelBehavior = None  # type: ignore

from chaos.domain.error_sanitizer import (
    build_exception_details,
    sanitize_error_details,
)
from chaos.domain.exceptions import (
    ApiKeyError,
    ContextLengthError,
    RateLimitError,
    SchemaError,
)
from chaos.llm.response_status import ResponseStatus


@dataclass(frozen=True)
class LLMErrorMapping:
    """Normalized error mapping for LLM failures."""

    status: ResponseStatus
    reason: str
    error_type: type[Exception]
    details: Dict[str, Any]


def map_llm_error(error: Exception) -> LLMErrorMapping:
    """Map an exception into a normalized LLM error mapping.

    Args:
        error: Exception raised during LLM execution.

    Returns:
        LLMErrorMapping describing the failure.
    """

    details: Dict[str, Any] = build_exception_details(error)
    cause = getattr(error, "__cause__", None)

    if ValidationError is not None and isinstance(error, ValidationError):
        return LLMErrorMapping(
            status=ResponseStatus.SEMANTIC_ERROR,
            reason="schema_error",
            error_type=SchemaError,
            details=details,
        )
    if (
        UnexpectedModelBehavior is not None
        and isinstance(error, UnexpectedModelBehavior)
        and ValidationError is not None
        and isinstance(cause, ValidationError)
    ):
        return LLMErrorMapping(
            status=ResponseStatus.SEMANTIC_ERROR,
            reason="schema_error",
            error_type=SchemaError,
            details=details,
        )

    if httpx is not None and isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        details["status_code"] = status_code
        if status_code == 429:
            return LLMErrorMapping(
                status=ResponseStatus.MECHANICAL_ERROR,
                reason="rate_limit_error",
                error_type=RateLimitError,
                details=details,
            )
        if status_code in (401, 403):
            return LLMErrorMapping(
                status=ResponseStatus.CONFIG_ERROR,
                reason="api_key_error",
                error_type=ApiKeyError,
                details=details,
            )
        if _is_context_length_payload(_extract_error_payload(error)):
            return LLMErrorMapping(
                status=ResponseStatus.CAPACITY_ERROR,
                reason="context_length_error",
                error_type=ContextLengthError,
                details=details,
            )
    if isinstance(error, SchemaError):
        return LLMErrorMapping(
            status=ResponseStatus.SEMANTIC_ERROR,
            reason="schema_error",
            error_type=SchemaError,
            details=details,
        )
    if isinstance(error, RateLimitError):
        return LLMErrorMapping(
            status=ResponseStatus.MECHANICAL_ERROR,
            reason="rate_limit_error",
            error_type=RateLimitError,
            details=details,
        )
    if isinstance(error, ApiKeyError):
        return LLMErrorMapping(
            status=ResponseStatus.CONFIG_ERROR,
            reason="api_key_error",
            error_type=ApiKeyError,
            details=details,
        )
    if isinstance(error, ContextLengthError):
        return LLMErrorMapping(
            status=ResponseStatus.CAPACITY_ERROR,
            reason="context_length_error",
            error_type=ContextLengthError,
            details=details,
        )
    details = sanitize_error_details(details)
    error_name = error.__class__.__name__.lower()
    error_message = str(error).lower()

    if (
        UnexpectedModelBehavior is not None
        and isinstance(error, UnexpectedModelBehavior)
        and (
            "validation" in error_message
            or "schema" in error_message
            or "json" in error_message
            or "output" in error_message
        )
    ):
        return LLMErrorMapping(
            status=ResponseStatus.SEMANTIC_ERROR,
            reason="schema_error",
            error_type=SchemaError,
            details=details,
        )
    if (
        "ratelimit" in error_name
        or "rate limit" in error_message
        or "429" in error_message
    ):
        return LLMErrorMapping(
            status=ResponseStatus.MECHANICAL_ERROR,
            reason="rate_limit_error",
            error_type=RateLimitError,
            details=details,
        )
    if (
        "authentication" in error_name
        or "auth" in error_name
        or "api key" in error_message
        or "apikey" in error_message
    ):
        return LLMErrorMapping(
            status=ResponseStatus.CONFIG_ERROR,
            reason="api_key_error",
            error_type=ApiKeyError,
            details=details,
        )
    return LLMErrorMapping(
        status=ResponseStatus.MECHANICAL_ERROR,
        reason="llm_execution_failed",
        error_type=type(error),
        details=details,
    )


def is_known_llm_error(error: Exception) -> bool:
    """Return True for errors that should be mapped as LLM failures."""

    cause = getattr(error, "__cause__", None)
    if ValidationError is not None and isinstance(error, ValidationError):
        return True
    if (
        UnexpectedModelBehavior is not None
        and isinstance(error, UnexpectedModelBehavior)
        and ValidationError is not None
        and isinstance(cause, ValidationError)
    ):
        return True
    if httpx is not None and isinstance(error, httpx.HTTPStatusError):
        return True
    if httpx is not None and isinstance(error, httpx.RequestError):
        return True
    return isinstance(
        error, (SchemaError, RateLimitError, ApiKeyError, ContextLengthError)
    )


def _extract_error_payload(error: "httpx.HTTPStatusError") -> Dict[str, Any]:
    """Extract error payload from an HTTP status error."""

    try:
        payload = error.response.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_context_length_payload(payload: Dict[str, Any]) -> bool:
    """Return True when payload indicates a context-length error."""

    error_info = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error_info, dict):
        return False
    code = error_info.get("code") or error_info.get("type")
    if isinstance(code, str):
        normalized = code.strip().lower()
        if normalized in {
            "context_length_exceeded",
            "context_window_exceeded",
            "context_length",
            "context_window",
        }:
            return True
    message = error_info.get("message")
    if isinstance(message, str):
        normalized = message.strip().lower()
        if "maximum context length" in normalized:
            return True
        if "context length exceeded" in normalized:
            return True
    return False
