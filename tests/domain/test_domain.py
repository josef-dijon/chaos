from typing import Any, Dict, cast

from chaos.domain.block import Block
from chaos.domain.messages import (
    Request,
    Response,
    reset_request_id_factory,
    set_request_id_factory,
)
from chaos.domain.policy import BubblePolicy, RecoveryType
from chaos.domain.state import BlockState


class SimpleBlock(Block):
    def build(self) -> None:
        pass

    def _execute_primitive(self, request: Request) -> Response:
        return Response(success=True, data=request.payload["value"])


class MetadataEchoBlock(Block):
    def build(self) -> None:
        pass

    def _execute_primitive(self, request: Request) -> Response:
        return Response(success=True, data=request.metadata)


def test_block_initialization():
    block = SimpleBlock(name="test_block")
    assert block.name == "test_block"
    assert block.state == BlockState.READY
    assert isinstance(block.get_policy_stack(ValueError)[0], BubblePolicy)


def test_request_response_flow():
    block = SimpleBlock(name="echo")
    req = Request(payload={"value": 42})
    resp = block.execute(req)

    assert resp.success() is True
    assert resp.data == 42
    assert resp.metadata["id"] is not None


def test_request_generates_id():
    req = Request()

    assert req.metadata["id"]


def test_request_preserves_id_across_execute():
    block = MetadataEchoBlock(name="meta")
    req = Request(metadata={"id": "request-id"})

    resp = block.execute(req)

    assert req.metadata["id"] == "request-id"
    assert resp.metadata["id"] == "request-id"


def test_request_id_factory_override() -> None:
    """Allows deterministic request ids in tests."""
    set_request_id_factory(lambda: "fixed-id")
    try:
        req = Request()
        assert req.metadata["id"] == "fixed-id"
    finally:
        reset_request_id_factory()


def test_failure_response_structure():
    fail = Response(success=False, reason="Something went wrong", details={"code": 500})
    assert fail.reason == "Something went wrong"
    assert fail.details["code"] == 500
    assert fail.metadata["id"] is not None


def test_base_metadata_is_populated_on_request():
    block = MetadataEchoBlock(name="meta")

    resp = block.execute(Request())

    assert resp.success() is True
    assert isinstance(resp.data, dict)
    metadata = cast(Dict[str, Any], resp.data)
    assert metadata["trace_id"]
    assert metadata["run_id"]
    assert metadata["span_id"]
    assert metadata["block_name"] == "meta"
    assert metadata["attempt"] == 1


def test_side_effect_class_normalization():
    block = MetadataEchoBlock(name="meta", side_effect_class="unknown")

    assert block.side_effect_class == "non_idempotent"
