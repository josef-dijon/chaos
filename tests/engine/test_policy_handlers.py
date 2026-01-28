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

        assert response.success() is True
        assert response.data == "fixed"
    finally:
        RepairRegistry.clear()


def test_policy_handler_repair_not_found():
    block = DummyBlock("dummy")
    policy = RepairPolicy(repair_function="missing_func")
    failure = Response(success=False, reason="oops")

    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success() is False
    assert response.reason == "repair_execution_failed"
    assert "not found" in str(response.details["error"])


def test_policy_handler_debug():
    block = DummyBlock("dummy")
    policy = DebugPolicy()
    failure = Response(success=False, reason="oops")

    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success() is False
    assert response.reason == "debug_breakpoint_hit"
    assert response.details["original_error"]["reason"] == "oops"


def test_policy_handler_bubble():
    block = DummyBlock("dummy")
    # BubblePolicy defaults to BUBBLE type
    policy = BubblePolicy()  # type: ignore (Pydantic init)

    failure = Response(success=False, reason="escalate me")
    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success() is False
    assert response.reason == "escalate me"

    block = DummyBlock("dummy")
    policy = DebugPolicy()
    failure = Response(success=False, reason="oops")

    response = PolicyHandler.handle(policy, block, Request(), failure)

    assert response.success() is False
    assert response.reason == "debug_breakpoint_hit"


def test_policy_handler_unknown():
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

    assert response.success() is False
    assert response.reason and "unknown_policy_type" in response.reason
