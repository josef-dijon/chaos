from __future__ import annotations

import pytest
from pydantic import BaseModel, SecretStr

from chaos.domain.exceptions import RateLimitError, SchemaError
from chaos.llm.llm_error_mapper import map_llm_error
from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_service import LLMService
from chaos.llm.response_status import ResponseStatus


class MockSchema(BaseModel):
    response: str


def _build_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ],
        output_data_model=MockSchema,
        model="test-model",
        temperature=0.0,
        manager_id="manager-1",
        attempt=1,
        metadata={},
    )


def test_llm_service_success_returns_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure LLMService returns validated structured output."""

    service = LLMService()

    def fake_run_agent(*, request, system_prompt, user_prompt):
        assert system_prompt == "sys"
        assert user_prompt == "hello"
        return {"response": "ok"}, {"input_tokens": 1}

    monkeypatch.setattr(service, "_run_agent", fake_run_agent)
    request = _build_request()
    response = service.execute(request)

    assert response.status == ResponseStatus.SUCCESS
    assert response.data == {"response": "ok"}


def test_llm_service_schema_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure schema errors map to semantic failures."""

    service = LLMService()

    def fake_run_agent(*, request, system_prompt, user_prompt):
        raise SchemaError("bad")

    monkeypatch.setattr(service, "_run_agent", fake_run_agent)
    request = _build_request()
    response = service.execute(request)

    assert response.status == ResponseStatus.SEMANTIC_ERROR
    assert response.reason == "schema_error"
    assert response.error_type == SchemaError


def test_llm_service_rate_limit_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure rate limit-like errors map to mechanical errors."""

    service = LLMService()

    def fake_run_agent(*, request, system_prompt, user_prompt):
        raise RateLimitError("Too many requests")

    monkeypatch.setattr(service, "_run_agent", fake_run_agent)
    request = _build_request()
    response = service.execute(request)

    assert response.status == ResponseStatus.MECHANICAL_ERROR
    assert response.reason == "rate_limit_error"
    assert response.error_type == RateLimitError


def test_llm_service_unknown_error_maps_internal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure unknown exceptions map to internal errors."""
    service = LLMService()

    def fake_run_agent(*, request, system_prompt, user_prompt):
        raise ValueError("boom")

    monkeypatch.setattr(service, "_run_agent", fake_run_agent)
    request = _build_request()
    response = service.execute(request)

    assert response.status == ResponseStatus.MECHANICAL_ERROR
    assert response.reason == "internal_error"
    assert response.error_type == ValueError


def test_llm_service_render_prompts_single_user() -> None:
    service = LLMService()

    system_prompt, user_prompt = service._render_prompts(
        [{"role": "user", "content": "hello"}]
    )

    assert system_prompt is None
    assert user_prompt == "hello"


def test_llm_service_render_prompts_multiturn() -> None:
    service = LLMService()

    system_prompt, user_prompt = service._render_prompts(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]
    )

    assert system_prompt == "sys"
    assert "User: u1" in user_prompt
    assert "Assistant: a1" in user_prompt
    assert "User: u2" in user_prompt


def test_llm_service_render_prompts_ignores_empty_content() -> None:
    service = LLMService()

    system_prompt, user_prompt = service._render_prompts(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "a1"},
        ]
    )

    assert system_prompt == "sys"
    assert user_prompt == "Assistant: a1"


def test_llm_service_run_agent_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    service = LLMService()

    class FakeUsage:
        requests = 2
        input_tokens = 3
        output_tokens = 5

    class FakeResult:
        def __init__(self, output):
            self.output = output

        def usage(self):
            return FakeUsage()

    class FakeAgent:
        def __init__(self, model, system_prompt, output_type, output_retries):
            assert output_retries >= 0
            self._output_type = output_type

        def run_sync(self, user_prompt, model_settings):
            assert user_prompt == "hello"
            assert model_settings["temperature"] == 0.0
            return FakeResult(self._output_type(response="ok"))

    monkeypatch.setattr("chaos.llm.llm_service.Agent", FakeAgent)
    monkeypatch.setattr(
        "chaos.llm.llm_service.OpenAIChatModel", lambda *a, **k: object()
    )

    request = _build_request()
    data, usage = service._run_agent(
        request=request, system_prompt="sys", user_prompt="hello"
    )

    assert data == {"response": "ok"}
    assert usage == {"requests": 2, "input_tokens": 3, "output_tokens": 5}


def test_llm_service_run_agent_unexpected_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = LLMService()

    class FakeResult:
        output = ["unexpected"]

        def usage(self):
            return type("Usage", (), {})()

    class FakeAgent:
        def __init__(self, model, system_prompt, output_type, output_retries):
            pass

        def run_sync(self, user_prompt, model_settings):
            return FakeResult()

    monkeypatch.setattr("chaos.llm.llm_service.Agent", FakeAgent)
    monkeypatch.setattr(
        "chaos.llm.llm_service.OpenAIChatModel", lambda *a, **k: object()
    )

    with pytest.raises(TypeError):
        service._run_agent(
            request=_build_request(), system_prompt="sys", user_prompt="hello"
        )


