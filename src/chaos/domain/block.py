from abc import ABC, abstractmethod
import logging
from time import perf_counter, sleep
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

from chaos.domain.block_estimate import BlockEstimate
from chaos.domain.error_sanitizer import build_exception_details
from chaos.domain.messages import Request, Response
from chaos.domain.policy import (
    BubblePolicy,
    RecoveryPolicy,
    RecoveryType,
    RepairPolicy,
    RetryPolicy,
)
from chaos.domain.state import BlockState
from chaos.engine.conditions import ConditionRegistry
from chaos.engine.policy_handlers import PolicyHandler
from chaos.engine.registry import RepairRegistry
from chaos.stats.block_attempt_record import BlockAttemptRecord
from chaos.stats.block_stats_store import BlockStatsStore
from chaos.stats.block_stats_identity import BlockStatsIdentity
from chaos.stats.store_registry import get_default_store

logger = logging.getLogger(__name__)


class Block(ABC):
    """Base class defining the contract and default behavior for all blocks.

    A Block can be either:
    1. A Composite Block: Has `nodes` and runs a graph execution loop.
    2. A Primitive Block: Has no `nodes` and executes atomic work (overrides _execute_primitive).
    """

    def __init__(
        self,
        name: str,
        nodes: Optional[Dict[str, "Block"]] = None,
        entry_point: Optional[str] = None,
        transitions: Optional[Dict[str, Any]] = None,
        max_steps: int = 128,
        side_effect_class: str = "none",
        stats_store: Optional[BlockStatsStore] = None,
    ):
        """Initialize a block.

        Args:
            name: Stable identifier for this block instance.
            nodes: Optional mapping of node name -> child block. If provided, this block is a composite.
            entry_point: Starting node name for a composite block.
            transitions: Optional mapping of node name -> transition configuration.
            max_steps: Maximum number of graph steps allowed for a composite execution.
            side_effect_class: Side-effect classification for retry safety.
                Allowed values: "none", "idempotent", "non_idempotent".
            stats_store: Optional stats store override for recording attempts.
        """
        self._name = name
        self._state = BlockState.READY
        self._nodes = nodes
        self._entry_point = entry_point
        self._transitions = transitions or {}
        self._max_steps = max_steps
        self._side_effect_class = self._normalize_side_effect_class(side_effect_class)
        self._stats_store = stats_store
        self._graph_validated = False
        self._graph_validation: Optional[Response] = None

        # Allow subclasses to configure the graph
        self.build()

    @abstractmethod
    def build(self) -> None:
        """Construct the block's internal graph or configuration.

        This method is called at the end of __init__. Subclasses must implement this
        to set up nodes and transitions (for composites) or perform other initialization.
        """
        pass

    def set_graph(
        self,
        nodes: Dict[str, "Block"],
        entry_point: str,
        transitions: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Configure the graph for this composite block.

        Args:
            nodes: Mapping of node name to Block instance.
            entry_point: Name of the start node.
            transitions: Transition configuration.
        """
        self._nodes = nodes
        self._entry_point = entry_point
        self._transitions = transitions or {}
        self._graph_validated = False
        self._graph_validation = None

    @property
    def name(self) -> str:
        """Stable identifier for this block instance."""
        return self._name

    @property
    def block_type(self) -> str:
        """Stable type identifier for this block."""

        return self.__class__.__name__

    @property
    def state(self) -> BlockState:
        """Current execution state."""
        return self._state

    @property
    def nodes(self) -> Optional[Dict[str, "Block"]]:
        """Child node map for composite blocks."""
        return self._nodes

    @property
    def side_effect_class(self) -> str:
        """Return the side-effect classification for this block.

        This value is used by recovery logic to determine whether retry/repair is safe.
        """

        return self._side_effect_class

    def execute(self, request: Request) -> Response:
        """Execute the block.

        If this block has nodes, it acts as a composite block and runs the graph loop.
        If it has no nodes, it calls _execute_primitive() for atomic work.
        """
        self._state = BlockState.BUSY
        start_time = perf_counter()
        response: Optional[Response] = None
        request_for_execution = self._with_base_metadata(request)
        try:
            if self._nodes is not None:
                response = self._execute_graph(request_for_execution)
            else:
                response = self._execute_primitive(request_for_execution)
        except Exception as e:
            metadata = request_for_execution.metadata
            logger.exception(
                "Block execution failed",
                extra={
                    "block_name": self.name,
                    "node_name": metadata.get("node_name"),
                    "request_id": metadata.get("id"),
                    "trace_id": metadata.get("trace_id"),
                    "run_id": metadata.get("run_id"),
                    "span_id": metadata.get("span_id"),
                    "parent_span_id": metadata.get("parent_span_id"),
                    "attempt": metadata.get("attempt"),
                },
            )
            response = Response(
                success=False,
                reason="internal_error",
                details=build_exception_details(e),
                error_type=type(e),
            )
        finally:
            self._state = BlockState.READY
            duration_ms = (perf_counter() - start_time) * 1000
            if response is not None:
                self._attach_correlation_metadata(request_for_execution, response)
                response.metadata["duration_ms"] = duration_ms
                self._record_attempt(
                    request=request_for_execution,
                    response=response,
                    duration_ms=duration_ms,
                )

        if response is None:
            return Response(
                success=False,
                reason="internal_error",
                details={"error": "No response returned"},
                error_type=Exception,
            )
        return response

    def _execute_primitive(self, request: Request) -> Response:
        """Execute atomic work. Override this for primitive blocks."""
        # Default implementation for "empty" blocks
        return Response(success=True, data=None)

    def estimate_execution(self, request: Request) -> BlockEstimate:
        """Return a side-effect-free estimate for this block.

        Args:
            request: Request to estimate.

        Returns:
            BlockEstimate for the given request.
        """

        identity = self.stats_identity()
        store = self._stats_store or get_default_store()
        return store.estimate(identity)

    def _execute_graph(self, request: Request) -> Response:
        """Execute the graph of child nodes."""
        validation_failure = self._validate_graph()
        if validation_failure is not None:
            return validation_failure

        # Ensure nodes dict exists for lookup
        nodes = self._nodes or {}

        current_node_name = self._entry_point
        current_request = request

        steps = 0

        while current_node_name:
            steps += 1
            if steps > self._max_steps:
                return Response(
                    success=False,
                    reason="max_steps_exceeded",
                    details={"max_steps": self._max_steps, "node": current_node_name},
                    error_type=Exception,
                )

            node = nodes.get(current_node_name)
            if not node:
                return Response(
                    success=False,
                    reason="unknown_node",
                    details={
                        "error": f"Entry point/Node '{current_node_name}' not found"
                    },
                    error_type=Exception,
                )

            # Execute the child with recovery logic
            response = self._execute_child_with_recovery(
                node=node,
                request=current_request,
                node_name=current_node_name,
            )

            if response.success is False:
                # If a child fails (and wasn't recovered), the graph fails.
                return response

            # If success, check transitions
            transition_config = self._transitions.get(current_node_name)
            next_node_name = None

            if isinstance(transition_config, str):
                next_node_name = transition_config
            elif isinstance(transition_config, list):
                for branch in transition_config:
                    condition_name = branch.get("condition", "default")
                    target = branch.get("target")

                    try:
                        condition_func = ConditionRegistry.get(condition_name)
                    except ValueError as exc:
                        return Response(
                            success=False,
                            reason="condition_resolution_error",
                            details={"error": str(exc), "condition": condition_name},
                            error_type=Exception,
                        )

                    try:
                        condition_result = condition_func(response)
                    except Exception as exc:
                        return Response(
                            success=False,
                            reason="condition_execution_error",
                            details={
                                "condition": condition_name,
                                "error": build_exception_details(exc),
                            },
                            error_type=Exception,
                        )

                    if condition_result:
                        next_node_name = target
                        break

            if transition_config is not None and next_node_name is None:
                return Response(
                    success=False,
                    reason="no_transition",
                    details={"node": current_node_name},
                    error_type=Exception,
                )

            if next_node_name:
                current_node_name = next_node_name
                # Optional: Update metadata to trace path
            else:
                # Terminal state
                final = response.model_copy(deep=False)
                final.metadata = {
                    **dict(final.metadata or {}),
                    "source": node.name,
                    "composite": self.name,
                    "last_node": current_node_name,
                }
                return final

        return Response(
            success=False,
            reason="graph_execution_ended_unexpectedly",
            details={},
            error_type=Exception,
        )

    def _execute_child_with_recovery(
        self,
        node: "Block",
        request: Request,
        node_name: str,
    ) -> Response:
        """Execute a child node and apply its recovery policies on failure.

        Args:
            node: Child block to execute.
            request: Parent-pruned request to execute against.
            node_name: Composite node name used to execute this child.

        Returns:
            A Response indicating success or failure for the node execution.
        """
        attempt = 1
        last_child_request, response = self._execute_child_attempt(
            node=node,
            request=request,
            node_name=node_name,
            attempt=attempt,
            source_request=None,
        )

        if response.success is True:
            return response

        error_type = response.error_type or Exception
        policies = node.get_policy_stack(error_type)
        current_failure: Response = response

        for policy in policies:
            if isinstance(policy, RetryPolicy):
                attempt, last_child_request, current_failure = self._apply_retry_policy(
                    node=node,
                    request=request,
                    node_name=node_name,
                    policy=policy,
                    attempt=attempt,
                    last_child_request=last_child_request,
                    current_failure=current_failure,
                )
            elif isinstance(policy, RepairPolicy):
                attempt, last_child_request, current_failure = (
                    self._apply_repair_policy(
                        node=node,
                        request=request,
                        node_name=node_name,
                        policy=policy,
                        attempt=attempt,
                        last_child_request=last_child_request,
                        current_failure=current_failure,
                    )
                )
            else:
                current_failure = self._apply_custom_policy(
                    policy, node, last_child_request, current_failure
                )

            if current_failure.success is True:
                return current_failure
            if policy.type == RecoveryType.BUBBLE:
                return current_failure

        return current_failure

    def _execute_child_attempt(
        self,
        node: "Block",
        request: Request,
        node_name: str,
        attempt: int,
        source_request: Optional[Request],
    ) -> tuple[Request, Response]:
        """Execute a single child attempt and return request + response.

        Args:
            node: Child block to execute.
            request: Parent request to derive from.
            node_name: Composite node name used to execute this child.
            attempt: Attempt number.
            source_request: Optional request that supplies payload/context.

        Returns:
            Tuple of (child request, child response).
        """

        child_request = self._build_child_request(
            parent_request=request,
            child=node,
            node_name=node_name,
            attempt=attempt,
            source_request=source_request,
        )
        response = node.execute(child_request)
        return child_request, response

    def _apply_retry_policy(
        self,
        node: "Block",
        request: Request,
        node_name: str,
        policy: RetryPolicy,
        attempt: int,
        last_child_request: Request,
        current_failure: Response,
    ) -> tuple[int, Request, Response]:
        """Apply a retry policy and return updated attempt state.

        Args:
            node: Child block to execute.
            request: Parent request to derive from.
            node_name: Composite node name used to execute this child.
            policy: Retry policy to apply.
            attempt: Current attempt number.
            last_child_request: Last child request sent.
            current_failure: Latest failure response.

        Returns:
            Tuple of (attempt, last_child_request, latest response).
        """

        if not self._is_recoverable_via_retry(node):
            return (
                attempt,
                last_child_request,
                self._unsafe_to_retry_response(node, current_failure),
            )

        remaining_attempts = max(policy.max_attempts - attempt, 0)
        for _ in range(remaining_attempts):
            attempt += 1
            if policy.delay_seconds > 0:
                sleep(policy.delay_seconds)
            last_child_request, response = self._execute_child_attempt(
                node=node,
                request=request,
                node_name=node_name,
                attempt=attempt,
                source_request=last_child_request,
            )
            if response.success is True:
                return attempt, last_child_request, response
            current_failure = response

        return attempt, last_child_request, current_failure

    def _apply_repair_policy(
        self,
        node: "Block",
        request: Request,
        node_name: str,
        policy: RepairPolicy,
        attempt: int,
        last_child_request: Request,
        current_failure: Response,
    ) -> tuple[int, Request, Response]:
        """Apply a repair policy and return updated attempt state.

        Args:
            node: Child block to execute.
            request: Parent request to derive from.
            node_name: Composite node name used to execute this child.
            policy: Repair policy to apply.
            attempt: Current attempt number.
            last_child_request: Last child request sent.
            current_failure: Latest failure response.

        Returns:
            Tuple of (attempt, last_child_request, latest response).
        """

        if not self._is_recoverable_via_retry(node):
            return (
                attempt,
                last_child_request,
                self._unsafe_to_retry_response(node, current_failure),
            )

        try:
            repair_func = RepairRegistry.get(policy.repair_function)
        except Exception as exc:
            return (
                attempt,
                last_child_request,
                Response(
                    success=False,
                    reason="repair_execution_failed",
                    details={
                        "repair_function": policy.repair_function,
                        "error": build_exception_details(exc),
                    },
                    error_type=Exception,
                ),
            )

        repaired = repair_func(last_child_request, current_failure)
        attempt += 1
        last_child_request, response = self._execute_child_attempt(
            node=node,
            request=request,
            node_name=node_name,
            attempt=attempt,
            source_request=repaired,
        )
        return attempt, last_child_request, response

    def _apply_custom_policy(
        self,
        policy: RecoveryPolicy,
        node: "Block",
        last_child_request: Request,
        current_failure: Response,
    ) -> Response:
        """Apply a non-retry policy and return its response.

        Args:
            policy: Custom recovery policy.
            node: Child block to execute.
            last_child_request: Last child request sent.
            current_failure: Latest failure response.

        Returns:
            Response returned by the policy handler.
        """

        return PolicyHandler.handle(policy, node, last_child_request, current_failure)

    def _validate_graph(self) -> Optional[Response]:
        """Validate composite graph configuration.

        Returns:
            Failed Response if invalid, otherwise None.
        """

        if self._graph_validated:
            return self._graph_validation

        nodes = self._nodes or {}
        if not self._entry_point:
            response = Response(
                success=False,
                reason="invalid_graph",
                details={"error": "Graph block missing entry_point"},
                error_type=Exception,
            )
            self._graph_validated = True
            self._graph_validation = response
            return response

        if self._entry_point not in nodes:
            response = Response(
                success=False,
                reason="invalid_graph",
                details={"error": f"entry_point '{self._entry_point}' not found"},
                error_type=Exception,
            )
            self._graph_validated = True
            self._graph_validation = response
            return response

        for from_node, transition in (self._transitions or {}).items():
            if from_node not in nodes:
                response = Response(
                    success=False,
                    reason="invalid_graph",
                    details={"error": f"transition from unknown node '{from_node}'"},
                    error_type=Exception,
                )
                self._graph_validated = True
                self._graph_validation = response
                return response

            if isinstance(transition, str):
                if transition not in nodes:
                    response = Response(
                        success=False,
                        reason="invalid_graph",
                        details={
                            "error": f"transition target '{transition}' not found"
                        },
                        error_type=Exception,
                    )
                    self._graph_validated = True
                    self._graph_validation = response
                    return response
                continue

            if isinstance(transition, list):
                for branch in transition:
                    condition_name = branch.get("condition", "default")
                    target = branch.get("target")
                    if not target:
                        response = Response(
                            success=False,
                            reason="invalid_graph",
                            details={"error": f"missing target for node '{from_node}'"},
                            error_type=Exception,
                        )
                        self._graph_validated = True
                        self._graph_validation = response
                        return response
                    if target not in nodes:
                        response = Response(
                            success=False,
                            reason="invalid_graph",
                            details={
                                "error": f"transition target '{target}' not found"
                            },
                            error_type=Exception,
                        )
                        self._graph_validated = True
                        self._graph_validation = response
                        return response

                    try:
                        ConditionRegistry.get(condition_name)
                    except ValueError as e:
                        response = Response(
                            success=False,
                            reason="condition_resolution_error",
                            details={"error": str(e), "condition": condition_name},
                            error_type=Exception,
                        )
                        self._graph_validated = True
                        self._graph_validation = response
                        return response
                continue

            response = Response(
                success=False,
                reason="invalid_graph",
                details={"error": f"invalid transition config for '{from_node}'"},
                error_type=Exception,
            )
            self._graph_validated = True
            self._graph_validation = response
            return response

        self._graph_validated = True
        self._graph_validation = None
        return None

    def stats_identity(self) -> BlockStatsIdentity:
        """Return the stable stats identity for this block."""

        return BlockStatsIdentity(
            block_name=self.name, block_type=self.block_type, version=None
        )

    def _build_attempt_record(
        self, request: Request, response: Response, duration_ms: float
    ) -> BlockAttemptRecord:
        """Build a stats record for a block execution attempt.

        Args:
            request: Request executed by the block.
            response: Response produced by the block.
            duration_ms: Execution duration in milliseconds.

        Returns:
            BlockAttemptRecord to record.
        """

        metadata = request.metadata
        identity = self.stats_identity()
        error_type = response.error_type
        error_type_name = error_type.__name__ if error_type else None
        return BlockAttemptRecord(
            trace_id=str(metadata.get("trace_id", "")),
            run_id=str(metadata.get("run_id", "")),
            span_id=str(metadata.get("span_id", "")),
            parent_span_id=metadata.get("parent_span_id"),
            block_name=identity.block_name,
            block_type=identity.block_type,
            version=identity.version,
            node_name=metadata.get("node_name"),
            attempt=int(metadata.get("attempt", 1)),
            success=response.success,
            reason=response.reason,
            error_type=error_type_name,
            duration_ms=duration_ms,
        )

    def _record_attempt(
        self, request: Request, response: Response, duration_ms: float
    ) -> None:
        """Record a block execution attempt in the stats store.

        Args:
            request: Request executed by the block.
            response: Response produced by the block.
            duration_ms: Execution duration in milliseconds.
        """

        record = self._build_attempt_record(request, response, duration_ms)
        try:
            store = self._stats_store or get_default_store()
            store.record_attempt(record)
        except Exception as exc:
            metadata = request.metadata
            logger.exception(
                "Failed to record block attempt",
                extra={
                    "block_name": self.name,
                    "node_name": metadata.get("node_name"),
                    "request_id": metadata.get("id"),
                    "trace_id": metadata.get("trace_id"),
                    "run_id": metadata.get("run_id"),
                    "span_id": metadata.get("span_id"),
                    "parent_span_id": metadata.get("parent_span_id"),
                    "attempt": metadata.get("attempt"),
                    "error": build_exception_details(exc),
                },
            )

    def _with_base_metadata(self, request: Request) -> Request:
        """Return a request copy with minimal base metadata populated.

        This method does not mutate the input request.
        """

        cloned = request.model_copy(deep=False)
        cloned.metadata = dict(request.metadata)
        md = cloned.metadata

        md.setdefault("id", str(uuid4()))
        md.setdefault("trace_id", str(uuid4()))
        md.setdefault("run_id", str(uuid4()))
        md.setdefault("span_id", str(uuid4()))
        md.setdefault("block_name", self.name)
        md.setdefault("attempt", 1)
        return cloned

    def _attach_correlation_metadata(
        self, request: Request, response: Response
    ) -> None:
        """Ensure response metadata contains attempt correlation fields.

        Args:
            request: The request that drove this specific attempt.
            response: The response produced by this attempt.
        """

        for key in (
            "id",
            "trace_id",
            "run_id",
            "span_id",
            "parent_span_id",
            "attempt",
            "block_name",
            "node_name",
        ):
            if key in request.metadata:
                response.metadata[key] = request.metadata[key]

    def _build_child_request(
        self,
        parent_request: Request,
        child: "Block",
        node_name: str,
        attempt: int,
        source_request: Optional[Request] = None,
    ) -> Request:
        """Construct a child request, propagating correlation metadata.

        This method does not mutate the input request.
        """

        cloned = parent_request.model_copy(deep=False)
        cloned.metadata = dict(parent_request.metadata)
        payload_source = (
            source_request.payload if source_request else parent_request.payload
        )
        context_source = (
            source_request.context if source_request else parent_request.context
        )
        cloned.payload = dict(payload_source)
        cloned.context = dict(context_source)
        md = cloned.metadata

        md["id"] = str(uuid4())
        md.setdefault("trace_id", str(uuid4()))
        md.setdefault("run_id", str(uuid4()))
        md["parent_span_id"] = md.get("span_id")
        md["span_id"] = str(uuid4())
        md["attempt"] = attempt
        md["block_name"] = child.name
        md["node_name"] = node_name
        return cloned

    def _is_recoverable_via_retry(self, block: "Block") -> bool:
        """Return True if retry/repair is allowed based on side-effect classification."""

        side_effect_class = self._normalize_side_effect_class(block.side_effect_class)
        return side_effect_class in {"none", "idempotent"}

    def _unsafe_to_retry_response(self, node: "Block", failure: Response) -> Response:
        """Build a standard unsafe-to-retry response.

        Args:
            node: The node that was attempted.
            failure: The original failure response.

        Returns:
            A response indicating retries are unsafe.
        """

        failure_error_type = failure.error_type or Exception
        return Response(
            success=False,
            reason="unsafe_to_retry",
            details={
                "side_effect_class": node.side_effect_class,
                "failure_reason": failure.reason,
                "failure_error_type": (
                    failure.error_type.__name__ if failure.error_type else None
                ),
                "failure_details": failure.details,
            },
            error_type=failure_error_type,
        )

    def _normalize_side_effect_class(self, value: str) -> str:
        """Normalize a side-effect class string.

        Unknown values are treated as "non_idempotent".
        """

        normalized = (value or "").strip().lower()
        if normalized in {"none", "idempotent", "non_idempotent"}:
            return normalized
        return "non_idempotent"

    def get_policy_stack(self, error_type: Type[Exception]) -> List[RecoveryPolicy]:
        """Return the recovery policy stack for a given error type."""
        return [BubblePolicy()]
