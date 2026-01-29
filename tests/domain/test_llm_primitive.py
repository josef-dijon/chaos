from types import SimpleNamespace
from typing import Any, Type

import pytest
from pydantic import BaseModel

from chaos.config import Config
from chaos.domain.exceptions import (
    ApiKeyError,
    ContextLengthError,
    RateLimitError,
    SchemaError,
)
from chaos.domain.llm_primitive import LLMPrimitive
from chaos.domain.messages import Request, Response
from chaos.domain.policy import (
    BubblePolicy,
    RecoveryType,
    RepairPolicy,
    RetryPolicy,
)
from chaos.llm.llm_service import LLMService
from chaos.stats.in_memory_block_stats_store import InMemoryBlockStatsStore
from chaos.stats.store_registry import set_default_store


class MockSchema(BaseModel):
    response: str


def _fake_response(content: Any) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _make_llm_service() -> LLMService:
    """Build a no-retry LLM service for tests."""

    return LLMService(use_instructor=False, max_attempts=1, retry_exceptions=())


def test_llm_primitive_initialization():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="You are a bot",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )
    assert block.name == "test_llm"
    assert block.state.name == "READY"


def test_llm_primitive_happy_path(monkeypatch: pytest.MonkeyPatch):
    def fake_completion(**kwargs):
        return _fake_response('{"response":"hello"}')

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )
    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert response.data == {"response": "hello"}


def test_llm_primitive_schema_error_policies(monkeypatch: pytest.MonkeyPatch):
    policy_block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    # Verify policy stack for SchemaError
    policies = policy_block.get_policy_stack(SchemaError)
    assert len(policies) == 4
    assert policies[0].type == RecoveryType.RETRY
    assert policies[1].type == RecoveryType.REPAIR
    assert policies[2].type == RecoveryType.REPAIR
    assert policies[3].type == RecoveryType.BUBBLE

    # Trigger execution failure
    def fake_completion(**kwargs):
        return _fake_response("not-json")

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )
    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == SchemaError
    assert response.reason == "schema_error"


def test_llm_primitive_nudge_repairs_schema_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure semantic errors trigger a repair attempt inside execute."""

    calls = {"count": 0}

    def fake_completion(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _fake_response("not-json")
        return _fake_response('{"response":"fixed"}')

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
        max_repair_attempts=1,
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert response.data == {"response": "fixed"}
    assert calls["count"] == 2


def test_llm_primitive_rate_limit_policies():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    policies = block.get_policy_stack(RateLimitError)
    assert len(policies) == 2
    assert policies[0].type == RecoveryType.RETRY
    assert isinstance(policies[0], RetryPolicy)
    assert policies[0].delay_seconds == 2.0
    assert policies[1].type == RecoveryType.BUBBLE


def test_llm_primitive_auth_error_policies(monkeypatch: pytest.MonkeyPatch):
    policy_block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    policies = policy_block.get_policy_stack(ApiKeyError)
    assert len(policies) == 1
    assert policies[0].type == RecoveryType.BUBBLE

    class LiteLLMAuthError(Exception):
        pass

    def fake_completion(**kwargs):
        raise LiteLLMAuthError("Invalid API Key")

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )
    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == ApiKeyError
    assert response.reason == "api_key_error"


def test_llm_primitive_rate_limit_mapping(monkeypatch: pytest.MonkeyPatch):
    class LiteLLMRateLimitError(Exception):
        pass

    def fake_completion(**kwargs):
        raise LiteLLMRateLimitError("429 Too Many Requests")

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == RateLimitError
    assert response.reason == "rate_limit_error"


def test_llm_primitive_includes_api_key(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response('{"response":"hello"}')

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    config = Config.model_validate(
        {"openai_api_key": "test-key", "litellm_use_proxy": False}
    )
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        config=config,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert captured["api_key"] == "test-key"


def test_llm_primitive_accepts_dict_content(monkeypatch: pytest.MonkeyPatch):
    def fake_completion(**kwargs):
        return _fake_response({"response": "hello"})

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert response.data == {"response": "hello"}


def test_llm_primitive_invalid_payload_returns_failure():
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    response = block.execute(Request(payload={"unexpected": "value"}))

    assert response.success() is False
    assert response.reason == "invalid_payload"
    assert response.error_type == SchemaError


def test_llm_primitive_missing_choices_returns_schema_error(
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_completion(**kwargs):
        return {}

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.reason == "schema_error"
    assert response.error_type == SchemaError


def test_llm_primitive_context_length_mapping(monkeypatch: pytest.MonkeyPatch):
    class LiteLLMContextError(Exception):
        pass

    def fake_completion(**kwargs):
        raise LiteLLMContextError("context length exceeded")

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
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
        llm_service=_make_llm_service(),
        use_instructor=False,
    )

    estimate = block.estimate_execution(Request(payload={"prompt": "hello"}))

    assert estimate.estimate_source == "prior"
    assert estimate.sample_size == 0
    assert estimate.expected_llm_calls == 1.0
    assert estimate.block_type == "llm_primitive"


def test_llm_primitive_estimate_execution_from_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure LLMPrimitive returns a stats-based estimate when data exists."""

    store = InMemoryBlockStatsStore()
    set_default_store(store)

    def fake_completion(**kwargs):
        return _fake_response('{"response":"hello"}')

    monkeypatch.setattr("chaos.llm.llm_service.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        llm_service=_make_llm_service(),
        use_instructor=False,
    )
    block.execute(Request(payload={"prompt": "hello"}))
    estimate = block.estimate_execution(Request(payload={"prompt": "hello"}))

    assert estimate.estimate_source == "stats"
    assert estimate.sample_size == 1
    assert estimate.expected_llm_calls == 1.0
