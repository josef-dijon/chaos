import pytest
from unittest.mock import MagicMock, patch, call, ANY
from pathlib import Path
from agent_of_chaos.core.agent import Agent


@pytest.fixture
def mock_dependencies():
    with (
        patch("agent_of_chaos.core.agent.Identity") as mock_ident,
        patch("agent_of_chaos.core.agent.BasicAgent") as mock_basic,
        patch("agent_of_chaos.core.agent.MemoryContainer") as mock_mem,
        patch("agent_of_chaos.core.agent.ToolLibrary") as mock_tools,
        patch("agent_of_chaos.core.agent.SkillsLibrary") as mock_skills,
        patch("agent_of_chaos.core.agent.KnowledgeLibrary") as mock_know,
        patch("agent_of_chaos.core.agent.ConfigProvider") as mock_config_provider,
    ):
        # Setup common returns
        mock_ident_instance = MagicMock()
        mock_ident.load.return_value = mock_ident_instance
        mock_ident.create_default.return_value = mock_ident_instance
        mock_ident.return_value = mock_ident_instance
        mock_ident_instance.profile.role = "tester"
        mock_ident_instance.agent_id = "tester"
        mock_ident_instance.tuning_policy.allow_subconscious_identity_updates = True

        mock_mem_instance = MagicMock()
        mock_mem.return_value = mock_mem_instance
        mock_mem_instance.actor_view.return_value = MagicMock()
        mock_mem_instance.subconscious_view.return_value = MagicMock()

        mock_config = MagicMock()
        mock_config_provider.return_value.load.return_value = mock_config

        yield {
            "ident": mock_ident,
            "basic": mock_basic,
            "mem": mock_mem,
            "tools": mock_tools,
            "skills": mock_skills,
            "know": mock_know,
            "config": mock_config,
        }


def test_agent_init_existing_identity(mock_dependencies):
    mocks = mock_dependencies
    with patch("pathlib.Path.exists", return_value=True):
        agent = Agent(identity_path=Path("dummy_path"))

    # It loads the main identity once and reuses it for the subconscious
    assert mocks["ident"].load.call_count == 1
    mocks["ident"].load.assert_any_call(Path("dummy_path"))

    mocks["mem"].assert_called_once_with(
        agent_id="tester",
        identity=mocks["ident"].load.return_value,
        config=mocks["config"],
    )

    assert agent.identity.profile.role == "tester"
    # BasicAgent called twice: actor + subconscious
    assert mocks["basic"].call_count == 2
    mocks["basic"].assert_has_calls(
        [
            call(
                identity=mocks["ident"].load.return_value,
                config=mocks["config"],
                memory=mocks["mem"].return_value.actor_view.return_value,
                skills_lib=ANY,
                knowledge_lib=ANY,
                tool_lib=ANY,
                identity_path=Path("dummy_path"),
                persona="actor",
            ),
            call(
                identity=mocks["ident"].load.return_value,
                config=mocks["config"],
                memory=mocks["mem"].return_value.subconscious_view.return_value,
                skills_lib=ANY,
                knowledge_lib=ANY,
                tool_lib=ANY,
                identity_path=Path("dummy_path"),
                persona="subconscious",
            ),
        ]
    )


def test_agent_init_new_identity(mock_dependencies):
    mocks = mock_dependencies
    # First exists False (main), second exists True (subconscious fallback check) or False

    with patch("pathlib.Path.exists", return_value=False):
        agent = Agent(identity_path=Path("new_path"))

    mocks["ident"].create_default.assert_called_once_with("new_path")
    mocks["ident"].create_default.return_value.save.assert_called_once_with(
        Path("new_path")
    )


def test_agent_do(mock_dependencies):
    mocks = mock_dependencies

    # Setup actor mock specifically
    mock_actor = MagicMock()
    mock_sub = MagicMock()
    mocks["basic"].side_effect = [mock_actor, mock_sub]
    mocks["mem"].return_value.create_loop_id.return_value = "loop-1"

    with patch("pathlib.Path.exists", return_value=True):
        agent = Agent(Path("dummy"))

    mock_actor.execute.return_value = "Task done"

    result = agent.do("clean up")

    mocks["mem"].return_value.record_event.assert_any_call(
        persona="actor",
        loop_id="loop-1",
        kind="user_input",
        visibility="external",
        content="clean up",
    )
    mock_actor.execute.assert_called()
    mocks["mem"].return_value.record_event.assert_any_call(
        persona="actor",
        loop_id="loop-1",
        kind="actor_output",
        visibility="external",
        content="Task done",
    )
    mocks["mem"].return_value.finalize_loop.assert_called_once_with(
        persona="actor", loop_id="loop-1"
    )
    assert result == "Task done"


def test_agent_learn(mock_dependencies):
    mocks = mock_dependencies
    mock_actor = MagicMock()
    mock_sub = MagicMock()
    mocks["basic"].side_effect = [mock_actor, mock_sub]

    with patch("pathlib.Path.exists", return_value=True):
        agent = Agent(Path("dummy"))

    mocks[
        "mem"
    ].return_value.subconscious_view.return_value.get_recent_stm_as_string.return_value = "History"
    mock_sub.execute.return_value = "New instructions"

    agent.learn("Good job")

    # learn does NOT record feedback to memory in current implementation
    mock_sub.execute.assert_called()
    mocks["ident"].load.return_value.patch_instructions.assert_called_with(
        "New instructions"
    )
    mocks["ident"].load.return_value.save.assert_called()


def test_agent_dream(mock_dependencies):
    with patch("pathlib.Path.exists", return_value=True):
        agent = Agent(Path("dummy"))
    assert agent.dream() == "Dream cycle complete (Stub)."
