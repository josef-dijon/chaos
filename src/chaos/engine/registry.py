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
        """Clear the registry (useful for testing)."""
        cls._registry.clear()
