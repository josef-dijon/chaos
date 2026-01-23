from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Config(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """

    openai_api_key: Optional[str] = None
    chroma_db_path: Path = Path("./chroma_db")
    env: str = "dev"
    model_name: str = "gpt-4o"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Config()
