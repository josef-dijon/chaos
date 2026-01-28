from typing import Any, Dict, List, Optional, Type

from litellm import completion
from pydantic import BaseModel, ValidationError

from chaos.config import Config
from chaos.domain.block import Block
from chaos.domain.exceptions import (
    ApiKeyError,
    ContextLengthError,
    RateLimitError,
    SchemaError,
)
from chaos.domain.messages import Request, Response
from chaos.domain.policy import (
    BubblePolicy,
    RecoveryPolicy,
    RecoveryType,
    RepairPolicy,
    RetryPolicy,
)


class LLMPrimitive(Block):
    """Stateless Atomic Block that wraps a raw Large Language Model interaction."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        output_data_model: Type[BaseModel],
        model: Optional[str] = None,
        temperature: float = 0.0,
        config: Optional[Config] = None,
    ):
        """Initialize the LLM primitive.

        Args:
            name: Stable identifier for this block instance.
            system_prompt: System prompt prepended to the model context.
            output_data_model: Pydantic schema used to validate model output.
            model: Optional model override. Defaults to Config model_name.
            temperature: Sampling temperature for the model.
            config: Optional Config instance for provider settings.
        """
        self._config = config or Config.load()
        resolved_model = model or self._config.get_model_name()
        super().__init__(name, side_effect_class="idempotent")
        self._system_prompt = system_prompt
        self._output_data_model = output_data_model
        self._model = resolved_model
        self._temperature = temperature

    def build(self) -> None:
        """Atomic blocks do not have a graph."""
        pass

    def _execute_primitive(self, request: Request) -> Response:
        """Execute the LLM call with the given request payload."""
        try:
            prompt = self._coerce_payload(request.payload)
            messages = self._build_messages(prompt)
            content = self._invoke_llm(messages)
            data = self._validate_output(content)
            return Response(success=True, data=data)
        except Exception as exc:
            return self._handle_error(exc)

    def _coerce_payload(self, payload: Any) -> str:
        """Normalize the request payload into a prompt string.

        Args:
            payload: Request payload value.

        Returns:
            Prompt string to send to the model.
        """
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            for key in ("prompt", "content", "input"):
                value = payload.get(key)
                if isinstance(value, str):
                    return value
        raise ValueError("LLMPrimitive payload must be a string or prompt dict.")

    def _build_messages(self, prompt: str) -> List[Dict[str, str]]:
        """Construct the message list for the LLM call.

        Args:
            prompt: User prompt content.

        Returns:
            A list of message dicts for the model.
        """
        messages: List[Dict[str, str]] = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _invoke_llm(self, messages: List[Dict[str, str]]) -> Any:
        """Invoke the LLM via LiteLLM and return raw content.

        Args:
            messages: Message list for the completion call.

        Returns:
            Model response content.
        """
        call_args: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
        }
        api_key = self._config.get_openai_api_key()
        if api_key:
            call_args["api_key"] = api_key
        response_format = self._build_response_format()
        if response_format is not None:
            call_args["response_format"] = response_format
        response = completion(**call_args)
        return self._extract_content(response)

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

    def _validate_output(self, content: Any) -> Dict[str, Any]:
        """Validate model content against the output schema.

        Args:
            content: Raw model content.

        Returns:
            A validated and normalized dict matching the output schema.
        """
        try:
            if isinstance(content, str):
                model = self._output_data_model.model_validate_json(content)
            else:
                model = self._output_data_model.model_validate(content)
        except (ValidationError, ValueError) as exc:
            raise SchemaError(str(exc)) from exc
        return model.model_dump()

    def _handle_error(self, error: Exception) -> Response:
        """Map provider errors into failed Response objects.

        Args:
            error: Exception raised during execution.

        Returns:
            A failed Response containing the mapped error details.
        """
        if isinstance(error, SchemaError):
            return self._failure_response("schema_error", error, SchemaError)
        if isinstance(error, RateLimitError):
            return self._failure_response("rate_limit_error", error, RateLimitError)
        if isinstance(error, ApiKeyError):
            return self._failure_response("api_key_error", error, ApiKeyError)
        if isinstance(error, ContextLengthError):
            return self._failure_response(
                "context_length_error", error, ContextLengthError
            )
        if isinstance(error, ValueError):
            return self._failure_response("invalid_payload", error, SchemaError)

        error_name = error.__class__.__name__.lower()
        error_message = str(error).lower()
        if (
            "ratelimit" in error_name
            or "rate limit" in error_message
            or "429" in error_message
        ):
            return self._failure_response("rate_limit_error", error, RateLimitError)
        if (
            "authentication" in error_name
            or "auth" in error_name
            or "api key" in error_message
            or "apikey" in error_message
        ):
            return self._failure_response("api_key_error", error, ApiKeyError)
        if "context" in error_name or "context" in error_message:
            return self._failure_response(
                "context_length_error", error, ContextLengthError
            )

        return Response(
            success=False,
            reason="llm_execution_failed",
            details={"error": str(error)},
            error_type=type(error),
        )

    def _failure_response(
        self,
        reason: str,
        error: Exception,
        error_type: Type[Exception],
    ) -> Response:
        """Build a standardized failure response for LLM errors.

        Args:
            reason: Stable reason label for the failure.
            error: The originating exception.
            error_type: Classification used for recovery policy selection.

        Returns:
            A failed Response instance.
        """
        return Response(
            success=False,
            reason=reason,
            details={"error": str(error)},
            error_type=error_type,
        )

    def _build_response_format(self) -> Optional[Dict[str, Any]]:
        """Build a response-format hint for LiteLLM if supported.

        Returns:
            A response_format payload or None if not supported.
        """
        if not self._supports_response_format():
            return None
        schema = self._output_data_model.model_json_schema()
        return {
            "type": "json_schema",
            "json_schema": {
                "name": self._output_data_model.__name__,
                "schema": schema,
            },
        }

    def _supports_response_format(self) -> bool:
        """Return True if the current model likely supports response_format.

        This is a best-effort heuristic to avoid unsupported parameter errors.
        """
        model_name = (self._model or "").lower()
        return model_name.startswith("gpt-") or model_name.startswith("o")

    def get_policy_stack(self, error_type: Type[Exception]) -> List[RecoveryPolicy]:
        """Return hardcoded recovery policies for LLM failures."""

        if issubclass(error_type, SchemaError):
            return [
                RetryPolicy(max_attempts=1),  # Simple Retry
                RepairPolicy(repair_function="add_validation_feedback"),  # Feedback 1
                RepairPolicy(repair_function="add_validation_feedback"),  # Feedback 2
                BubblePolicy(),
            ]

        if issubclass(error_type, RateLimitError):
            return [
                RetryPolicy(max_attempts=3, delay_seconds=2.0),  # Wait and Retry
                BubblePolicy(),
            ]

        # ApiKeyError, ContextLengthError, and others bubble immediately
        return [BubblePolicy()]
