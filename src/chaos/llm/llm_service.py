from typing import Any, Dict, Optional, Tuple

from litellm import completion
from pydantic import BaseModel, ValidationError

from chaos.domain.exceptions import SchemaError
from chaos.llm.llm_error_mapper import map_llm_error
from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_response import LLMResponse
from chaos.llm.llm_retry_policy import (
    DEFAULT_MAX_ATTEMPTS,
    default_retry_exceptions,
    default_wait_strategy,
)
from chaos.llm.response_status import ResponseStatus
from chaos.llm.stable_transport import StableTransport

try:
    import instructor  # type: ignore
except ImportError:  # pragma: no cover
    instructor = None


class LLMService:
    """LLM execution service that wraps schema enforcement and transport."""

    def __init__(
        self,
        transport: Optional[StableTransport] = None,
        use_instructor: bool = True,
        retry_exceptions: Optional[Tuple[type[Exception], ...]] = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        wait_strategy: Optional[Any] = None,
    ) -> None:
        """Initialize the LLM service.

        Args:
            transport: Optional transport override.
            use_instructor: Whether to use instructor for schema enforcement.
            retry_exceptions: Exception types eligible for transport retry.
            max_attempts: Maximum transport retry attempts.
            wait_strategy: Tenacity wait strategy override.
        """

        self._use_instructor = use_instructor and instructor is not None
        completion_callable = completion
        if self._use_instructor:
            assert instructor is not None
            completion_callable = instructor.patch(completion)
        resolved_retry_exceptions = (
            default_retry_exceptions() if retry_exceptions is None else retry_exceptions
        )
        resolved_wait = (
            default_wait_strategy() if wait_strategy is None else wait_strategy
        )
        self._transport = transport or StableTransport(
            completion_callable,
            retry_exceptions=resolved_retry_exceptions,
            max_attempts=max_attempts,
            wait_strategy=resolved_wait,
        )

    def execute(self, request: LLMRequest) -> LLMResponse:
        """Execute the LLM call and return a structured response.

        Args:
            request: LLM request to execute.

        Returns:
            LLMResponse containing success or failure information.
        """

        call_args = self._build_call_args(request)
        try:
            if self._use_instructor:
                call_args["response_model"] = request.output_data_model
                result = self._transport.complete(call_args)
                data = self._normalize_instructor_output(
                    result, request.output_data_model
                )
                return LLMResponse.success(data=data, raw_output=None)

            response = self._transport.complete(call_args)
            content = self._extract_content(response)
            data = self._validate_output(content, request.output_data_model)
            usage = self._extract_usage(response)
            return LLMResponse.success(data=data, raw_output=response, usage=usage)
        except Exception as exc:
            mapping = map_llm_error(self._normalize_error(exc))
            return LLMResponse.failure(
                status=mapping.status,
                reason=mapping.reason,
                error_type=mapping.error_type,
                error_details=mapping.details,
            )

    def _build_call_args(self, request: LLMRequest) -> Dict[str, Any]:
        """Build LiteLLM call arguments from the internal request.

        Args:
            request: LLM request to translate.

        Returns:
            Keyword arguments for LiteLLM completion.
        """

        call_args: Dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "metadata": request.metadata,
        }
        if not self._use_instructor:
            response_format = self._build_response_format(request)
            if response_format is not None:
                call_args["response_format"] = response_format
        if request.api_base:
            call_args["api_base"] = request.api_base
        if request.api_key:
            call_args["api_key"] = request.api_key
        return call_args

    def _normalize_instructor_output(
        self, result: Any, model: type[BaseModel]
    ) -> Dict[str, Any]:
        """Normalize instructor output into a dict.

        Args:
            result: Result returned by instructor.
            model: Expected output data model.

        Returns:
            Parsed data dict.
        """

        if isinstance(result, BaseModel):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            return self._validate_output(result, model)
        raise SchemaError("Unsupported instructor response type")

    def _extract_content(self, response: Any) -> Any:
        """Extract the content field from a LiteLLM response.

        Args:
            response: LiteLLM completion response.

        Returns:
            The message content from the first choice.
        """

        if isinstance(response, dict):
            choices = response.get("choices")
        else:
            choices = getattr(response, "choices", None)
        if not choices:
            raise SchemaError("Missing choices in LLM response")

        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
        else:
            message = getattr(first_choice, "message", None)
        if message is None:
            raise SchemaError("Missing message in LLM response")

        if isinstance(message, dict):
            content = message.get("content")
        else:
            content = getattr(message, "content", None)
        if content is None:
            raise SchemaError("Missing content in LLM response")
        return content

    def _extract_usage(self, response: Any) -> Optional[Dict[str, Any]]:
        """Extract usage metadata from a LiteLLM response.

        Args:
            response: LiteLLM completion response.

        Returns:
            Usage metadata if available.
        """

        if isinstance(response, dict):
            return response.get("usage")
        return getattr(response, "usage", None)

    def _validate_output(self, content: Any, model: type[BaseModel]) -> Dict[str, Any]:
        """Validate model content against the output schema.

        Args:
            content: Raw model content.
            model: Pydantic model used to validate output.

        Returns:
            A validated and normalized dict matching the output schema.
        """

        try:
            if isinstance(content, str):
                parsed = model.model_validate_json(content)
            else:
                parsed = model.model_validate(content)
        except (ValidationError, ValueError) as exc:
            raise SchemaError(str(exc)) from exc
        return parsed.model_dump()

    def _normalize_error(self, error: Exception) -> Exception:
        """Normalize exceptions into domain errors where possible."""

        if isinstance(error, SchemaError):
            return error
        return error

    def _build_response_format(self, request: LLMRequest) -> Optional[Dict[str, Any]]:
        """Build a response-format hint for LiteLLM if supported.

        Args:
            request: LLM request being executed.

        Returns:
            A response_format payload or None if not supported.
        """

        if not self._supports_response_format(request.model):
            return None
        schema = request.output_data_model.model_json_schema()
        return {
            "type": "json_schema",
            "json_schema": {
                "name": request.output_data_model.__name__,
                "schema": schema,
            },
        }

    def _supports_response_format(self, model: str) -> bool:
        """Return True if the model likely supports response_format.

        Args:
            model: Model name to check.

        Returns:
            True if response_format should be safe to send.
        """

        model_name = (model or "").lower()
        return model_name.startswith("gpt-") or model_name.startswith("o")
