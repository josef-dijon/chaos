from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, SecretStr

from chaos.config import Config
from chaos.domain.block import Block
from chaos.domain.block_estimate import BlockEstimate
from chaos.domain.error_sanitizer import (
    build_exception_details,
    sanitize_error_details,
)
from chaos.domain.exceptions import (
    ApiKeyError,
    ContextLengthError,
    RateLimitError,
    SchemaError,
)
from chaos.domain.messages import Request, Response
from chaos.domain.policy import BubblePolicy, RecoveryPolicy
from chaos.llm.litellm_stats_adapter import LiteLLMStatsAdapter
from chaos.llm.llm_executor import LLMExecutor
from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_response import LLMResponse
from chaos.llm.llm_service import LLMService
from chaos.llm.response_status import ResponseStatus
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.store_registry import get_default_store


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
        stats_adapter: Optional[LiteLLMStatsAdapter] = None,
        llm_service: Optional[LLMExecutor] = None,
        output_retries: int = 2,
    ):
        """Initialize the LLM primitive.

        Args:
            name: Stable identifier for this block instance.
            system_prompt: System prompt prepended to the model context.
            output_data_model: Pydantic schema used to validate model output.
            model: Optional model override. Defaults to Config model_name.
            temperature: Sampling temperature for the model.
            config: Optional Config instance for provider settings.
            stats_adapter: Optional stats adapter for LLM estimation.
            llm_service: Optional LLM executor override.
            output_retries: Number of PydanticAI output validation retries.
        """
        self._config = config or Config()
        resolved_model = model or self._config.get_model_name()
        super().__init__(name, side_effect_class="idempotent")
        self._system_prompt = system_prompt
        self._output_data_model = output_data_model
        self._model = resolved_model
        self._temperature = temperature
        self._stats_adapter = stats_adapter
        self._llm_service: LLMExecutor = llm_service or LLMService(
            output_retries=output_retries
        )

    def build(self) -> None:
        """Atomic blocks do not have a graph."""
        pass

    def _execute_primitive(self, request: Request) -> Response:
        """Execute the LLM call with the given request payload."""
        try:
            prompt = self._coerce_payload(request.payload)
        except ValueError as exc:
            return self._failure_response("invalid_payload", exc, SchemaError)

        messages = self._build_messages(prompt)
        model = self._model
        execution_id = self._build_execution_id()
        api_base, api_key = self._resolve_api_settings()

        llm_request = self._build_llm_request(
            request=request,
            messages=messages,
            model=model,
            execution_id=execution_id,
            attempt=1,
            api_base=api_base,
            api_key=api_key,
        )
        llm_response = self._llm_service.execute(llm_request)
        response_metadata: Dict[str, Any] = {
            "model": model,
            "llm.execution_id": execution_id,
            "llm.attempt": llm_request.attempt,
        }
        if llm_response.usage:
            response_metadata["llm_usage"] = dict(llm_response.usage)
            llm_calls = llm_response.usage.get("requests")
            if isinstance(llm_calls, int):
                response_metadata["llm_calls"] = llm_calls
                response_metadata["llm.retry_count"] = max(0, llm_calls - 1)
            input_tokens = llm_response.usage.get("input_tokens")
            if isinstance(input_tokens, int):
                response_metadata["input_tokens"] = input_tokens
            output_tokens = llm_response.usage.get("output_tokens")
            if isinstance(output_tokens, int):
                response_metadata["output_tokens"] = output_tokens
        if llm_response.status == ResponseStatus.SUCCESS:
            return Response(
                success=True, data=llm_response.data, metadata=response_metadata
            )

        failure = self._map_llm_failure(llm_response)
        failure.metadata.update(response_metadata)
        return failure

    @property
    def block_type(self) -> str:
        """Return the stable block type identifier."""

        return "llm_primitive"

    def stats_identity(self) -> BlockStatsIdentity:
        """Return the stable stats identity for this block."""

        return BlockStatsIdentity(
            block_name=self.name, block_type=self.block_type, version=None
        )

    def estimate_execution(self, request: Request) -> BlockEstimate:
        """Return a side-effect-free estimate for this block."""
        if self._stats_adapter is None:
            self._stats_adapter = LiteLLMStatsAdapter(get_default_store())
        identity = self.stats_identity()
        prior = self._build_prior_estimate(identity, request)
        return self._stats_adapter.estimate(identity, request, prior)

    def _build_attempt_record(
        self, request: Request, response: Response, duration_ms: float
    ) -> "BlockAttemptRecord":
        """Build a stats record for an LLM execution attempt."""

        record = super()._build_attempt_record(request, response, duration_ms)
        model = response.metadata.get("model") or self._model
        llm_calls = response.metadata.get("llm_calls")
        input_tokens = response.metadata.get("input_tokens")
        output_tokens = response.metadata.get("output_tokens")
        return record.model_copy(
            update={
                "llm_calls": int(llm_calls) if isinstance(llm_calls, int) else 1,
                "model": str(model) if model is not None else None,
                "input_tokens": int(input_tokens)
                if isinstance(input_tokens, int)
                else None,
                "output_tokens": int(output_tokens)
                if isinstance(output_tokens, int)
                else None,
                "block_executions": 1,
            }
        )

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

    def _build_llm_request(
        self,
        request: Request,
        messages: List[Dict[str, str]],
        model: str,
        execution_id: str,
        attempt: int,
        api_base: Optional[str],
        api_key: Optional[SecretStr],
    ) -> LLMRequest:
        """Build the internal LLM request payload.

        Args:
            request: Block request driving the LLM call.
            messages: Message list for the LLM call.
            model: Selected model identifier.
            execution_id: Unique execution identifier for auditing.
            attempt: Internal attempt number for the LLM call.
            api_base: Optional API base for proxy routing.
            api_key: Optional API key for provider access.

        Returns:
            An LLMRequest instance.
        """

        metadata = dict(request.metadata)
        metadata.setdefault("block_name", self.name)
        return LLMRequest(
            messages=messages,
            output_data_model=self._output_data_model,
            model=model,
            temperature=self._temperature,
            execution_id=execution_id,
            attempt=attempt,
            metadata=metadata,
            api_base=api_base,
            api_key=api_key,
        )

    def _build_prior_estimate(
        self, identity: BlockStatsIdentity, request: Request
    ) -> BlockEstimate:
        """Build a cold-start estimate for LLM execution.

        Args:
            identity: Stable block identity metadata.
            request: Request to estimate.

        Returns:
            A BlockEstimate built from conservative priors.
        """

        prompt = ""
        try:
            prompt = self._coerce_payload(request.payload)
        except ValueError:
            prompt = ""
        estimated_input_tokens = max(0, len(prompt) // 4)
        notes = [
            f"estimated_input_tokens={estimated_input_tokens}",
            "estimated_output_tokens=256",
            "pricing_unknown_prior",
        ]
        return BlockEstimate.from_prior(
            identity,
            time_ms_mean=750.0,
            time_ms_std=400.0,
            cost_usd_mean=0.01,
            cost_usd_std=0.02,
            expected_llm_calls=1.0,
            expected_block_executions=1.0,
            notes=notes,
        )

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
            details=build_exception_details(error),
            error_type=error_type,
        )

    def _map_llm_failure(self, response: LLMResponse) -> Response:
        """Map an internal LLM response failure to a block Response."""

        reason = response.reason or "llm_execution_failed"
        error_type = response.error_type or Exception
        details = sanitize_error_details(response.error_details)
        return Response(
            success=False,
            reason=reason,
            details=details,
            error_type=error_type,
        )

    def _build_execution_id(self) -> str:
        """Build a unique execution identifier for auditing."""

        return f"{self.name}-{uuid4().hex[:8]}"

    def _resolve_api_settings(self) -> tuple[Optional[str], Optional[SecretStr]]:
        """Resolve API base and key for OpenAI-compatible routing."""

        if self._config.use_litellm_proxy():
            api_base = self._config.get_litellm_proxy_url()
            api_key_value = (
                self._config.get_litellm_proxy_api_key()
                or self._config.get_openai_api_key()
            )
            return api_base, SecretStr(api_key_value) if api_key_value else None

        api_key_value = self._config.get_openai_api_key()
        return None, SecretStr(api_key_value) if api_key_value else None
