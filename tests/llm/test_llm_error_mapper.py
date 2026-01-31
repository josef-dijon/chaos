"""Tests for LLM error mapping helpers."""

from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel, ValidationError

from chaos.domain.exceptions import ApiKeyError, ContextLengthError, RateLimitError
from chaos.llm.llm_error_mapper import (
    _extract_error_payload,
    _is_context_length_payload,
    is_known_llm_error,
    map_llm_error,
)
from chaos.llm.response_status import ResponseStatus


class _SchemaModel(BaseModel):
    value: int


def test_map_llm_error_validation_error() -> None:
    """Validation errors map to schema_error."""
    with pytest.raises(ValidationError) as exc_info:
        _SchemaModel.model_validate({"value": "nope"})

    mapping = map_llm_error(exc_info.value)

    assert mapping.reason == "schema_error"
    assert mapping.status == ResponseStatus.SEMANTIC_ERROR


def test_map_llm_error_http_status_api_key() -> None:
    """HTTP 401/403 map to API key errors."""
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(401, request=request)
    error = httpx.HTTPStatusError("auth", request=request, response=response)

    mapping = map_llm_error(error)

    assert mapping.reason == "api_key_error"
    assert mapping.status == ResponseStatus.CONFIG_ERROR
    assert mapping.error_type == ApiKeyError


def test_map_llm_error_http_status_rate_limit() -> None:
    """HTTP 429 maps to rate limit errors."""
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(429, request=request)
    error = httpx.HTTPStatusError("rate limit", request=request, response=response)

    mapping = map_llm_error(error)

    assert mapping.reason == "rate_limit_error"
    assert mapping.status == ResponseStatus.MECHANICAL_ERROR
    assert mapping.error_type == RateLimitError


def test_map_llm_error_http_status_context_payload() -> None:
    """Context-length payloads map to capacity errors."""
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(
        400,
        request=request,
        json={"error": {"code": "context_length_exceeded"}},
    )
    error = httpx.HTTPStatusError("context", request=request, response=response)

    mapping = map_llm_error(error)

    assert mapping.reason == "context_length_error"
    assert mapping.status == ResponseStatus.CAPACITY_ERROR


def test_map_llm_error_specific_exceptions() -> None:
    """Explicit error types map to stable reasons."""
    mapping = map_llm_error(ApiKeyError("bad key"))
    assert mapping.reason == "api_key_error"

    mapping = map_llm_error(RateLimitError("slow down"))
    assert mapping.reason == "rate_limit_error"

    mapping = map_llm_error(ContextLengthError("too long"))
    assert mapping.reason == "context_length_error"


def test_map_llm_error_text_fallbacks() -> None:
    """Text-only errors still map to stable categories."""
    mapping = map_llm_error(Exception("rate limit hit"))
    assert mapping.reason == "rate_limit_error"

    mapping = map_llm_error(Exception("API key invalid"))
    assert mapping.reason == "api_key_error"

    mapping = map_llm_error(Exception("something else"))
    assert mapping.reason == "llm_execution_failed"


def test_is_known_llm_error_request_error() -> None:
    """Request errors are treated as known LLM errors."""
    request = httpx.Request("POST", "https://example.com")
    error = httpx.RequestError("boom", request=request)

    assert is_known_llm_error(error) is True


def test_extract_error_payload_invalid_json() -> None:
    """Invalid JSON payloads return empty dicts."""
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(400, request=request, content=b"not json")
    error = httpx.HTTPStatusError("bad", request=request, response=response)

    assert _extract_error_payload(error) == {}


def test_is_context_length_payload_message() -> None:
    """Message-based context detection returns True."""
    payload = {"error": {"message": "Maximum context length exceeded"}}

    assert _is_context_length_payload(payload) is True
