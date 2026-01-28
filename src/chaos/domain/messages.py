from typing import Any, Dict, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Request(BaseModel):
    """Standardized request object passed to blocks."""

    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Response(BaseModel):
    """Unified response object returned by blocks."""

    ok: bool = Field(alias="success", description="Whether the execution succeeded")
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

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "id" not in self.metadata:
            self.metadata["id"] = str(uuid4())

    def success(self) -> bool:
        """Return True if the response represents success."""

        return self.ok
