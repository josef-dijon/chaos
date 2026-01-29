from chaos.domain.messages import Request
from chaos.llm.model_selector import ModelSelector


def test_model_selector_returns_default() -> None:
    """Ensure ModelSelector returns the provided default model."""

    selector = ModelSelector()
    request = Request(payload={"prompt": "hello"})

    assert selector.select_model(request, "default-model") == "default-model"
