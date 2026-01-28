from typing import Callable, Dict

from chaos.domain.messages import Response


class ConditionRegistry:
    """Registry for transition condition functions."""

    _registry: Dict[str, Callable[[Response], bool]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a condition function."""

        def wrapper(func: Callable[[Response], bool]):
            cls._registry[name] = func
            return func

        return wrapper

    @classmethod
    def get(cls, name: str) -> Callable[[Response], bool]:
        """Retrieve a condition function by name."""
        if name == "default":
            return lambda _: True

        if name not in cls._registry:
            raise ValueError(f"Condition function '{name}' not found in registry")
        return cls._registry[name]

    @classmethod
    def clear(cls):
        """Clear the registry (useful for testing)."""
        cls._registry.clear()
