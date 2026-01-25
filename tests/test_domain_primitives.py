from dataclasses import dataclass, field
import pytest
from pydantic import ValidationError
from chaos.domain.knowledge import KnowledgeItem
from chaos.domain.tool import BaseTool, ToolType


def test_knowledge_item_creation():
    item = KnowledgeItem(id="k1", content="Some knowledge")
    assert item.id == "k1"
    assert item.content == "Some knowledge"
    assert item.tags == []
    assert item.metadata == {}


def test_knowledge_item_full_creation():
    item = KnowledgeItem(
        id="k2",
        content="More knowledge",
        tags=["important", "python"],
        metadata={"source": "book"},
    )
    assert item.id == "k2"
    assert item.content == "More knowledge"
    assert item.tags == ["important", "python"]
    assert item.metadata == {"source": "book"}


def test_base_tool_instantiation():
    # BaseTool is abstract, so we must implement it to test it
    @dataclass
    class ConcreteTool(BaseTool):
        name: str = "test_tool"
        description: str = "A test tool"
        type: ToolType = ToolType.CLI
        schema: dict = field(
            default_factory=lambda: {"type": "object", "properties": {}}
        )

        def call(self, args: dict) -> str:
            return "ran"

    tool = ConcreteTool()
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.call({}) == "ran"
    assert tool.as_openai_tool()["function"]["name"] == "test_tool"


def test_base_tool_cannot_instantiate_abstract():
    # Attempting to instantiate BaseTool directly should fail or be impossible
    # Python's ABCMeta prevents instantiation of classes with abstract methods
    with pytest.raises(TypeError):
        BaseTool(  # type: ignore[abstract]
            name="bad", description="bad", type=ToolType.CLI, schema={}
        )
