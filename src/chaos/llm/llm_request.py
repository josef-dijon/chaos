from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LLMRequest(BaseModel):
    """Internal request payload for LLM execution."""

    messages: List[Dict[str, str]] = Field(description="Chat messages for the LLM.")
    output_data_model: Type[BaseModel] = Field(
        description="Pydantic model used to validate output."
    )
    model: str = Field(description="Model identifier for the request.")
    temperature: float = Field(description="Sampling temperature.")
    manager_id: str = Field(description="Unique manager identifier for auditing.")
    attempt: int = Field(description="Attempt number for this execution.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Provider metadata for auditing."
    )
    api_base: Optional[str] = Field(
        default=None, description="Optional API base override for proxy usage."
    )
    api_key: Optional[SecretStr] = Field(
        default=None, description="Optional API key for provider access."
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
