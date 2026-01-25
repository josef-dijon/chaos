"""Helpers for constructing configuration instances."""

from pathlib import Path
from typing import Optional

from chaos.config import Config


class ConfigProvider:
    """
    Provides configuration instances without import-time side effects.

    Args:
        path: Optional override path for the JSON config file.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path

    def load(self) -> Config:
        """
        Loads a configuration instance using the configured path.

        Returns:
            A validated configuration object.
        """
        return Config.load(self._path)
