from typing import Any, Callable, Dict, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Request(BaseModel):
    """Standardized request object passed to blocks."""

    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        """Initialize the request and ensure an envelope id is present."""

        super().__init__(**data)
        if "id" not in self.metadata:
            self.metadata["id"] = _REQUEST_ID_FACTORY()


class Response(BaseModel):
    """Unified response object returned by blocks."""

    success: bool = Field(description="Whether the execution succeeded")
    data: Optional[Any] = Field(
        default=None, description="Result value produced by the block"
    )
    reason: Optional[str] = Field(
        default=None, description="Short error label or category"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Structured diagnostic details"
    )
    error_type: Optional[Type[Exception]] = Field(
        default=None,
        description="Failure classification for policy selection",
        exclude=True,
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "id" not in self.metadata:
            self.metadata["id"] = str(uuid4())


_REQUEST_ID_FACTORY: Callable[[], str] = lambda: str(uuid4())


def set_request_id_factory(factory: Callable[[], str]) -> None:
    """Override the request id factory for deterministic tests.

    Args:
        factory: Callable that returns a unique request id.
    """

    global _REQUEST_ID_FACTORY
    _REQUEST_ID_FACTORY = factory


def reset_request_id_factory() -> None:
    """Reset the request id factory to the default UUID generator."""

    global _REQUEST_ID_FACTORY
    _REQUEST_ID_FACTORY = lambda: str(uuid4())
