from typing import Callable, Dict

from chaos.domain.messages import Request, Response


class RepairRegistry:
    """Registry for request repair functions."""

    _registry: Dict[str, Callable[[Request, Response], Request]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a repair function."""

        def wrapper(func: Callable[[Request, Response], Request]):
            cls._registry[name] = func
            return func

        return wrapper

    @classmethod
    def get(cls, name: str) -> Callable[[Request, Response], Request]:
        """Retrieve a repair function by name."""
        if name not in cls._registry:
            raise ValueError(f"Repair function '{name}' not found in registry")
        return cls._registry[name]

    @classmethod
    def clear(cls):
        """Clear the registry (useful for testing).

        Note:
            Built-in repair functions are re-registered after clearing.
        """
        cls._registry.clear()
        _register_builtin_repairs()


def add_validation_feedback(request: Request, failure: Response) -> Request:
    """Append schema validation feedback into the prompt.

    This repair is intended for SchemaError-style failures where the model output
    did not conform to the required schema.

    Args:
        request: The original request that produced the failure.
        failure: The failed response containing validation error details.

    Returns:
        A new Request with the prompt updated to include validation feedback.
    """

    cloned = request.model_copy(deep=True)

    payload = dict(cloned.payload or {})
    existing_prompt = ""
    for key in ("prompt", "content", "input"):
        value = payload.get(key)
        if isinstance(value, str):
            existing_prompt = value
            break

    error_text = failure.details.get("error") or failure.details.get("message") or ""
    feedback = (
        "The previous response failed validation. "
        f"Validation error: {error_text}. "
        "Please respond with valid JSON matching the required schema."
    )

    if existing_prompt:
        new_prompt = f"{existing_prompt}\n\n{feedback}"
    else:
        new_prompt = feedback

    payload["prompt"] = new_prompt
    cloned.payload = payload
    return cloned


def _register_builtin_repairs() -> None:
    """Register built-in repair functions.

    This function is intentionally idempotent.
    """

    RepairRegistry._registry.setdefault(
        "add_validation_feedback", add_validation_feedback
    )


_register_builtin_repairs()
