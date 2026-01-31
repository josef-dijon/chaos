from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from chaos.config import Config
from chaos.domain.exceptions import (
    ApiKeyError,
    ContextLengthError,
    RateLimitError,
    SchemaError,
)
from chaos.domain.llm_primitive import LLMPrimitive
from chaos.domain.messages import Request, Response
from chaos.domain.policy import BubblePolicy
from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_response import LLMResponse
from chaos.llm.response_status import ResponseStatus
from chaos.stats.in_memory_block_stats_store import InMemoryBlockStatsStore
from chaos.stats.store_registry import set_default_store


class MockSchema(BaseModel):
    response: str


class StubLLMService:
    """Deterministic LLMService stub for LLMPrimitive tests."""

    def __init__(
        self,
        response: LLMResponse,
        capture: dict | None = None,
    ) -> None:
        self._response = response
        self._capture = capture

    def execute(self, request: LLMRequest) -> LLMResponse:
        if self._capture is not None:
            api_key = request.api_key
            if isinstance(api_key, SecretStr):
                self._capture["api_key"] = api_key.get_secret_value()
            else:
                self._capture["api_key"] = api_key
            self._capture["api_base"] = request.api_base
            self._capture["model"] = request.model
            self._capture["messages"] = request.messages
        return self._response


def test_llm_primitive_initialization():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="You are a bot",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.success(data={"response": "ok"}, raw_output=None)
        ),
    )
    assert block.name == "test_llm"
    assert block.state.name == "READY"


def test_llm_primitive_happy_path():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.success(data={"response": "hello"}, raw_output=None)
        ),
    )
    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert response.data == {"response": "hello"}


def test_llm_primitive_schema_error_policies():
    policy_block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.failure(
                status=ResponseStatus.SEMANTIC_ERROR,
                reason="schema_error",
                error_type=SchemaError,
                error_details={"error": "bad"},
            )
        ),
    )

    # Verify policy stack for SchemaError
    policies = policy_block.get_policy_stack(SchemaError)
    assert policies == [BubblePolicy()]

    response = policy_block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == SchemaError
    assert response.reason == "schema_error"


def test_llm_primitive_rate_limit_policies():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.failure(
                status=ResponseStatus.MECHANICAL_ERROR,
                reason="rate_limit_error",
                error_type=RateLimitError,
                error_details={"error": "429"},
            )
        ),
    )

    policies = block.get_policy_stack(RateLimitError)
    assert policies == [BubblePolicy()]


def test_llm_primitive_auth_error_policies():
    policy_block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.failure(
                status=ResponseStatus.CONFIG_ERROR,
                reason="api_key_error",
                error_type=ApiKeyError,
                error_details={"error": "Invalid API Key"},
            )
        ),
    )

    policies = policy_block.get_policy_stack(ApiKeyError)
    assert len(policies) == 1
    assert policies[0] == BubblePolicy()

    response = policy_block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == ApiKeyError
    assert response.reason == "api_key_error"


def test_llm_primitive_rate_limit_mapping():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.failure(
                status=ResponseStatus.MECHANICAL_ERROR,
                reason="rate_limit_error",
                error_type=RateLimitError,
                error_details={"error": "429 Too Many Requests"},
            )
        ),
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == RateLimitError
    assert response.reason == "rate_limit_error"


def test_llm_primitive_includes_api_key():
    captured: dict = {}
    config = Config.model_validate(
        {"openai_api_key": "test-key", "litellm_use_proxy": False}
    )
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        config=config,
        llm_service=StubLLMService(
            LLMResponse.success(data={"response": "hello"}, raw_output=None),
            capture=captured,
        ),
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert captured["api_key"] == "test-key"


def test_llm_primitive_accepts_dict_content():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.success(data={"response": "hello"}, raw_output=None)
        ),
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert response.data == {"response": "hello"}


def test_llm_primitive_invalid_payload_returns_failure():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.success(data={"response": "ok"}, raw_output=None)
        ),
    )

    response = block.execute(Request(payload={"unexpected": "value"}))

    assert response.success() is False
    assert response.reason == "invalid_payload"
    assert response.error_type == SchemaError


def test_llm_primitive_context_length_mapping():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.failure(
                status=ResponseStatus.CAPACITY_ERROR,
                reason="context_length_error",
                error_type=ContextLengthError,
                error_details={"error": "context length exceeded"},
            )
        ),
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.reason == "context_length_error"
    assert response.error_type == ContextLengthError


def test_llm_primitive_estimate_execution_prior() -> None:
    """Ensure LLMPrimitive returns a prior estimate on cold start."""

    store = InMemoryBlockStatsStore()
    set_default_store(store)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.success(data={"response": "ok"}, raw_output=None)
        ),
    )

    estimate = block.estimate_execution(Request(payload={"prompt": "hello"}))

    assert estimate.estimate_source == "prior"
    assert estimate.sample_size == 0
    assert estimate.expected_llm_calls == 1.0
    assert estimate.block_type == "llm_primitive"


def test_llm_primitive_estimate_execution_from_stats() -> None:
    """Ensure LLMPrimitive returns a stats-based estimate when data exists."""

    store = InMemoryBlockStatsStore()
    set_default_store(store)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=StubLLMService(
            LLMResponse.success(data={"response": "hello"}, raw_output=None)
        ),
    )
    block.execute(Request(payload={"prompt": "hello"}))
    estimate = block.estimate_execution(Request(payload={"prompt": "hello"}))

    assert estimate.estimate_source == "stats"
    assert estimate.sample_size == 1
    assert estimate.expected_llm_calls == 1.0


def test_llm_primitive_records_llm_usage_in_attempt_record() -> None:
    store = InMemoryBlockStatsStore()
    set_default_store(store)

    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        model="default-model",
        llm_service=StubLLMService(
            LLMResponse.success(
                data={"response": "ok"},
                raw_output=None,
                usage={"requests": 3, "input_tokens": 10, "output_tokens": 20},
            )
        ),
    )

    response = block.execute(Request(payload={"prompt": "hello"}))
    assert response.success() is True
    assert response.metadata["llm_calls"] == 3
    assert response.metadata["llm.retry_count"] == 2

    record = store._records[-1]
    assert record.model == "default-model"
    assert record.llm_calls == 3
    assert record.input_tokens == 10
    assert record.output_tokens == 20
