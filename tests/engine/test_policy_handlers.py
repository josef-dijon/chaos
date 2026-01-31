from chaos.domain.block import Block
from chaos.domain.messages import Request, Response
from chaos.domain.policy import BubblePolicy, DebugPolicy, RepairPolicy, RecoveryType
from chaos.engine.policy_handlers import PolicyHandler
from chaos.engine.registry import RepairRegistry


class DummyBlock(Block):
    def build(self) -> None:
        pass

    def _execute_primitive(self, request: Request):
        if request.payload.get("fixed"):
            return Response(success=True, data="fixed")
        return Response(success=False, reason="fail")


def test_policy_handler_repair_success():
    """Executes repair policy successfully."""

    # Setup registry
    @RepairRegistry.register("fix_it")
    def fix_request(request: Request, failure: Response) -> Request:
        # Clone and modify
        new_payload = request.payload.copy()
        new_payload["fixed"] = True
        return Request(payload=new_payload)

    try:
        block = DummyBlock("dummy")
        policy = RepairPolicy(repair_function="fix_it")
        failure = Response(success=False, reason="oops")

        response = PolicyHandler.handle(policy, block, Request(), failure)

        assert response.success is True
        assert response.data == "fixed"
    finally:
        RepairRegistry.clear()


def test_policy_handler_repair_not_found():
    """Returns failure when repair function is missing."""
    block = DummyBlock("dummy")
    policy = RepairPolicy(repair_function="missing_func")
    failure = Response(success=False, reason="oops")

    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success is False
    assert response.reason == "repair_execution_failed"
    assert "not found" in str(response.details["error"])


def test_policy_handler_debug():
    """Returns a debug breakpoint response."""
    block = DummyBlock("dummy")
    policy = DebugPolicy()
    failure = Response(success=False, reason="oops")

    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success is False
    assert response.reason == "debug_breakpoint_hit"
    assert response.details["original_error"]["reason"] == "oops"


def test_policy_handler_debug_includes_request_metadata() -> None:
    """Preserves request metadata in debug responses."""
    block = DummyBlock("dummy")
    policy = DebugPolicy()
    failure = Response(success=False, reason="oops")
    request = Request(metadata={"trace_id": "t", "span_id": "s", "attempt": 3})

    response = PolicyHandler.handle(policy, block, request, failure)

    assert response.metadata["trace_id"] == "t"
    assert response.metadata["span_id"] == "s"
    assert response.metadata["attempt"] == 3


def test_policy_handler_repair_merges_request_metadata_into_execution() -> None:
    """Merges original metadata into repaired execution."""
    captured: dict = {}

    class CaptureBlock(Block):
        def build(self) -> None:
            pass

        def _execute_primitive(self, request: Request):
            captured.update(request.metadata)
            return Response(success=True, data="ok")

    @RepairRegistry.register("fix_payload")
    def fix_request(request: Request, failure: Response) -> Request:
        return Request(payload={"fixed": True})

    try:
        block = CaptureBlock("cap")
        policy = RepairPolicy(repair_function="fix_payload")
        failure = Response(success=False, reason="oops")
        request = Request(metadata={"trace_id": "t", "run_id": "r"})

        response = PolicyHandler.handle(policy, block, request, failure)

        assert response.success is True
        assert captured.get("trace_id") == "t"
        assert captured.get("run_id") == "r"
    finally:
        RepairRegistry.clear()


def test_policy_handler_bubble():
    """Bubbles failures without additional handling."""
    block = DummyBlock("dummy")
    # BubblePolicy defaults to BUBBLE type
    policy = BubblePolicy()  # type: ignore (Pydantic init)

    failure = Response(success=False, reason="escalate me")
    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success is False
    assert response.reason == "escalate me"

    block = DummyBlock("dummy")
    policy = DebugPolicy()
    failure = Response(success=False, reason="oops")

    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success is False
    assert response.reason == "debug_breakpoint_hit"


def test_policy_handler_unknown():
    """Returns failure for unknown policy types."""
    # Test defensive coding for unknown policy types
    block = DummyBlock("dummy")
    # Use base class to avoid isinstance() matching specific subclasses
    from chaos.domain.policy import RecoveryPolicy

    # We need to bypass Pydantic validation if we want to inject an invalid enum
    # Or just use a valid enum that isn't handled if we had one (but we handle all).
    # Actually, we can just pass a policy object that isn't one of the known subclasses
    # but has a type that confuses the handler?

    # In the new implementation, we check isinstance first.
    # So if we pass a generic RecoveryPolicy with type=DEBUG, it might fail the isinstance checks
    # and fall through to the else block.

    # Let's try to construct a raw RecoveryPolicy with a type that is valid Enum but not handled?
    # No, we handle all Enums.

    # Let's constructing a RecoveryPolicy that is NOT a subclass of the others
    # but has type=RETRY. The code should catch it in the else block and handle it via duck typing.

    # But wait, the test is asserting "Unknown policy type".
    # That only happens if it falls through ALL checks, including the duck typing ones.
    # So we need a policy where type is NOT one of the known enum values?
    # That requires bypassing Pydantic validation.

    policy = RecoveryPolicy.model_construct(type="UNKNOWN_TYPE")  # type: ignore

    failure = Response(success=False, reason="oops")
    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success is False
    assert response.reason and "unknown_policy_type" in response.reason