def test_llm_error_mapper_http_status_error_429() -> None:
    try:
        import httpx
    except ImportError:  # pragma: no cover
        pytest.skip("httpx not installed")

    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(429, request=request)
    err = httpx.HTTPStatusError("too many", request=request, response=response)

    mapping = map_llm_error(err)

    assert mapping.reason == "rate_limit_error"
    assert mapping.error_type == RateLimitError


def test_llm_error_mapper_unexpected_model_behavior_schema() -> None:
    try:
        from pydantic_ai import UnexpectedModelBehavior
    except ImportError:  # pragma: no cover
        pytest.skip("pydantic_ai not installed")

    mapping = map_llm_error(UnexpectedModelBehavior("Output validation failed"))
    assert mapping.reason == "schema_error"
    assert mapping.error_type == SchemaError


def test_llm_service_build_model_uses_model_builder() -> None:
    sentinel = object()

    from typing import cast

    from pydantic_ai.models.openai import OpenAIChatModel

    def builder(request: LLMRequest) -> OpenAIChatModel:
        return cast(OpenAIChatModel, sentinel)

    service = LLMService(model_builder=builder)
    model = service._build_model(_build_request())

    assert model is sentinel


def test_llm_service_resolve_api_key() -> None:
    assert LLMService._resolve_api_key(SecretStr("secret")) == "secret"
    assert LLMService._resolve_api_key("plain") == "plain"
    assert LLMService._resolve_api_key(123) == "123"


def test_llm_service_build_model_api_base_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_async_openai(**kwargs):
        captured.update(kwargs)
        return object()

    def fake_provider(*, openai_client):
        captured["openai_client"] = openai_client
        return object()

    def fake_model(model_name: str, *, provider):
        captured["model_name"] = model_name
        captured["provider"] = provider
        return object()

    monkeypatch.setattr("chaos.llm.llm_service.AsyncOpenAI", fake_async_openai)
    monkeypatch.setattr("chaos.llm.llm_service.OpenAIProvider", fake_provider)
    monkeypatch.setattr("chaos.llm.llm_service.OpenAIChatModel", fake_model)

    request = _build_request().model_copy(
        update={"api_base": "http://proxy", "api_key": "k"}
    )
    service = LLMService()
    model = service._build_model(request)

    assert model is not None
    assert captured["base_url"] == "http://proxy"
    assert captured["api_key"] == "k"
    assert captured["max_retries"] == 2
    assert captured["model_name"] == "test-model"


def test_llm_service_build_model_api_key_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_async_openai(**kwargs):
        captured.update(kwargs)
        return object()

    def fake_provider(*, openai_client):
        captured["openai_client"] = openai_client
        return object()

    def fake_model(model_name: str, *, provider):
        captured["model_name"] = model_name
        captured["provider"] = provider
        return object()

    monkeypatch.setattr("chaos.llm.llm_service.AsyncOpenAI", fake_async_openai)
    monkeypatch.setattr("chaos.llm.llm_service.OpenAIProvider", fake_provider)
    monkeypatch.setattr("chaos.llm.llm_service.OpenAIChatModel", fake_model)

    request = _build_request().model_copy(update={"api_base": None, "api_key": "k"})
    service = LLMService()
    model = service._build_model(request)

    assert model is not None
    assert captured["api_key"] == "k"
    assert captured["max_retries"] == 2
    assert captured["model_name"] == "test-model"


def test_llm_service_build_model_default_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_model(model_name: str):
        captured["model_name"] = model_name
        return object()

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def should_not_build_client(**kwargs):
        raise AssertionError("AsyncOpenAI should not be constructed")

    monkeypatch.setattr("chaos.llm.llm_service.AsyncOpenAI", should_not_build_client)
    monkeypatch.setattr("chaos.llm.llm_service.OpenAIChatModel", fake_model)

    request = _build_request().model_copy(update={"api_base": None, "api_key": None})
    service = LLMService()
    model = service._build_model(request)

    assert model is not None
    assert captured["model_name"] == "test-model"


def test_llm_error_mapper_api_key_message() -> None:
    mapping = map_llm_error(Exception("Invalid API key"))
    assert mapping.reason == "api_key_error"


def test_llm_error_mapper_context_message() -> None:
    try:
        import httpx
    except ImportError:  # pragma: no cover
        pytest.skip("httpx not installed")

    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(
        400,
        request=request,
        json={
            "error": {
                "code": "context_length_exceeded",
                "message": "maximum context length exceeded",
            }
        },
    )
    err = httpx.HTTPStatusError("context too long", request=request, response=response)

    mapping = map_llm_error(err)

    assert mapping.reason == "context_length_error"
