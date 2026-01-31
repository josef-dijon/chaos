import pytest

from chaos.domain.block import Block
from chaos.domain.messages import Request, Response
from chaos.domain.policy import BubblePolicy, RecoveryPolicy, RepairPolicy, RetryPolicy
from chaos.engine.conditions import ConditionRegistry
from chaos.engine.registry import RepairRegistry


class AlwaysSuccessBlock(Block):
    """A deterministic leaf block that always succeeds."""

    def __init__(self, name: str, data: object = "ok"):
        super().__init__(name=name)
        self._data = data

    def _execute_primitive(self, request: Request):
        return Response(success=True, data=self._data)

    def build(self) -> None:
        pass


class AlwaysFailBlock(Block):
    """A deterministic leaf block that always fails."""

    def __init__(self, name: str, side_effect_class: str = "none"):
        super().__init__(name=name, side_effect_class=side_effect_class)
        self.attempts = 0
        self.policies: list[RecoveryPolicy] = [RetryPolicy(max_attempts=3)]

    def _execute_primitive(self, request: Request):
        self.attempts += 1
        return Response(success=False, reason="fail")

    def get_policy_stack(self, error_type) -> list[RecoveryPolicy]:
        return self.policies

    def build(self) -> None:
        pass


class CompositeBlockStub(Block):
    def build(self) -> None:
        pass


class RepairableBlock(Block):
    """A leaf block that can be repaired by setting payload.fixed=True."""

    def __init__(self, name: str):
        super().__init__(name=name, side_effect_class="idempotent")
        self.seen_attempts: list[int] = []
        self.seen_node_names: list[str] = []

    def _execute_primitive(self, request: Request):
        self.seen_attempts.append(int(request.metadata.get("attempt", 0)))
        self.seen_node_names.append(str(request.metadata.get("node_name", "")))
        if request.payload.get("fixed") is True:
            return Response(success=True, data="fixed")
        return Response(success=False, reason="fail")

    def get_policy_stack(self, error_type) -> list[RecoveryPolicy]:
        return [RepairPolicy(repair_function="fix_it"), BubblePolicy()]

    def build(self) -> None:
        pass


class CaptureRequestIdBlock(Block):
    """A block that captures request ids for retry assertions."""

    def __init__(self, name: str, max_attempts: int = 2, delay_seconds: float = 0.0):
        super().__init__(name=name)
        self.request_ids: list[str] = []
        self.policies: list[RecoveryPolicy] = [
            RetryPolicy(max_attempts=max_attempts, delay_seconds=delay_seconds)
        ]

    def _execute_primitive(self, request: Request):
        self.request_ids.append(str(request.metadata.get("id", "")))
        return Response(success=False, reason="fail")

    def get_policy_stack(self, error_type) -> list[RecoveryPolicy]:
        return self.policies

    def build(self) -> None:
        pass


class MetadataBlock(Block):
    """A block that returns conflicting metadata for overwrite tests."""

    def _execute_primitive(self, request: Request):
        return Response(
            success=True,
            data="ok",
            metadata={"id": "child-id", "trace_id": "child-trace"},
        )

    def build(self) -> None:
        pass


class GraphBuilderBlock(Block):
    def __init__(self, name: str):
        self._child = AlwaysSuccessBlock("child")
        super().__init__(name)

    def build(self) -> None:
        self.set_graph(nodes={"child": self._child}, entry_point="child")


def test_composite_max_steps_exceeded():
    """Fails when composite exceeds max step count."""
    child = AlwaysSuccessBlock("A")
    composite = CompositeBlockStub(
        "composite",
        nodes={"A": child},
        entry_point="A",
        transitions={"A": "A"},
        max_steps=3,
    )

    response = composite.execute(Request())
    assert response.success is False
    assert response.reason == "max_steps_exceeded"


def test_composite_no_transition_when_no_branch_matches():
    """Returns no_transition when no condition matches."""
    block_a = AlwaysSuccessBlock("A", data=1)
    block_b = AlwaysSuccessBlock("B")

    @ConditionRegistry.register("never")
    def never(_: Response) -> bool:
        return False

    try:
        composite = CompositeBlockStub(
            "composite",
            nodes={"A": block_a, "B": block_b},
            entry_point="A",
            transitions={"A": [{"condition": "never", "target": "B"}]},
        )

        response = composite.execute(Request())
        assert response.success is False
        assert response.reason == "no_transition"
    finally:
        ConditionRegistry.clear()


