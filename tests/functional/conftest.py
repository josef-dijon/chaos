import pytest
from pathlib import Path
from typer.testing import CliRunner
from agent_of_chaos.config import settings


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """
    Creates an isolated workspace for functional tests.
    """
    # Ensure we have an API key for functional tests
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY not found in environment or .env")

    # Change CWD to tmp_path
    monkeypatch.chdir(tmp_path)

    # Update settings to use the tmp_path for data
    monkeypatch.setattr(settings, "chroma_db_path", tmp_path / ".chaos" / "memories")

    return tmp_path
