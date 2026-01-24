from pathlib import Path
from typing import List

import pytest
from typer.testing import CliRunner
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from agent_of_chaos.config import Config
from agent_of_chaos.config_provider import ConfigProvider
from agent_of_chaos.engine import basic_agent as basic_agent_module


class FakeChatOpenAI:
    """
    Deterministic fake LLM for functional tests.

    Args:
        args: Unused positional arguments.
        kwargs: Unused keyword arguments.
    """

    def __init__(self, *args, **kwargs) -> None:
        self._bound_tools: List[dict] = []

    def bind_tools(self, tools: List[dict]) -> "FakeChatOpenAI":
        """
        Records bound tools for compatibility with the agent interface.

        Args:
            tools: Tool schema list from the agent.

        Returns:
            The same fake instance for chaining.
        """
        self._bound_tools = tools
        return self

    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        """
        Returns a deterministic response based on the prompt content.

        Args:
            messages: The messages passed to the LLM.

        Returns:
            An AIMessage response.
        """
        system_text = " ".join(
            str(message.content)
            for message in messages
            if isinstance(message, SystemMessage)
        ).lower()
        last_human = next(
            (
                message
                for message in reversed(messages)
                if isinstance(message, HumanMessage)
            ),
            None,
        )
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content="File written successfully.")
        if last_human:
            prompt = str(last_human.content)
            if "Analyze the recent interaction logs" in prompt:
                return AIMessage(content="Always respond like a pirate.")
            if "Write 'Functional Test'" in prompt:
                return AIMessage(
                    content="Writing file.",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {
                                "file_path": "func_test.txt",
                                "content": "Functional Test",
                            },
                            "id": "write-file-1",
                        }
                    ],
                )
            if "What is my favorite book" in prompt:
                return AIMessage(
                    content="Your favorite book is The Hitchhiker's Guide to the Galaxy."
                )
            if "Say hello again" in prompt:
                if "pirate" in system_text:
                    return AIMessage(content="Ahoy matey!")
                return AIMessage(content="Hello again.")
            if "Say hello" in prompt:
                if "pirate" in system_text:
                    return AIMessage(content="Ahoy matey!")
                return AIMessage(content="Hello.")
            if "My favorite book is" in prompt:
                return AIMessage(content="Got it.")
        return AIMessage(content="Okay.")


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """
    Creates an isolated workspace for functional tests.
    """
    config = Config(
        openai_api_key="test-key",
        chaos_dir=tmp_path / ".chaos",
        tool_root=tmp_path,
    )
    monkeypatch.setattr(ConfigProvider, "load", lambda self: config)
    monkeypatch.setattr(basic_agent_module, "ChatOpenAI", FakeChatOpenAI)

    # Change CWD to tmp_path
    monkeypatch.chdir(tmp_path)

    return tmp_path
