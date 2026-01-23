from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import json


class Profile(BaseModel):
    """
    Represents the immutable core description of an agent.
    """

    name: str = Field(..., description="The name of the agent.")
    role: str = Field(..., description="The primary role or function of the agent.")
    core_values: List[str] = Field(
        ..., description="List of core values guiding the agent's behavior."
    )


class Instructions(BaseModel):
    """
    Represents the mutable operational instructions of an agent.
    """

    operational_notes: List[str] = Field(
        default_factory=list, description="Mutable notes learned from experience."
    )
    system_prompts: List[str] = Field(
        default_factory=list, description="Base system prompts defining behavior."
    )


class Identity(BaseModel):
    """
    The persistent state of an agent, containing profile, instructions, and capabilities.
    """

    profile: Profile
    instructions: Instructions
    tool_manifest: List[str] = Field(
        default_factory=list, description="List of allowed tool names."
    )

    # Access Control (Phase 2 Expansion)
    skills_whitelist: Optional[List[str]] = Field(
        default=None, description="Allowed skills (null = all)."
    )
    skills_blacklist: Optional[List[str]] = Field(
        default=None, description="Forbidden skills."
    )
    knowledge_whitelist: Optional[List[str]] = Field(
        default=None, description="Allowed knowledge domains (null = all)."
    )
    knowledge_blacklist: Optional[List[str]] = Field(
        default=None, description="Forbidden knowledge domains."
    )
    tool_whitelist: Optional[List[str]] = Field(
        default=None, description="Allowed tools (null = all)."
    )
    tool_blacklist: Optional[List[str]] = Field(
        default=None, description="Forbidden tools."
    )

    def save(self, path: Path) -> None:
        """
        Serializes the Identity to a JSON file.

        Args:
            path: The file path to save to.
        """
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "Identity":
        """
        Loads an Identity from a JSON file.

        Args:
            path: The file path to load from.

        Returns:
            An Identity instance.
        """
        with open(path, "r") as f:
            return cls.model_validate_json(f.read())

    def patch_instructions(self, note: str) -> None:
        """
        Updates the operational notes with a new learning.

        Args:
            note: The new instruction or observation to add.
        """
        self.instructions.operational_notes.append(note)
