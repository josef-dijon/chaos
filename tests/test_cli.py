from typer.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock

from chaos.config import Config
from chaos.cli.main import app

runner = CliRunner()


@patch("chaos.cli.main.ConfigProvider")
@patch("chaos.cli.main.Agent")
@patch("pathlib.Path.exists")
def test_init_creates_identity(mock_exists, mock_agent, mock_config_provider):
    mock_exists.return_value = False
    mock_config_provider.return_value.load.return_value = Config(
        chaos_dir=Path(".chaos")
    )
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Initialized new Chaos Agent" in result.stdout
    mock_agent.assert_called()
    mock_agent.return_value.close.assert_called_once()


@patch("chaos.cli.main.ConfigProvider")
@patch("chaos.cli.main.Agent")
@patch("pathlib.Path.exists")
def test_init_already_exists(mock_exists, mock_agent, mock_config_provider):
    mock_exists.return_value = True
    mock_config_provider.return_value.load.return_value = Config(
        chaos_dir=Path(".chaos")
    )
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Identity already exists" in result.stdout
    mock_agent.assert_not_called()
    mock_config_provider.return_value.load.assert_called()


@patch("chaos.cli.main.ConfigProvider")
@patch("chaos.cli.main.Agent")
def test_do(mock_agent, mock_config_provider):
    mock_config_provider.return_value.load.return_value = Config(
        chaos_dir=Path(".chaos")
    )
    mock_agent.return_value.do.return_value = "Done"
    result = runner.invoke(app, ["do", "work"])
    assert result.exit_code == 0
    assert "Done" in result.stdout
    mock_agent.return_value.do.assert_called_with("work")
    mock_agent.return_value.close.assert_called_once()


@patch("chaos.cli.main.ConfigProvider")
@patch("chaos.cli.main.Agent")
def test_learn(mock_agent, mock_config_provider):
    mock_config_provider.return_value.load.return_value = Config(
        chaos_dir=Path(".chaos")
    )
    mock_agent.return_value.learn.return_value = "Learned X"
    result = runner.invoke(app, ["learn", "feedback"])
    assert result.exit_code == 0
    assert "Learned X" in result.stdout
    mock_agent.return_value.learn.assert_called_with("feedback")
    mock_agent.return_value.close.assert_called_once()


@patch("chaos.cli.main.ConfigProvider")
@patch("chaos.cli.main.Agent")
def test_dream(mock_agent, mock_config_provider):
    mock_config_provider.return_value.load.return_value = Config(
        chaos_dir=Path(".chaos")
    )
    mock_agent.return_value.dream.return_value = "Dreamt"
    result = runner.invoke(app, ["dream"])
    assert result.exit_code == 0
    assert "Dreamt" in result.stdout
    mock_agent.return_value.dream.assert_called()
    mock_agent.return_value.close.assert_called_once()
