from typing import Any, Callable, Dict, Optional, Tuple

from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)


class StableTransportError(Exception):
    """Raised when StableTransport exhausts retries."""


class StableTransport:
    """Retry-capable transport wrapper for LLM calls."""

    def __init__(
        self,
        completion_callable: Callable[..., Any],
        retry_exceptions: Optional[Tuple[type[Exception], ...]] = None,
        max_attempts: int = 1,
        wait_strategy: Optional[Any] = None,
    ) -> None:
        """Initialize the transport wrapper.

        Args:
            completion_callable: Callable used to execute an LLM request.
            retry_exceptions: Exception types eligible for retry.
            max_attempts: Maximum attempts including the initial call.
            wait_strategy: Tenacity wait strategy for backoff.
        """

        self._completion_callable = completion_callable
        self._retry_exceptions = retry_exceptions or ()
        self._max_attempts = max(1, max_attempts)
        self._wait_strategy = wait_strategy or wait_fixed(0)

    def complete(self, call_args: Dict[str, Any]) -> Any:
        """Execute the LLM call with retry handling.

        Args:
            call_args: Keyword arguments for the completion callable.

        Returns:
            The raw response from the completion callable.
        """

        if self._max_attempts == 1 or not self._retry_exceptions:
            return self._completion_callable(**call_args)

        retrying = Retrying(
            stop=stop_after_attempt(self._max_attempts),
            retry=retry_if_exception_type(self._retry_exceptions),
            wait=self._wait_strategy,
            reraise=False,
        )
        try:
            return retrying(self._completion_callable, **call_args)
        except RetryError as exc:
            raise StableTransportError(str(exc)) from exc
