from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

from chaos.domain.messages import Request, Response
from chaos.domain.policy import BubblePolicy, RecoveryPolicy, RecoveryType, RetryPolicy
from chaos.domain.state import BlockState
from chaos.engine.conditions import ConditionRegistry
from chaos.engine.policy_handlers import PolicyHandler


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
        """
        self._name = name
        self._state = BlockState.READY
        self._nodes = nodes
        self._entry_point = entry_point
        self._transitions = transitions or {}
        self._max_steps = max_steps
        self._side_effect_class = self._normalize_side_effect_class(side_effect_class)

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

    @property
    def name(self) -> str:
        """Stable identifier for this block instance."""
        return self._name

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
        try:
            request_for_execution = self._with_base_metadata(request)
            if self._nodes is not None:
                return self._execute_graph(request_for_execution)
            return self._execute_primitive(request_for_execution)

        except Exception as e:
            return Response(
                success=False,
                reason="internal_error",
                details={"error": str(e)},
                error_type=type(e),
            )
        finally:
            self._state = BlockState.READY

    def _execute_primitive(self, request: Request) -> Response:
        """Execute atomic work. Override this for primitive blocks."""
        # Default implementation for "empty" blocks
        return Response(success=True, data=None)

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
                )

            # Execute the child with recovery logic
            response = self._execute_child_with_recovery(
                node=node,
                request=current_request,
                node_name=current_node_name,
            )

            if response.success() is False:
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

                    condition_func = ConditionRegistry.get(condition_name)
                    if condition_func(response):
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
                return Response(
                    success=True,
                    data=response.data,
                    metadata={
                        "source": node.name,
                        "composite": self.name,
                        "last_node": current_node_name,
                    },
                )

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
        child_request = self._build_child_request(
            parent_request=request,
            child=node,
            node_name=node_name,
            attempt=attempt,
        )
        response = node.execute(child_request)

        if response.success() is True:
            return response

        error_type = response.error_type or Exception
        policies = node.get_policy_stack(error_type)

        current_failure: Response = response

        for policy in policies:
            if policy.type == RecoveryType.RETRY:
                if not self._is_recoverable_via_retry(node):
                    return Response(
                        success=False,
                        reason="unsafe_to_retry",
                        details={"side_effect_class": node.side_effect_class},
                        error_type=Exception,
                    )
                retry_policy: RetryPolicy = policy  # type: ignore
                for _ in range(retry_policy.max_attempts):
                    attempt += 1
                    retry_request = self._build_child_request(
                        parent_request=request,
                        child=node,
                        node_name=node_name,
                        attempt=attempt,
                    )
                    retry_response = node.execute(retry_request)
                    if retry_response.success() is True:
                        return retry_response
                    current_failure = retry_response
            else:
                if (
                    policy.type == RecoveryType.REPAIR
                    and not self._is_recoverable_via_retry(node)
                ):
                    return Response(
                        success=False,
                        reason="unsafe_to_retry",
                        details={"side_effect_class": node.side_effect_class},
                        error_type=Exception,
                    )
                policy_response = PolicyHandler.handle(
                    policy, node, request, current_failure
                )
                if policy_response.success() is True:
                    return policy_response
                current_failure = policy_response
                if policy.type == RecoveryType.BUBBLE:
                    return current_failure

        return current_failure

    def _validate_graph(self) -> Optional[Response]:
        """Validate composite graph configuration.

        Returns:
            Failed Response if invalid, otherwise None.
        """

        nodes = self._nodes or {}
        if not self._entry_point:
            return Response(
                success=False,
                reason="invalid_graph",
                details={"error": "Graph block missing entry_point"},
                error_type=Exception,
            )

        if self._entry_point not in nodes:
            return Response(
                success=False,
                reason="invalid_graph",
                details={"error": f"entry_point '{self._entry_point}' not found"},
                error_type=Exception,
            )

        for from_node, transition in (self._transitions or {}).items():
            if from_node not in nodes:
                return Response(
                    success=False,
                    reason="invalid_graph",
                    details={"error": f"transition from unknown node '{from_node}'"},
                    error_type=Exception,
                )

            if isinstance(transition, str):
                if transition not in nodes:
                    return Response(
                        success=False,
                        reason="invalid_graph",
                        details={
                            "error": f"transition target '{transition}' not found"
                        },
                        error_type=Exception,
                    )
                continue

            if isinstance(transition, list):
                for branch in transition:
                    condition_name = branch.get("condition", "default")
                    target = branch.get("target")
                    if not target:
                        return Response(
                            success=False,
                            reason="invalid_graph",
                            details={"error": f"missing target for node '{from_node}'"},
                            error_type=Exception,
                        )
                    if target not in nodes:
                        return Response(
                            success=False,
                            reason="invalid_graph",
                            details={
                                "error": f"transition target '{target}' not found"
                            },
                            error_type=Exception,
                        )

                    try:
                        ConditionRegistry.get(condition_name)
                    except ValueError as e:
                        return Response(
                            success=False,
                            reason="condition_resolution_error",
                            details={"error": str(e), "condition": condition_name},
                            error_type=Exception,
                        )
                continue

            return Response(
                success=False,
                reason="invalid_graph",
                details={"error": f"invalid transition config for '{from_node}'"},
                error_type=Exception,
            )

        return None

    def _with_base_metadata(self, request: Request) -> Request:
        """Return a request copy with minimal base metadata populated.

        This method does not mutate the input request.
        """

        cloned = request.model_copy(deep=True)
        md = cloned.metadata

        md.setdefault("trace_id", str(uuid4()))
        md.setdefault("run_id", str(uuid4()))
        md.setdefault("span_id", str(uuid4()))
        md.setdefault("block_name", self.name)
        md.setdefault("attempt", 1)
        return cloned

    def _build_child_request(
        self,
        parent_request: Request,
        child: "Block",
        node_name: str,
        attempt: int,
    ) -> Request:
        """Construct a child request, propagating correlation metadata.

        This method does not mutate the input request.
        """

        cloned = parent_request.model_copy(deep=True)
        md = cloned.metadata

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
