import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from chaos.config import Config
from chaos.domain.skill import Skill
from chaos.engine.basic_agent import BasicAgent, AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage


@pytest.fixture
def mock_deps():
    mock_ident = MagicMock()
    mock_ident.profile.name = "TestBot"
    mock_ident.profile.role = "Tester"
    mock_ident.profile.core_values = ["Accuracy"]
    mock_ident.instructions.system_prompts = ["Be precise"]
    mock_ident.instructions.operational_notes = ["No bugs"]
    mock_ident.loop_definition = "default"
    mock_ident.knowledge_whitelist = None
    mock_ident.knowledge_blacklist = None
    mock_ident.skills_whitelist = None
    mock_ident.skills_blacklist = None
    mock_ident.tool_manifest = []
    mock_ident.tool_whitelist = None
    mock_ident.tool_blacklist = None
    mock_ident.resolve_tool_whitelist.return_value = None

    mock_mem = MagicMock()
    mock_skills = MagicMock()
    mock_know = MagicMock()
    mock_tools = MagicMock()
    mock_config = MagicMock(spec=Config)
    mock_config.get_model_name.return_value = "gpt-4o"
    mock_config.get_openai_api_key.return_value = "test-key"

    return {
        "identity": mock_ident,
        "config": mock_config,
        "memory": mock_mem,
        "skills_lib": mock_skills,
        "knowledge_lib": mock_know,
        "tool_lib": mock_tools,
        "identity_path": Path("/tmp/identity.json"),
    }


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_init(mock_graph, mock_llm, mock_deps):
    """Initializes the agent with graph and LLM dependencies."""
    agent = BasicAgent(**mock_deps)
    mock_llm.assert_called()
    mock_graph.assert_called()


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_init_invalid_loop_definition(mock_graph, mock_llm, mock_deps):
    """Rejects unsupported loop definitions."""
    mock_deps["identity"].loop_definition = "unsupported"

    with pytest.raises(ValueError, match="Unsupported loop definition"):
        BasicAgent(**mock_deps)


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_should_continue(mock_graph, mock_llm, mock_deps):
    """Determines whether to continue based on tool calls."""
    agent = BasicAgent(**mock_deps)

    msg_with_tool = AIMessage(
        content="use tool", tool_calls=[{"name": "t1", "args": {}, "id": "1"}]
    )
    state_with_tool: AgentState = {"messages": [msg_with_tool], "context": ""}
    assert agent.should_continue(state_with_tool) == "continue"

    msg_no_tool = AIMessage(content="done")
    state_no_tool: AgentState = {"messages": [msg_no_tool], "context": ""}
    assert agent.should_continue(state_no_tool) == "end"


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_recall(mock_graph, mock_llm, mock_deps):
    """Builds context from memory and knowledge sources."""
    mock_deps["memory"].retrieve.return_value = "Memory 1"
    mock_deps["knowledge_lib"].search.return_value = "Knowledge 1"

    agent = BasicAgent(**mock_deps)

    empty_state: AgentState = {"messages": [], "context": ""}
    assert agent.recall(empty_state) == {"context": ""}

    state: AgentState = {
        "messages": [HumanMessage(content="Help me")],
        "context": "",
    }
    result = agent.recall(state)

    assert "LTM: Memory 1" in result["context"]
    assert "Reference Knowledge: Knowledge 1" in result["context"]
    mock_deps["memory"].retrieve.assert_called_with("Help me")
    mock_deps["knowledge_lib"].search.assert_called_with(
        query="Help me",
        whitelist=mock_deps["identity"].knowledge_whitelist,
        blacklist=mock_deps["identity"].knowledge_blacklist,
    )


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_recall_subconscious_full_access(mock_graph, mock_llm, mock_deps):
    """Ignores knowledge filters for subconscious persona."""
    mock_deps["identity"].knowledge_whitelist = ["restricted"]
    mock_deps["identity"].knowledge_blacklist = ["blocked"]
    mock_deps["memory"].retrieve.return_value = "Memory 1"
    mock_deps["knowledge_lib"].search.return_value = "Knowledge 1"

    agent = BasicAgent(**mock_deps, persona="subconscious")

    state: AgentState = {
        "messages": [HumanMessage(content="Help me")],
        "context": "",
    }

    agent.recall(state)

    mock_deps["knowledge_lib"].search.assert_called_with(
        query="Help me",
        whitelist=None,
        blacklist=None,
    )


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_reason_logic(mock_graph, mock_llm, mock_deps):
    """Constructs prompts and invokes the LLM with tools."""
    # Setup
    mock_deps["identity"].tool_manifest = ["test_tool"]
    mock_deps["identity"].resolve_tool_whitelist.return_value = ["test_tool"]
    mock_deps["skills_lib"].list_skills.return_value = [
        Skill(name="S1", description="", content="How to test")
    ]

    mock_tool = MagicMock()
    mock_tool.as_openai_tool.return_value = {
        "type": "function",
        "function": {"name": "test_tool", "description": "Tests things"},
    }
    mock_deps["tool_lib"].list_tools.return_value = [mock_tool]

    # Mock LLM behavior
    mock_llm_instance = mock_llm.return_value
    mock_bound_llm = MagicMock()
    mock_llm_instance.bind_tools.return_value = mock_bound_llm
    mock_bound_llm.invoke.return_value = AIMessage(content="response")

    agent = BasicAgent(**mock_deps)

    # Run
    state: AgentState = {
        "messages": [HumanMessage(content="Hi")],
        "context": "Previous info",
    }
    result = agent.reason(state)

    # Assertions
    assert result["messages"][0].content == "response"

    # Check skills fetch
    mock_deps["skills_lib"].list_skills.assert_called()

    # Check tool binding
    mock_deps["tool_lib"].list_tools.assert_called_with(
        whitelist=["test_tool"],
        blacklist=mock_deps["identity"].tool_blacklist,
    )
    mock_llm_instance.bind_tools.assert_called_with(
        [mock_tool.as_openai_tool.return_value]
    )

    # Check invoke call structure
    call_args = mock_bound_llm.invoke.call_args[0][0]  # List of messages

    # 0: System Prompt
    assert isinstance(call_args[0], SystemMessage)
    assert "Identity: TestBot" in call_args[0].content
    assert "Core Instructions:" in call_args[0].content
    assert "Be precise" in call_args[0].content
    assert "Operational Notes" in call_args[0].content

    # 1: Context (inserted)
    assert isinstance(call_args[1], SystemMessage)
    assert "Relevant Context: Previous info" in call_args[1].content

    # 2: User message
    assert isinstance(call_args[2], HumanMessage)
    assert call_args[2].content == "Hi"


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_act(mock_graph, mock_llm, mock_deps):
    """Executes tool calls and returns tool messages."""
    agent = BasicAgent(**mock_deps)

    mock_tool = MagicMock()
    mock_tool.call.return_value = "Tool Output"
    mock_deps["tool_lib"].get_tool.return_value = mock_tool

    tool_call = {"name": "test_tool", "args": {"arg": 1}, "id": "call_1"}
    message = AIMessage(content="calling", tool_calls=[tool_call])
    state: AgentState = {"messages": [message], "context": ""}

    result = agent.act(state)

    assert len(result["messages"]) == 1
    tool_msg = result["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.content == "Tool Output"
    assert tool_msg.tool_call_id == "call_1"
    mock_tool.call.assert_called_with({"arg": 1})


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_act_tool_error(mock_graph, mock_llm, mock_deps):
    """Captures tool execution errors in messages."""
    agent = BasicAgent(**mock_deps)

    mock_tool = MagicMock()
    mock_tool.call.side_effect = Exception("Boom")
    mock_deps["tool_lib"].get_tool.return_value = mock_tool

    tool_call = {"name": "test_tool", "args": {}, "id": "call_1"}
    state: AgentState = {
        "messages": [AIMessage(content="calling", tool_calls=[tool_call])],
        "context": "",
    }

    result = agent.act(state)
    assert "Error executing test_tool: Boom" in result["messages"][0].content


@patch("chaos.engine.basic_agent.ChatOpenAI")
@patch("chaos.engine.basic_agent.StateGraph")
def test_execute(mock_graph, mock_llm, mock_deps):
    """Runs the agent loop and returns the final response."""
    agent = BasicAgent(**mock_deps)

    mock_builder = mock_graph.return_value
    mock_compiled = mock_builder.compile.return_value

    mock_compiled.invoke.return_value = {
        "messages": [HumanMessage(content="hi"), AIMessage(content="Final Answer")]
    }

    agent.refresh = MagicMock()

    result = agent.execute("hi")

    assert result == "Final Answer"
    mock_compiled.invoke.assert_called()
    agent.refresh.assert_called_once()
