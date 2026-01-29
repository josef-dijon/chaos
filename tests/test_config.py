"""Tests for configuration loading and validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from chaos.config import Config
from chaos.config_provider import ConfigProvider


def test_config_load_defaults(tmp_path: Path) -> None:
    """Uses default values when the config file is missing."""
    config = Config.load(path=tmp_path / "missing.json")

    assert config.get_chaos_dir() == Path(".chaos")
    assert config.get_chroma_db_path() == Path(".chaos") / "db" / "chroma"
    assert config.get_raw_db_path() == Path(".chaos") / "db" / "raw.sqlite"
    assert config.get_block_stats_path() == (Path(".chaos") / "db" / "block_stats.json")
    assert config.use_litellm_proxy() is True
    assert config.get_litellm_proxy_url() is None
    assert config.get_litellm_proxy_api_key() is None


def test_config_load_from_file(tmp_path: Path) -> None:
    """Loads configuration values from JSON when present."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "env": "test",
          "model_name": "gpt-4o-mini",
          "openai_api_key": "test-key",
          "litellm_use_proxy": false,
          "litellm_proxy_url": "https://proxy.local",
          "litellm_proxy_api_key": "proxy-key",
          "chroma_db_path": ".chaos/db/chroma",
          "raw_db_path": ".chaos/db/raw.sqlite",
          "block_stats_path": ".chaos/db/block_stats.json"
        }
        """,
        encoding="utf-8",
    )

    config = Config.load(path=config_path)

    assert config.get_model_name() == "gpt-4o-mini"
    assert config.get_openai_api_key() == "test-key"
    assert config.use_litellm_proxy() is False
    assert config.get_litellm_proxy_url() == "https://proxy.local"
    assert config.get_litellm_proxy_api_key() == "proxy-key"
    assert config.get_chroma_db_path() == Path(".chaos") / "db" / "chroma"
    assert config.get_raw_db_path() == Path(".chaos") / "db" / "raw.sqlite"
    assert config.get_block_stats_path() == (Path(".chaos") / "db" / "block_stats.json")


def test_config_provider_loads_custom_path(tmp_path: Path) -> None:
    """Loads configuration via the provider path override."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "model_name": "gpt-4o-mini",
          "openai_api_key": "test-key"
        }
        """,
        encoding="utf-8",
    )

    provider = ConfigProvider(path=config_path)

    config = provider.load()

    assert config.get_model_name() == "gpt-4o-mini"


def test_config_resolves_relative_paths(tmp_path: Path) -> None:
    """Anchors relative storage paths under the CHAOS directory."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "chroma_db_path": "db/custom",
          "raw_db_path": "db/raw.sqlite",
          "block_stats_path": "db/block_stats.json"
        }
        """,
        encoding="utf-8",
    )

    config = Config.load(path=config_path)

    assert config.get_chroma_db_path() == Path(".chaos") / "db" / "custom"
    assert config.get_raw_db_path() == Path(".chaos") / "db" / "raw.sqlite"
    assert config.get_block_stats_path() == (Path(".chaos") / "db" / "block_stats.json")


def test_config_rejects_unknown_fields(tmp_path: Path) -> None:
    """Rejects unexpected keys to enforce schema validation."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "env": "test",
          "unknown": "value"
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        Config.load(path=config_path)


def test_config_identity_path(tmp_path: Path) -> None:
    """Builds identity paths under the CHAOS identities directory."""
    config = Config(chaos_dir=tmp_path / ".chaos")

    assert config.get_identity_path("agent") == (
        tmp_path / ".chaos" / "identities" / "agent.identity.json"
    )


def test_config_memory_paths(tmp_path: Path) -> None:
    """Returns raw and chroma database paths."""
    config = Config(chaos_dir=tmp_path / ".chaos")

    raw_path, chroma_path = config.get_memory_paths()

    assert raw_path == tmp_path / ".chaos" / "db" / "raw.sqlite"
    assert chroma_path == tmp_path / ".chaos" / "db" / "chroma"


def test_config_tool_root_defaults_to_cwd(tmp_path: Path, monkeypatch) -> None:
    """Defaults tool root to the current working directory."""
    monkeypatch.chdir(tmp_path)
    config = Config()

    assert config.get_tool_root() == tmp_path.resolve()
