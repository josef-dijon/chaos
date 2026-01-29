from typing import Optional

from pydantic import BaseModel, Field


class BlockStatsIdentity(BaseModel):
    """Stable identity metadata used for block stats queries."""

    block_name: str = Field(description="Stable block instance name.")
    block_type: str = Field(description="Stable block type identifier.")
    version: Optional[str] = Field(default=None, description="Optional block version.")
