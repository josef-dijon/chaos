from typing import TYPE_CHECKING, Callable, Optional

from chaos.domain.error_sanitizer import build_exception_details
from chaos.domain.messages import Request, Response
from chaos.domain.policy import (
    BubblePolicy,
    DebugPolicy,
    RecoveryPolicy,
    RecoveryType,
    RepairPolicy,
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
        if isinstance(policy, RepairPolicy):
            return PolicyHandler.repair(policy, block, request, failure)
        elif isinstance(policy, DebugPolicy):
            return PolicyHandler.debug(policy, request, failure)
        elif isinstance(policy, BubblePolicy):
            return PolicyHandler.bubble(failure)
        else:
            # Fallback for when type field matches but class doesn't (deserialization edge cases)
            # or just simple duck typing check
            if policy.type == RecoveryType.REPAIR:
                return PolicyHandler.repair(policy, block, request, failure)  # type: ignore
            if policy.type == RecoveryType.DEBUG:
                return PolicyHandler.debug(policy, request, failure)  # type: ignore
            if policy.type == RecoveryType.BUBBLE:
                return PolicyHandler.bubble(failure)

            return Response(
                success=False,
                reason=f"unknown_policy_type:{policy.type}",
                details={"policy_type": str(policy.type)},
                error_type=Exception,
            )

    @staticmethod
    def repair(
        policy: RepairPolicy, block: "Block", request: Request, failure: Response
    ) -> Response:
        """Apply a repair function to the request and re-execute."""
        try:
            repair_func = RepairRegistry.get(policy.repair_function)
            repaired_request = repair_func(request, failure)
            merged = repaired_request.model_copy(deep=True)
            merged.metadata = {
                **dict(request.metadata or {}),
                **dict(repaired_request.metadata or {}),
            }
            return block.execute(merged)
        except Exception as e:
            return Response(
                success=False,
                reason="repair_execution_failed",
                details={
                    "repair_function": policy.repair_function,
                    "error": build_exception_details(e),
                },
                error_type=Exception,
            )

    @staticmethod
    def debug(policy: DebugPolicy, request: Request, failure: Response) -> Response:
        """Enter debug mode (stub).

        The returned response includes enough metadata to correlate the debug event
        to the attempt that produced the failure.
        """
        # In a real CLI, this might drop into a pdb shell or wait for user input
        return Response(
            success=False,
            reason="debug_breakpoint_hit",
            details={"original_error": failure.model_dump()},
            metadata=dict(request.metadata or {}),
            error_type=Exception,
        )

    @staticmethod
    def bubble(failure: Response) -> Response:
        """Return the failure as-is (escalate)."""
        return failure
