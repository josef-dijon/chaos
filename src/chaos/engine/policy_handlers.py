from typing import TYPE_CHECKING, Callable, Optional

from chaos.domain.messages import Request, Response
from chaos.domain.policy import (
    BubblePolicy,
    DebugPolicy,
    RecoveryPolicy,
    RecoveryType,
    RepairPolicy,
    RetryPolicy,
)
from chaos.engine.registry import RepairRegistry

if TYPE_CHECKING:
    from chaos.domain.block import Block


class PolicyHandler:
    """Base class/Namespace for recovery policy execution logic."""

    @staticmethod
    def handle(
        policy: RecoveryPolicy,
        block: "Block",
        request: Request,
        failure: Response,
    ) -> Response:
        """Dispatch to the specific handler based on policy type."""
        if isinstance(policy, RetryPolicy):
            return PolicyHandler.retry(policy, block, request)
        elif isinstance(policy, RepairPolicy):
            return PolicyHandler.repair(policy, block, request, failure)
        elif isinstance(policy, DebugPolicy):
            return PolicyHandler.debug(policy, failure)
        elif isinstance(policy, BubblePolicy):
            return PolicyHandler.bubble(failure)
        else:
            # Fallback for when type field matches but class doesn't (deserialization edge cases)
            # or just simple duck typing check
            if policy.type == RecoveryType.RETRY:
                return PolicyHandler.retry(policy, block, request)  # type: ignore
            if policy.type == RecoveryType.REPAIR:
                return PolicyHandler.repair(policy, block, request, failure)  # type: ignore
            if policy.type == RecoveryType.DEBUG:
                return PolicyHandler.debug(policy, failure)  # type: ignore
            if policy.type == RecoveryType.BUBBLE:
                return PolicyHandler.bubble(failure)

            return Response(
                success=False,
                reason=f"unknown_policy_type:{policy.type}",
                details={"policy_type": str(policy.type)},
            )

    @staticmethod
    def retry(policy: RetryPolicy, block: "Block", request: Request) -> Response:
        """Execute the block again, respecting max_attempts."""
        # Note: In a real async system, we would sleep here (policy.delay_seconds)
        # For now, this is a direct recursive call (simple retry)
        # TODO: track attempt count in metadata to prevent infinite loops if not handled by caller

        # We assume the caller (composite) tracks the number of attempts.
        # But wait, if the policy itself has 'max_attempts', the caller needs to know
        # how many times we've tried *this specific policy*.

        # For this primitive implementation, let's just re-execute once per call.
        # The composite loop is responsible for the "looping" part.
        return block.execute(request)

    @staticmethod
    def repair(
        policy: RepairPolicy, block: "Block", request: Request, failure: Response
    ) -> Response:
        """Apply a repair function to the request and re-execute."""
        try:
            repair_func = RepairRegistry.get(policy.repair_function)
            new_request = repair_func(request, failure)
            return block.execute(new_request)
        except Exception as e:
            return Response(
                success=False,
                reason="repair_execution_failed",
                details={"repair_function": policy.repair_function, "error": str(e)},
            )

    @staticmethod
    def debug(policy: DebugPolicy, failure: Response) -> Response:
        """Enter debug mode (stub)."""
        # In a real CLI, this might drop into a pdb shell or wait for user input
        return Response(
            success=False,
            reason="debug_breakpoint_hit",
            details={"original_error": failure.model_dump()},
        )

    @staticmethod
    def bubble(failure: Response) -> Response:
        """Return the failure as-is (escalate)."""
        return failure
