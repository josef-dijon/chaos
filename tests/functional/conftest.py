import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_of_chaos.config import Config
from agent_of_chaos.config_provider import ConfigProvider


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """
    Creates an isolated workspace for functional tests.
    """
    # Ensure we have an API key for functional tests
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment or .env")

    config = Config(openai_api_key=api_key, chaos_dir=tmp_path / ".chaos")
    monkeypatch.setattr(ConfigProvider, "load", lambda self: config)

    # Change CWD to tmp_path
    monkeypatch.chdir(tmp_path)

    return tmp_path
