from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from chaos.llm.response_status import ResponseStatus


class LLMResponse(BaseModel):
    """Internal response container for LLM execution."""

    status: ResponseStatus = Field(description="Execution status for the LLM call.")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Parsed response data when successful."
    )
    reason: Optional[str] = Field(
        default=None, description="Stable reason label for failures."
    )
    error_type: Optional[type[Exception]] = Field(
        default=None, description="Error type used for recovery mapping."
    )
    error_details: Dict[str, Any] = Field(
        default_factory=dict, description="Structured error details."
    )
    raw_output: Optional[Any] = Field(
        default=None, description="Raw output returned from the provider."
    )
    usage: Optional[Dict[str, Any]] = Field(
        default=None, description="Provider usage metadata if available."
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def success(
        cls,
        data: Dict[str, Any],
        raw_output: Optional[Any] = None,
        usage: Optional[Dict[str, Any]] = None,
    ) -> "LLMResponse":
        """Build a successful LLM response.

        Args:
            data: Parsed data from the LLM response.
            raw_output: Raw provider output if available.
            usage: Usage metadata if available.

        Returns:
            A successful LLMResponse.
        """

        return cls(
            status=ResponseStatus.SUCCESS,
            data=data,
            raw_output=raw_output,
            usage=usage,
        )

    @classmethod
    def failure(
        cls,
        status: ResponseStatus,
        reason: str,
        error_type: type[Exception],
        error_details: Optional[Dict[str, Any]] = None,
        raw_output: Optional[Any] = None,
    ) -> "LLMResponse":
        """Build a failed LLM response.

        Args:
            status: Failure status category.
            reason: Stable reason label for the failure.
            error_type: Error type used for recovery mapping.
            error_details: Structured error details if available.
            raw_output: Raw provider output if available.

        Returns:
            A failed LLMResponse.
        """

        return cls(
            status=status,
            reason=reason,
            error_type=error_type,
            error_details=error_details or {},
            raw_output=raw_output,
        )
