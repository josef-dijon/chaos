import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator

DEFAULT_CHAOS_DIR = Path(".chaos")
DEFAULT_CONFIG_PATH = DEFAULT_CHAOS_DIR / "config.json"


class Config(BaseModel):
    """
    Application configuration loaded from a JSON file.
    """

    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key used for LLM access."
    )
    model_name: str = Field(
        default="gpt-4o", description="Default model name for the agent runtime."
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

    model_config = ConfigDict(extra="forbid")

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
        return self

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

        with config_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.model_validate(payload)

    def get_openai_api_key(self) -> Optional[str]:
        """
        Returns the OpenAI API key for runtime usage.

        Returns:
            The OpenAI API key or None if unset.
        """
        return self.openai_api_key

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
