import pytest

from chaos.domain.messages import Request, Response
from chaos.engine.registry import RepairRegistry, add_validation_feedback


def test_registry_registration():
    @RepairRegistry.register("test_func")
    def func(req, fail):
        return req

    assert RepairRegistry.get("test_func") == func
    RepairRegistry.clear()


def test_registry_get_missing():
    with pytest.raises(ValueError):
        RepairRegistry.get("missing_func")


def test_registry_clear():
    @RepairRegistry.register("test_func")
    def func(req, fail):
        return req

    RepairRegistry.clear()
    with pytest.raises(ValueError):
        RepairRegistry.get("test_func")


def test_registry_clear_preserves_builtin_repairs() -> None:
    RepairRegistry.clear()
    assert callable(RepairRegistry.get("add_validation_feedback"))


def test_add_validation_feedback_appends_to_existing_prompt() -> None:
    request = Request(payload={"prompt": "hello"}, metadata={"trace_id": "t"})
    failure = Response(success=False, reason="schema_error", details={"error": "bad"})

    repaired = add_validation_feedback(request, failure)

    assert repaired.payload["prompt"].startswith("hello")
    assert "previous response failed validation" in repaired.payload["prompt"].lower()
    assert "bad" in repaired.payload["prompt"]
    assert repaired.metadata["trace_id"] == "t"


def test_add_validation_feedback_creates_prompt_when_missing() -> None:
    request = Request(payload={}, metadata={"trace_id": "t"})
    failure = Response(success=False, reason="schema_error", details={"error": "bad"})

    repaired = add_validation_feedback(request, failure)

    assert isinstance(repaired.payload.get("prompt"), str)
    assert "valid json" in repaired.payload["prompt"].lower()
