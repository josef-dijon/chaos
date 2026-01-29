from types import SimpleNamespace

from pydantic import BaseModel

from chaos.domain.exceptions import RateLimitError, SchemaError
from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_service import LLMService
from chaos.llm.response_status import ResponseStatus
from chaos.llm.stable_transport import StableTransport


class MockSchema(BaseModel):
    response: str


def _fake_response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_llm_service_success_parses_json() -> None:
    """Ensure LLMService parses JSON content successfully."""

    def fake_completion(**kwargs):
        return _fake_response('{"response":"ok"}')

    transport = StableTransport(fake_completion)
    service = LLMService(transport=transport, use_instructor=False)
    request = LLMRequest(
        messages=[{"role": "user", "content": "hello"}],
        output_data_model=MockSchema,
        model="test-model",
        temperature=0.0,
        manager_id="manager-1",
        attempt=1,
        metadata={},
    )
    response = service.execute(request)

    assert response.status == ResponseStatus.SUCCESS
    assert response.data == {"response": "ok"}


def test_llm_service_schema_error() -> None:
    """Ensure schema errors are returned as semantic failures."""

    def fake_completion(**kwargs):
        return _fake_response("not-json")

    transport = StableTransport(fake_completion)
    service = LLMService(transport=transport, use_instructor=False)
    request = LLMRequest(
        messages=[{"role": "user", "content": "hello"}],
        output_data_model=MockSchema,
        model="test-model",
        temperature=0.0,
        manager_id="manager-1",
        attempt=1,
        metadata={},
    )
    response = service.execute(request)

    assert response.status == ResponseStatus.SEMANTIC_ERROR
    assert response.reason == "schema_error"
    assert response.error_type == SchemaError


def test_llm_service_rate_limit_mapping() -> None:
    """Ensure rate limit exceptions map to mechanical errors."""

    def fake_completion(**kwargs):
        raise Exception("429 Too Many Requests")

    transport = StableTransport(fake_completion)
    service = LLMService(transport=transport, use_instructor=False)
    request = LLMRequest(
        messages=[{"role": "user", "content": "hello"}],
        output_data_model=MockSchema,
        model="test-model",
        temperature=0.0,
        manager_id="manager-1",
        attempt=1,
        metadata={},
    )
    response = service.execute(request)

    assert response.status == ResponseStatus.MECHANICAL_ERROR
    assert response.reason == "rate_limit_error"
    assert response.error_type == RateLimitError
