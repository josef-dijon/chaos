from typing import Protocol

from chaos.llm.llm_request import LLMRequest
from chaos.llm.llm_response import LLMResponse


class LLMExecutor(Protocol):
    """Protocol for executing a structured-output LLM request."""

    def execute(self, request: LLMRequest) -> LLMResponse:
        """Execute an LLM request.

        Args:
            request: Request to execute.

        Returns:
            LLMResponse describing success or failure.
        """

        ...
