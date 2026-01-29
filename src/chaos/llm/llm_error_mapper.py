from dataclasses import dataclass
from typing import Any, Dict

from chaos.domain.exceptions import (
    ApiKeyError,
    ContextLengthError,
    RateLimitError,
    SchemaError,
)
from chaos.llm.response_status import ResponseStatus
from chaos.llm.stable_transport import StableTransportError


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

    details = {"error": str(error)}
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
    if isinstance(error, StableTransportError):
        return LLMErrorMapping(
            status=ResponseStatus.MECHANICAL_ERROR,
            reason="transport_error",
            error_type=StableTransportError,
            details=details,
        )

    error_name = error.__class__.__name__.lower()
    error_message = str(error).lower()
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
    if "context" in error_name or "context" in error_message:
        return LLMErrorMapping(
            status=ResponseStatus.CAPACITY_ERROR,
            reason="context_length_error",
            error_type=ContextLengthError,
            details=details,
        )

    return LLMErrorMapping(
        status=ResponseStatus.MECHANICAL_ERROR,
        reason="llm_execution_failed",
        error_type=type(error),
        details=details,
    )