def test_composite_condition_resolution_error_fails_fast():
    """Returns condition_resolution_error for missing condition functions."""
    block_a = AlwaysSuccessBlock("A")
    block_b = AlwaysSuccessBlock("B")

    composite = CompositeBlockStub(
        "composite",
        nodes={"A": block_a, "B": block_b},
        entry_point="A",
        transitions={"A": [{"condition": "missing_condition", "target": "B"}]},
    )

    response = composite.execute(Request())
    assert response.success is False
    assert response.reason == "condition_resolution_error"


def test_retry_forbidden_for_non_idempotent_side_effects():
    """Returns unsafe_to_retry and preserves failure details."""
    child = AlwaysFailBlock("child", side_effect_class="non_idempotent")
    composite = CompositeBlockStub(
        "composite", nodes={"child": child}, entry_point="child"
    )

    response = composite.execute(Request())
    assert response.success is False
    assert response.reason == "unsafe_to_retry"
    assert response.details["failure_reason"] == "fail"
    assert child.attempts == 1


def test_condition_execution_error_returns_failure():
    """Returns condition_execution_error when condition raises."""
    block_a = AlwaysSuccessBlock("A")
    block_b = AlwaysSuccessBlock("B")

    @ConditionRegistry.register("explode")
    def explode(_: Response) -> bool:
        raise RuntimeError("boom")

    try:
        composite = CompositeBlockStub(
            "composite",
            nodes={"A": block_a, "B": block_b},
            entry_point="A",
            transitions={"A": [{"condition": "explode", "target": "B"}]},
        )

        response = composite.execute(Request())
        assert response.success is False
        assert response.reason == "condition_execution_error"
        assert response.details["condition"] == "explode"
    finally:
        ConditionRegistry.clear()


def test_child_request_ids_unique_and_parent_metadata_overwrites():
    """Ensures child request ids are unique and parent metadata wins."""
    child = CaptureRequestIdBlock("child")
    composite = CompositeBlockStub(
        "composite",
        nodes={"child": child},
        entry_point="child",
    )

    request = Request(metadata={"id": "root-id", "trace_id": "root-trace"})
    response = composite.execute(request)

    assert response.success is False
    assert response.metadata["id"] == "root-id"
    assert response.metadata["trace_id"] == "root-trace"
    assert len(child.request_ids) == 2
    assert len(set(child.request_ids)) == 2
    assert "root-id" not in child.request_ids


def test_retry_delay_is_applied(monkeypatch):
    """Applies delay_seconds for retry attempts."""
    import chaos.domain.block as block_module

    delays: list[float] = []

    def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(block_module, "sleep", fake_sleep)

    child = CaptureRequestIdBlock("child", max_attempts=2, delay_seconds=0.25)
    composite = CompositeBlockStub(
        "composite",
        nodes={"child": child},
        entry_point="child",
    )

    response = composite.execute(Request())

    assert response.success is False
    assert delays == [0.25]


def test_build_sets_graph_and_executes():
    """Build hooks set graph configuration before execution."""
    composite = GraphBuilderBlock("composite")

    response = composite.execute(Request())

    assert response.success is True
    assert response.data == "ok"
    assert response.metadata["last_node"] == "child"


def test_invalid_transition_config_returns_failure():
    """Rejects invalid transition configurations."""
    block_a = AlwaysSuccessBlock("A")
    composite = CompositeBlockStub(
        "composite",
        nodes={"A": block_a},
        entry_point="A",
        transitions={"A": {"bad": "config"}},
    )

    response = composite.execute(Request())

    assert response.success is False
    assert response.reason == "invalid_graph"


def test_repair_increments_attempt_and_uses_child_envelope() -> None:
    """Tracks repair attempts and uses child metadata."""
    captured: dict = {}

    @RepairRegistry.register("fix_it")
    def fix_request(request: Request, failure: Response) -> Request:
        captured["attempt"] = request.metadata.get("attempt")
        captured["node_name"] = request.metadata.get("node_name")
        new_payload = dict(request.payload)
        new_payload["fixed"] = True
        return Request(payload=new_payload)

    try:
        child = RepairableBlock("child")
        composite = CompositeBlockStub(
            "composite", nodes={"child": child}, entry_point="child"
        )

        response = composite.execute(Request())

        assert response.success is True
        assert response.data == "fixed"
        assert child.seen_attempts == [1, 2]
        assert captured["attempt"] == 1
        assert captured["node_name"] == "child"
        assert response.metadata.get("attempt") == 1
        assert response.metadata.get("node_name") == "child"
        assert "trace_id" in response.metadata
        assert "span_id" in response.metadata
    finally:
        RepairRegistry.clear()
