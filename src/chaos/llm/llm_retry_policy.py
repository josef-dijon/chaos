from tenacity import wait_exponential_jitter

try:
    from litellm import (
        APIConnectionError,
        BadGatewayError,
        InternalServerError,
        RateLimitError,
        RouterRateLimitError,
        ServiceUnavailableError,
        Timeout,
    )
except ImportError:  # pragma: no cover
    APIConnectionError = None
    BadGatewayError = None
    InternalServerError = None
    RateLimitError = None
    RouterRateLimitError = None
    ServiceUnavailableError = None
    Timeout = None

DEFAULT_MAX_ATTEMPTS = 3


def default_retry_exceptions() -> tuple[type[Exception], ...]:
    """Return the default retryable exception set."""

    candidates = (
        RateLimitError,
        RouterRateLimitError,
        ServiceUnavailableError,
        InternalServerError,
        BadGatewayError,
        APIConnectionError,
        Timeout,
    )
    return tuple(candidate for candidate in candidates if candidate is not None)


def default_wait_strategy():
    """Return the default tenacity wait strategy."""

    return wait_exponential_jitter(initial=1.0, max=8.0)
