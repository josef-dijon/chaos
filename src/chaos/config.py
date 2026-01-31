from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import (
    DotEnvSettingsSource,
    EnvSettingsSource,
    JsonConfigSettingsSource,
)

DEFAULT_CHAOS_DIR = Path(".chaos")
DEFAULT_CONFIG_PATH = DEFAULT_CHAOS_DIR / "config.json"


class Config(BaseSettings):
    """
    Application configuration loaded from environment variables, .env, and JSON.
    """

    openai_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenAI API key used for LLM access."
    )
    model_name: str = Field(
        default="gpt-4o", description="Default model name for the agent runtime."
    )
    litellm_use_proxy: bool = Field(
        default=False, description="Route LLM traffic through the LiteLLM proxy."
    )
    litellm_proxy_url: Optional[str] = Field(
        default=None, description="LiteLLM proxy base URL."
    )
    litellm_proxy_api_key: Optional[SecretStr] = Field(
        default=None, description="LiteLLM proxy API key."
    )
    env: str = Field(default="dev", description="Execution environment name.")
    chaos_dir: Path = Field(
        default=DEFAULT_CHAOS_DIR, description="Root directory for CHAOS artifacts."
    )
    chroma_db_path: Optional[Path] = Field(
        default=None, description="Path to the Chroma vector store."
    )
    raw_db_path: Optional[Path] = Field(
        default=None, description="Path to the raw SQLite event store."
    )
    block_stats_path: Optional[Path] = Field(
        default=None, description="Path to the block stats JSON store."
    )
    tool_root: Optional[Path] = Field(
        default=None, description="Root directory for file tool access."
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="forbid"
    )

    @staticmethod
    def _resolve_relative_path(path: Path, chaos_dir: Path) -> Path:
        """
        Resolves a relative path by anchoring it under the CHAOS directory.

        Args:
            path: The input path to resolve.
            chaos_dir: The root directory for CHAOS artifacts.

        Returns:
            A resolved path under the CHAOS directory when relative.
        """
        if path.is_absolute():
            return path

        chaos_parts = chaos_dir.parts
        if path.parts[: len(chaos_parts)] == chaos_parts:
            return path
        return chaos_dir / path

    @model_validator(mode="after")
    def _apply_defaults(self) -> "Config":
        """
        Ensures default storage paths are derived from the CHAOS directory.

        Returns:
            The validated configuration instance.
        """
        base_db_dir = self.chaos_dir / "db"
        if self.chroma_db_path is None:
            self.chroma_db_path = base_db_dir / "chroma"
        else:
            self.chroma_db_path = self._resolve_relative_path(
                self.chroma_db_path, self.chaos_dir
            )

        if self.raw_db_path is None:
            self.raw_db_path = base_db_dir / "raw.sqlite"
        else:
            self.raw_db_path = self._resolve_relative_path(
                self.raw_db_path, self.chaos_dir
            )
        if self.block_stats_path is None:
            self.block_stats_path = base_db_dir / "block_stats.json"
        else:
            self.block_stats_path = self._resolve_relative_path(
                self.block_stats_path, self.chaos_dir
            )
        if self.tool_root is None:
            self.tool_root = Path.cwd().resolve()
        if self.litellm_use_proxy and not self.litellm_proxy_url:
            raise ValueError(
                "LiteLLM proxy URL is required when proxy mode is enabled."
            )
        return self

    @staticmethod
    def _secret_to_str(secret: Optional[SecretStr]) -> Optional[str]:
        """Return the underlying secret value if present."""

        if secret is None:
            return None
        return secret.get_secret_value()

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """
        Loads configuration from a JSON file when present.

        Args:
            path: Optional override path for the JSON config file.

        Returns:
            A validated configuration object.
        """
        config_path = path or DEFAULT_CONFIG_PATH
        if not config_path.exists():
            return cls()

        json_source = JsonConfigSettingsSource(cls, json_file=config_path)
        dotenv_source = DotEnvSettingsSource(cls)
        env_source = EnvSettingsSource(cls)
        merged: dict[str, object] = {}
        merged.update(json_source())
        merged.update(dotenv_source())
        merged.update(env_source())
        return cls.model_validate(merged)

    def get_openai_api_key(self) -> Optional[str]:
        """
        Returns the OpenAI API key for runtime usage.

        Returns:
            The OpenAI API key or None if unset.
        """
        return self._secret_to_str(self.openai_api_key)

    def use_litellm_proxy(self) -> bool:
        """Returns whether LiteLLM proxy usage is enabled."""

        return self.litellm_use_proxy

    def get_litellm_proxy_url(self) -> Optional[str]:
        """Returns the configured LiteLLM proxy base URL."""

        return self.litellm_proxy_url

    def get_litellm_proxy_api_key(self) -> Optional[str]:
        """Returns the configured LiteLLM proxy API key."""

        return self._secret_to_str(self.litellm_proxy_api_key)

    def get_model_name(self) -> str:
        """
        Returns the configured model name.

        Returns:
            The model name string.
        """
        return self.model_name

    def get_chroma_db_path(self) -> Path:
        """
        Returns the path to the Chroma vector store.

        Returns:
            A path to the Chroma storage directory.
        """
        if self.chroma_db_path is None:
            raise ValueError("Chroma database path is not configured.")
        return self.chroma_db_path

    def get_raw_db_path(self) -> Path:
        """
        Returns the path to the raw SQLite event store.

        Returns:
            A path to the raw SQLite database.
        """
        if self.raw_db_path is None:
            raise ValueError("Raw database path is not configured.")
        return self.raw_db_path

    def get_block_stats_path(self) -> Path:
        """Returns the path to the block stats JSON store.

        Returns:
            A path to the block stats JSON file.
        """

        if self.block_stats_path is None:
            raise ValueError("Block stats path is not configured.")
        return self.block_stats_path

    def get_tool_root(self) -> Path:
        """
        Returns the root directory for file tool operations.

        Returns:
            The root directory path for file tool access.
        """
        if self.tool_root is None:
            raise ValueError("Tool root path is not configured.")
        return self.tool_root

    def get_chaos_dir(self) -> Path:
        """
        Returns the root directory for CHAOS artifacts.

        Returns:
            The CHAOS root directory path.
        """
        return self.chaos_dir

    def get_identity_path(self, agent_id: str) -> Path:
        """
        Returns the identity file path for a given agent id.

        Args:
            agent_id: The unique agent identifier.

        Returns:
            The identity file path under the CHAOS identities directory.
        """
        return self.chaos_dir / "identities" / f"{agent_id}.identity.json"

    def get_memory_paths(self) -> tuple[Path, Path]:
        """
        Returns the raw and chroma database paths.

        Returns:
            A tuple containing the raw db path and chroma db path.
        """
        return (self.get_raw_db_path(), self.get_chroma_db_path())
