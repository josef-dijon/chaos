from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

from pydantic import BaseModel

from chaos.config import Config
from chaos.domain.block import Block
from chaos.domain.block_estimate import BlockEstimate
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
from chaos.llm.litellm_stats_adapter import LiteLLMStatsAdapter
from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_response import LLMResponse
from chaos.llm.llm_service import LLMService
from chaos.llm.model_selector import ModelSelector
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
        llm_service: Optional[LLMService] = None,
        model_selector: Optional[ModelSelector] = None,
        use_instructor: bool = True,
        max_repair_attempts: int = 2,
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
            llm_service: Optional LLM service override.
            model_selector: Optional model selector override.
            use_instructor: Whether to use instructor for schema enforcement.
            max_repair_attempts: Number of semantic repair attempts.
        """
        self._config = config or Config.load()
        resolved_model = model or self._config.get_model_name()
        super().__init__(name, side_effect_class="idempotent")
        self._system_prompt = system_prompt
        self._output_data_model = output_data_model
        self._model = resolved_model
        self._temperature = temperature
        self._stats_adapter = stats_adapter or LiteLLMStatsAdapter(get_default_store())
        self._llm_service = llm_service or LLMService(use_instructor=use_instructor)
        self._model_selector = model_selector or ModelSelector()
        self._max_repair_attempts = max(0, max_repair_attempts)

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
        model = self._model_selector.select_model(request, self._model)
        manager_id = self._build_manager_id()
        api_base, api_key = self._resolve_api_settings()

        max_attempts = 1 + self._max_repair_attempts
        attempt = 1
        while attempt <= max_attempts:
            llm_request = self._build_llm_request(
                request=request,
                messages=messages,
                model=model,
                manager_id=manager_id,
                attempt=attempt,
                api_base=api_base,
                api_key=api_key,
            )
            llm_response = self._llm_service.execute(llm_request)
            if llm_response.status == ResponseStatus.SUCCESS:
                return Response(success=True, data=llm_response.data)
            if (
                llm_response.status == ResponseStatus.SEMANTIC_ERROR
                and attempt < max_attempts
            ):
                messages = self._append_validation_feedback(
                    messages, llm_response.error_details
                )
                attempt += 1
                continue
            return self._map_llm_failure(llm_response)

        return Response(
            success=False,
            reason="llm_execution_failed",
            details={"error": "LLM execution failed"},
            error_type=Exception,
        )

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

        identity = self.stats_identity()
        prior = self._build_prior_estimate(identity, request)
        return self._stats_adapter.estimate(identity, request, prior)

    def _build_attempt_record(
        self, request: Request, response: Response, duration_ms: float
    ) -> "BlockAttemptRecord":
        """Build a stats record for an LLM execution attempt."""

        record = super()._build_attempt_record(request, response, duration_ms)
        return record.model_copy(
            update={"llm_calls": 1, "model": self._model, "block_executions": 1}
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
        manager_id: str,
        attempt: int,
        api_base: Optional[str],
        api_key: Optional[str],
    ) -> LLMRequest:
        """Build the internal LLM request payload.

        Args:
            request: Block request driving the LLM call.
            messages: Message list for the LLM call.
            model: Selected model identifier.
            manager_id: Unique manager identifier for auditing.
            attempt: Internal attempt number for the LLM call.
            api_base: Optional API base for proxy routing.
            api_key: Optional API key for provider access.

        Returns:
            An LLMRequest instance.
        """

        metadata = dict(request.metadata)
        metadata["manager_id"] = manager_id
        metadata.setdefault("block_name", self.name)
        metadata["block_attempt"] = int(request.metadata.get("attempt", 1))
        metadata["llm_attempt"] = attempt
        return LLMRequest(
            messages=messages,
            output_data_model=self._output_data_model,
            model=model,
            temperature=self._temperature,
            manager_id=manager_id,
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
            details={"error": str(error)},
            error_type=error_type,
        )

    def _append_validation_feedback(
        self, messages: List[Dict[str, str]], error_details: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Append validation feedback to the message list.

        Args:
            messages: Existing message list.
            error_details: Error details from the failed validation.

        Returns:
            Updated message list including validation feedback.
        """

        feedback = self._format_validation_feedback(error_details)
        return messages + [{"role": "user", "content": feedback}]

    def _format_validation_feedback(self, error_details: Dict[str, Any]) -> str:
        """Format validation feedback for the LLM repair loop."""

        error_text = error_details.get("error", "Unknown validation error")
        return (
            "The previous response failed validation. "
            f"Validation error: {error_text}. "
            "Please respond with valid JSON matching the required schema."
        )

    def _map_llm_failure(self, response: LLMResponse) -> Response:
        """Map an internal LLM response failure to a block Response."""

        reason = response.reason or "llm_execution_failed"
        error_type = response.error_type or Exception
        return Response(
            success=False,
            reason=reason,
            details=response.error_details,
            error_type=error_type,
        )

    def _build_manager_id(self) -> str:
        """Build a unique manager identifier for auditing."""

        return f"{self.name}-{uuid4().hex[:8]}"

    def _resolve_api_settings(self) -> tuple[Optional[str], Optional[str]]:
        """Resolve API base and key for LiteLLM usage."""

        if self._config.use_litellm_proxy():
            api_base = self._config.get_litellm_proxy_url()
            api_key = (
                self._config.get_litellm_proxy_api_key()
                or self._config.get_openai_api_key()
            )
            return api_base, api_key

        return None, self._config.get_openai_api_key()

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
