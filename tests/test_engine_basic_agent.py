import pytest
from unittest.mock import MagicMock, patch, call
from agent_of_chaos.engine.basic_agent import BasicAgent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage


@pytest.fixture
def mock_deps():
    mock_ident = MagicMock()
    mock_ident.profile.name = "TestBot"
    mock_ident.profile.role = "Tester"
    mock_ident.profile.core_values = ["Accuracy"]
    mock_ident.instructions.system_prompts = ["Be precise"]
    mock_ident.instructions.operational_notes = ["No bugs"]
    mock_ident.knowledge_whitelist = []
    mock_ident.knowledge_blacklist = []
    mock_ident.skills_whitelist = []
    mock_ident.skills_blacklist = []
    mock_ident.tool_whitelist = []
    mock_ident.tool_blacklist = []

    mock_mem = MagicMock()
    mock_skills = MagicMock()
    mock_know = MagicMock()
    mock_tools = MagicMock()

    return {
        "identity": mock_ident,
        "memory": mock_mem,
        "skills_lib": mock_skills,
        "knowledge_lib": mock_know,
        "tool_lib": mock_tools,
    }


@patch("agent_of_chaos.engine.basic_agent.ChatOpenAI")
@patch("agent_of_chaos.engine.basic_agent.StateGraph")
def test_init(mock_graph, mock_llm, mock_deps):
    agent = BasicAgent(**mock_deps)
    mock_llm.assert_called()
    mock_graph.assert_called()


@patch("agent_of_chaos.engine.basic_agent.ChatOpenAI")
@patch("agent_of_chaos.engine.basic_agent.StateGraph")
def test_should_continue(mock_graph, mock_llm, mock_deps):
    agent = BasicAgent(**mock_deps)

    msg_with_tool = AIMessage(
        content="use tool", tool_calls=[{"name": "t1", "args": {}, "id": "1"}]
    )
    assert agent.should_continue({"messages": [msg_with_tool]}) == "continue"

    msg_no_tool = AIMessage(content="done")
    assert agent.should_continue({"messages": [msg_no_tool]}) == "end"


@patch("agent_of_chaos.engine.basic_agent.ChatOpenAI")
@patch("agent_of_chaos.engine.basic_agent.StateGraph")
def test_recall(mock_graph, mock_llm, mock_deps):
    mock_deps["memory"].retrieve.return_value = "Memory 1"
    mock_deps["knowledge_lib"].search.return_value = "Knowledge 1"

    agent = BasicAgent(**mock_deps)

    assert agent.recall({"messages": []}) == {"context": ""}

    state = {"messages": [HumanMessage(content="Help me")]}
    result = agent.recall(state)

    assert "LTM: Memory 1" in result["context"]
    assert "Reference Knowledge: Knowledge 1" in result["context"]
    mock_deps["memory"].retrieve.assert_called_with("Help me")


@patch("agent_of_chaos.engine.basic_agent.ChatOpenAI")
@patch("agent_of_chaos.engine.basic_agent.StateGraph")
def test_reason_logic(mock_graph, mock_llm, mock_deps):
    # Setup
    mock_deps["skills_lib"].filter_skills.return_value = [
        MagicMock(name="S1", content="How to test")
    ]

    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "Tests things"
    mock_deps["tool_lib"].filter_tools.return_value = [mock_tool]

    # Mock LLM behavior
    mock_llm_instance = mock_llm.return_value
    mock_bound_llm = MagicMock()
    mock_llm_instance.bind_tools.return_value = mock_bound_llm
    mock_bound_llm.invoke.return_value = AIMessage(content="response")

    agent = BasicAgent(**mock_deps)

    # Run
    state = {"messages": [HumanMessage(content="Hi")], "context": "Previous info"}
    result = agent.reason(state)

    # Assertions
    assert result["messages"][0].content == "response"

    # Check skills fetch
    mock_deps["skills_lib"].filter_skills.assert_called()

    # Check tool binding
    mock_deps["tool_lib"].filter_tools.assert_called()
    mock_llm_instance.bind_tools.assert_called()

    # Check invoke call structure
    call_args = mock_bound_llm.invoke.call_args[0][0]  # List of messages

    # 0: System Prompt
    assert isinstance(call_args[0], SystemMessage)
    assert "Identity: TestBot" in call_args[0].content
    assert "Instructions:\n        Be precise" in call_args[0].content

    # 1: Context (inserted)
    assert isinstance(call_args[1], SystemMessage)
    assert "Relevant Context: Previous info" in call_args[1].content

    # 2: User message
    assert isinstance(call_args[2], HumanMessage)
    assert call_args[2].content == "Hi"


@patch("agent_of_chaos.engine.basic_agent.ChatOpenAI")
@patch("agent_of_chaos.engine.basic_agent.StateGraph")
def test_act(mock_graph, mock_llm, mock_deps):
    agent = BasicAgent(**mock_deps)

    mock_tool = MagicMock()
    mock_tool.run.return_value = "Tool Output"
    mock_deps["tool_lib"].get_tool.return_value = mock_tool

    tool_call = {"name": "test_tool", "args": {"arg": 1}, "id": "call_1"}
    message = AIMessage(content="calling", tool_calls=[tool_call])
    state = {"messages": [message]}

    result = agent.act(state)

    assert len(result["messages"]) == 1
    tool_msg = result["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.content == "Tool Output"
    assert tool_msg.tool_call_id == "call_1"
    mock_tool.run.assert_called_with(arg=1)


@patch("agent_of_chaos.engine.basic_agent.ChatOpenAI")
@patch("agent_of_chaos.engine.basic_agent.StateGraph")
def test_act_tool_error(mock_graph, mock_llm, mock_deps):
    agent = BasicAgent(**mock_deps)

    mock_tool = MagicMock()
    mock_tool.run.side_effect = Exception("Boom")
    mock_deps["tool_lib"].get_tool.return_value = mock_tool

    tool_call = {"name": "test_tool", "args": {}, "id": "call_1"}
    state = {"messages": [AIMessage(content="calling", tool_calls=[tool_call])]}

    result = agent.act(state)
    assert "Error executing test_tool: Boom" in result["messages"][0].content


@patch("agent_of_chaos.engine.basic_agent.ChatOpenAI")
@patch("agent_of_chaos.engine.basic_agent.StateGraph")
def test_execute(mock_graph, mock_llm, mock_deps):
    agent = BasicAgent(**mock_deps)

    mock_builder = mock_graph.return_value
    mock_compiled = mock_builder.compile.return_value

    mock_compiled.invoke.return_value = {
        "messages": [HumanMessage(content="hi"), AIMessage(content="Final Answer")]
    }

    result = agent.execute("hi")

    assert result == "Final Answer"
    mock_compiled.invoke.assert_called()
