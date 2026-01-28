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


class MockSchema(BaseModel):
    response: str


def _fake_response(content: Any) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_llm_primitive_initialization():
    block = LLMPrimitive(
        name="test_llm", system_prompt="You are a bot", output_data_model=MockSchema
    )
    assert block.name == "test_llm"
    assert block.state.name == "READY"


def test_llm_primitive_happy_path(monkeypatch: pytest.MonkeyPatch):
    def fake_completion(**kwargs):
        return _fake_response('{"response":"hello"}')

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
    )
    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert response.data == {"response": "hello"}


def test_llm_primitive_schema_error_policies(monkeypatch: pytest.MonkeyPatch):
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
    )

    # Verify policy stack for SchemaError
    policies = block.get_policy_stack(SchemaError)
    assert len(policies) == 4
    assert policies[0].type == RecoveryType.RETRY
    assert policies[1].type == RecoveryType.REPAIR
    assert policies[2].type == RecoveryType.REPAIR
    assert policies[3].type == RecoveryType.BUBBLE

    # Trigger execution failure
    def fake_completion(**kwargs):
        return _fake_response("not-json")

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == SchemaError
    assert response.reason == "schema_error"


def test_llm_primitive_rate_limit_policies():
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
    )

    policies = block.get_policy_stack(RateLimitError)
    assert len(policies) == 2
    assert policies[0].type == RecoveryType.RETRY
    assert isinstance(policies[0], RetryPolicy)
    assert policies[0].delay_seconds == 2.0
    assert policies[1].type == RecoveryType.BUBBLE


def test_llm_primitive_auth_error_policies(monkeypatch: pytest.MonkeyPatch):
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
    )

    policies = block.get_policy_stack(ApiKeyError)
    assert len(policies) == 1
    assert policies[0].type == RecoveryType.BUBBLE

    class LiteLLMAuthError(Exception):
        pass

    def fake_completion(**kwargs):
        raise LiteLLMAuthError("Invalid API Key")

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.error_type == ApiKeyError
    assert response.reason == "api_key_error"


def test_llm_primitive_rate_limit_mapping(monkeypatch: pytest.MonkeyPatch):
    class LiteLLMRateLimitError(Exception):
        pass

    def fake_completion(**kwargs):
        raise LiteLLMRateLimitError("429 Too Many Requests")

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
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

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    config = Config.model_validate({"openai_api_key": "test-key"})
    block = LLMPrimitive(
        name="test_llm",
        system_prompt="sys",
        output_data_model=MockSchema,
        config=config,
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert captured["api_key"] == "test-key"


def test_llm_primitive_accepts_dict_content(monkeypatch: pytest.MonkeyPatch):
    def fake_completion(**kwargs):
        return _fake_response({"response": "hello"})

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is True
    assert response.data == {"response": "hello"}


def test_llm_primitive_invalid_payload_returns_failure():
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
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

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
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

    monkeypatch.setattr("chaos.domain.llm_primitive.completion", fake_completion)
    block = LLMPrimitive(
        name="test_llm", system_prompt="sys", output_data_model=MockSchema
    )

    response = block.execute(Request(payload={"prompt": "hello"}))

    assert response.success() is False
    assert response.reason == "context_length_error"
    assert response.error_type == ContextLengthError
