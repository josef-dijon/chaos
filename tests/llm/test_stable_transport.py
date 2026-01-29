import pytest

from chaos.llm.stable_transport import StableTransport, StableTransportError


class TransientError(Exception):
    pass


def test_stable_transport_retries_until_success() -> None:
    """Ensure StableTransport retries eligible exceptions."""

    calls = {"count": 0}

    def flaky_completion(**kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TransientError("temporary")
        return "ok"

    transport = StableTransport(
        flaky_completion, retry_exceptions=(TransientError,), max_attempts=3
    )
    result = transport.complete({})

    assert result == "ok"
    assert calls["count"] == 3


def test_stable_transport_raises_after_retries() -> None:
    """Ensure StableTransport raises after exhausting retries."""

    def failing_completion(**kwargs):
        raise TransientError("always failing")

    transport = StableTransport(
        failing_completion, retry_exceptions=(TransientError,), max_attempts=2
    )

    with pytest.raises(StableTransportError):
        transport.complete({})


def test_stable_transport_no_retry_passes_through() -> None:
    """Ensure StableTransport does not retry when disabled."""

    def failing_completion(**kwargs):
        raise TransientError("no retry")

    transport = StableTransport(failing_completion)

    with pytest.raises(TransientError):
        transport.complete({})
