class ChaosError(Exception):
    """Base exception for the Chaos system."""

    pass


class LLMError(ChaosError):
    """Base exception for LLM interaction failures."""

    pass


class SchemaError(LLMError):
    """Output could not be parsed into the required schema."""

    pass


class RateLimitError(LLMError):
    """Provider returned 429 Rate Limit Exceeded."""

    pass


class ApiKeyError(LLMError):
    """Provider returned 401/403 Authentication Error."""

    pass


class ContextLengthError(LLMError):
    """Prompt exceeded model context limits."""

    pass
