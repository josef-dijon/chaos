from chaos.domain.messages import Request


class ModelSelector:
    """Selects a model for LLM execution."""

    def select_model(self, request: Request, default_model: str) -> str:
        """Return the selected model for the request.

        Args:
            request: Block request driving the LLM call.
            default_model: Default model configured for the primitive.

        Returns:
            Selected model identifier.
        """

        del request
        return default_model
