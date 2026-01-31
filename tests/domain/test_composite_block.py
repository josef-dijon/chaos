from typing import List, Type
from unittest.mock import Mock

import pytest
from chaos.domain.block import Block
from chaos.domain.messages import Request, Response
from chaos.domain.policy import BubblePolicy, RecoveryPolicy, RetryPolicy
from chaos.engine.conditions import ConditionRegistry


class MockBlock(Block):
    def __init__(self, name: str, should_fail=False, fail_count=0, data=None):
        super().__init__(name)
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.attempts = 0
        self.policies: List[RecoveryPolicy] = [BubblePolicy()]
        self.fixed_data = data

    def build(self) -> None:
        pass

    def _execute_primitive(self, request: Request):
        self.attempts += 1
        if self.should_fail:
            return Response(success=False, reason="Mock failure")
        if self.attempts <= self.fail_count:
            return Response(success=False, reason="Temporary failure")
        return Response(success=True, data=self.fixed_data or "Success")

    def get_policy_stack(self, error_type: Type[Exception]) -> List[RecoveryPolicy]:
        return self.policies


class CompositeBlockStub(Block):
    def build(self) -> None:
        pass


def test_composite_simple_execution():
    child = MockBlock("child")
    composite = CompositeBlockStub(
        "composite", nodes={"child": child}, entry_point="child"
    )

    request = Request(payload={"foo": "bar"})
    response = composite.execute(request)

    assert response.success is True
    assert response.data == "Success"
    assert child.attempts == 1
    assert "trace_id" in response.metadata
    assert "span_id" in response.metadata
    assert response.metadata.get("attempt") == 1


def test_composite_retry_success():
    # Child fails twice then succeeds
    child = MockBlock("child", fail_count=2)
    child.policies = [RetryPolicy(max_attempts=3)]

    composite = CompositeBlockStub(
        "composite", nodes={"child": child}, entry_point="child"
    )

    response = composite.execute(Request())

    assert response.success is True
    assert child.attempts == 3


def test_composite_retry_exhausted():
    # Child always fails
    child = MockBlock("child", should_fail=True)
    child.policies = [RetryPolicy(max_attempts=2)]

    composite = CompositeBlockStub(
        "composite", nodes={"child": child}, entry_point="child"
    )

    response = composite.execute(Request())

    assert response.success is False
    assert child.attempts == 2


def test_composite_bubble():
    child = MockBlock("child", should_fail=True)
    child.policies = [BubblePolicy()]

    composite = CompositeBlockStub(
        "composite", nodes={"child": child}, entry_point="child"
    )

    response = composite.execute(Request())

    assert response.success is False
    assert child.attempts == 1


def test_composite_config_error():
    composite = CompositeBlockStub("composite", nodes={}, entry_point="missing_child")
    response = composite.execute(Request())
    assert response.success is False
    assert response.reason == "invalid_graph"


def test_composite_linear_flow():
    # A -> B -> End
    block_a = MockBlock("A")
    block_b = MockBlock("B")

    composite = CompositeBlockStub(
        "composite",
        nodes={"A": block_a, "B": block_b},
        entry_point="A",
        transitions={"A": "B"},
    )

    response = composite.execute(Request(payload={"val": 0}))

    assert response.success is True
    assert block_a.attempts == 1
    assert block_b.attempts == 1
    assert response.metadata["last_node"] == "B"
    assert "trace_id" in response.metadata
    assert "span_id" in response.metadata


def test_composite_branching_flow():
    # A -> (val > 10) -> B
    #   -> (default) -> C

    block_a = MockBlock("A", data=15)
    block_b = MockBlock("B")
    block_c = MockBlock("C")

    @ConditionRegistry.register("is_large")
    def check_large(response: Response) -> bool:
        return (
            response.success is True
            and isinstance(response.data, int)
            and response.data > 10
        )

    try:
        transitions = {
            "A": [
                {"condition": "is_large", "target": "B"},
                {"condition": "default", "target": "C"},
            ]
        }

        composite = CompositeBlockStub(
            "composite",
            nodes={"A": block_a, "B": block_b, "C": block_c},
            entry_point="A",
            transitions=transitions,
        )

        # Test Case 1: Large Value -> B
        response = composite.execute(Request())
        assert response.metadata["last_node"] == "B"
        assert block_b.attempts == 1
        assert block_c.attempts == 0

        # Test Case 2: Small Value -> C
        block_a.fixed_data = 5
        block_b.attempts = 0  # Reset

        response = composite.execute(Request())
        assert response.metadata["last_node"] == "C"
        assert block_b.attempts == 0
        assert block_c.attempts == 1

    finally:
        ConditionRegistry.clear()
