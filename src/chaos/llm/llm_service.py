from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel
from pydantic import SecretStr

from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore

from chaos.domain.error_sanitizer import build_exception_details
from chaos.llm.llm_error_mapper import is_known_llm_error, map_llm_error
from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_response import LLMResponse
from chaos.llm.response_status import ResponseStatus

logger = logging.getLogger(__name__)


class LLMService:
    """LLM execution service implemented via PydanticAI.

    PydanticAI is responsible for structured-output validation retries.
    """

    def __init__(
        self,
        output_retries: int = 2,
        api_max_retries: int = 2,
        model_builder: Optional[Callable[[LLMRequest], OpenAIChatModel]] = None,
    ) -> None:
        """Initialize the LLM service.

        Args:
            output_retries: Number of PydanticAI output validation retries.
            api_max_retries: Number of API retries performed by the provider SDK.
            model_builder: Optional override for building the PydanticAI model.
        """

        self._output_retries = max(0, int(output_retries))
        self._api_max_retries = max(0, int(api_max_retries))
        self._model_builder = model_builder

    def execute(self, request: LLMRequest) -> LLMResponse:
        """Execute the LLM call and return a structured response.

        Args:
            request: LLM request to execute.

        Returns:
            LLMResponse containing success or failure information.
        """

        try:
            system_prompt, user_prompt = self._render_prompts(request.messages)
            data, usage = self._run_agent(
                request=request,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return LLMResponse.success(data=data, raw_output=None, usage=usage)
        except Exception as exc:
            if is_known_llm_error(exc):
                mapping = map_llm_error(exc)
                return LLMResponse.failure(
                    status=mapping.status,
                    reason=mapping.reason,
                    error_type=mapping.error_type,
                    error_details=mapping.details,
                )
            metadata = request.metadata or {}
            logger.exception(
                "Unexpected LLM execution error",
                extra={
                    "request_id": metadata.get("id"),
                    "trace_id": metadata.get("trace_id"),
                    "run_id": metadata.get("run_id"),
                    "span_id": metadata.get("span_id"),
                    "model": request.model,
                },
            )
            return LLMResponse.failure(
                status=ResponseStatus.MECHANICAL_ERROR,
                reason="internal_error",
                error_type=type(exc),
                error_details=build_exception_details(exc),
            )

    def _render_prompts(
        self, messages: List[Dict[str, str]]
    ) -> tuple[Optional[str], str]:
        """Render OpenAI-style role messages into system + user prompts.

        Args:
            messages: OpenAI-style role/content messages.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """

        system_parts: list[str] = []
        non_system: list[Dict[str, str]] = []
        for message in messages:
            role = (message.get("role") or "").strip()
            content = (message.get("content") or "").strip()
            if not content:
                continue
            if role == "system":
                system_parts.append(content)
            else:
                non_system.append({"role": role, "content": content})

        system_prompt = "\n\n".join(system_parts).strip() or None

        if len(non_system) == 1 and non_system[0].get("role") == "user":
            return system_prompt, non_system[0]["content"]

        rendered: list[str] = []
        for msg in non_system:
            role = msg.get("role") or "user"
            label = role.capitalize()
            rendered.append(f"{label}: {msg.get('content', '')}")
        return system_prompt, "\n\n".join(rendered).strip()

    def _run_agent(
        self,
        request: LLMRequest,
        system_prompt: Optional[str],
        user_prompt: str,
    ) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Run PydanticAI and return validated output + usage.

        This is isolated for testability: unit tests should patch this method.

        Args:
            request: Internal LLMRequest.
            system_prompt: Optional system prompt.
            user_prompt: User prompt content.

        Returns:
            Tuple of (validated_data, usage_dict).
        """

        model = self._build_model(request)
        agent = Agent(
            model,
            system_prompt=system_prompt or (),
            output_type=request.output_data_model,
            output_retries=self._output_retries,
        )
        metadata = request.metadata or {}
        logger.info(
            "LLM request start",
            extra={
                "request_id": metadata.get("id"),
                "trace_id": metadata.get("trace_id"),
                "run_id": metadata.get("run_id"),
                "span_id": metadata.get("span_id"),
                "model": request.model,
            },
        )
        result = agent.run_sync(
            user_prompt,
            model_settings=ModelSettings(temperature=request.temperature),
        )
        logger.info(
            "LLM request complete",
            extra={
                "request_id": metadata.get("id"),
                "trace_id": metadata.get("trace_id"),
                "run_id": metadata.get("run_id"),
                "span_id": metadata.get("span_id"),
                "model": request.model,
            },
        )

        output = result.output
        if isinstance(output, BaseModel):
            data = output.model_dump()
        elif isinstance(output, dict):
            data = output
        else:
            raise TypeError(f"Unexpected PydanticAI output type: {type(output)}")

        usage_obj = result.usage()
        usage = {
            "requests": getattr(usage_obj, "requests", None),
            "input_tokens": getattr(usage_obj, "input_tokens", None),
            "output_tokens": getattr(usage_obj, "output_tokens", None),
        }
        usage = {k: v for k, v in usage.items() if v is not None}
        return data, usage or None

    def _build_model(self, request: LLMRequest) -> OpenAIChatModel:
        """Build the PydanticAI model for a request.

        Args:
            request: LLM request describing the target model and credentials.

        Returns:
            An OpenAIChatModel configured for direct or proxy (LiteLLM) usage.
        """

        if self._model_builder is not None:
            return self._model_builder(request)

        if AsyncOpenAI is None:  # pragma: no cover
            # This should not happen in production since `pydantic-ai-slim[openai]`
            # installs the OpenAI SDK.
            return OpenAIChatModel(request.model)

        api_key = self._resolve_api_key(request.api_key) or os.environ.get(
            "OPENAI_API_KEY"
        )
        if api_key is None:
            # Allow tests and callers to inject an already-configured model via
            # `model_builder`, and avoid instantiating the OpenAI SDK client
            # without credentials.
            return OpenAIChatModel(request.model)

        client_kwargs: Dict[str, Any] = {
            "api_key": api_key,
            "max_retries": self._api_max_retries,
        }
        if request.api_base:
            # OpenAI-compatible proxy base url (e.g. LiteLLM proxy).
            client_kwargs["base_url"] = request.api_base

        openai_client = AsyncOpenAI(**client_kwargs)
        provider = OpenAIProvider(openai_client=openai_client)
        return OpenAIChatModel(request.model, provider=provider)

    @staticmethod
    def _resolve_api_key(api_key: Optional[Any]) -> Optional[str]:
        """Resolve a secret or plain API key to a string."""

        if api_key is None:
            return None
        if isinstance(api_key, SecretStr):
            return api_key.get_secret_value()
        if isinstance(api_key, str):
            return api_key
        return str(api_key)
