from pathlib import Path
import json
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from chaos.domain.instructions import Instructions
from chaos.domain.memory_config import MemoryConfig
from chaos.domain.memory_persona_config import MemoryPersonaConfig
from chaos.domain.profile import Profile
from chaos.domain.search_weights import SearchWeights
from chaos.domain.stm_search_config import StmSearchConfig
from chaos.domain.tuning_policy import TuningPolicy

SCHEMA_VERSION = "1.0"


def agent_id_from_path(identity_path: Path) -> str:
    """
    Derives an agent id from an identity filename.

    Args:
        identity_path: The path to the identity file.

    Returns:
        The derived agent id.
    """
    filename = identity_path.name
    suffix = ".identity.json"
    if filename.endswith(suffix):
        return filename[: -len(suffix)]
    if filename.endswith(".json"):
        return filename[: -len(".json")]
    return identity_path.stem


def _default_actor_memory_config() -> MemoryPersonaConfig:
    """
    Returns the default memory configuration for the actor persona.

    Returns:
        The default actor memory configuration.
    """
    return MemoryPersonaConfig(
        ltm_collection="default__actor__ltm",
        stm_window_size=20,
        stm_search=StmSearchConfig(
            engine="rapidfuzz",
            algorithm="token_set_ratio",
            threshold=60,
            top_k=8,
            recency_half_life_seconds=86400,
            weights=SearchWeights(
                similarity=1.0,
                recency=1.0,
                kind_boosts={
                    "user_input": 1.0,
                    "actor_output": 0.9,
                    "tool_call": 0.6,
                    "tool_result": 0.7,
                    "system_event": 0.3,
                    "error": 1.2,
                },
                visibility_boosts={"external": 1.0, "internal": 0.4},
            ),
        ),
    )


def _default_subconscious_memory_config() -> MemoryPersonaConfig:
    """
    Returns the default memory configuration for the subconscious persona.

    Returns:
        The default subconscious memory configuration.
    """
    return MemoryPersonaConfig(
        ltm_collection="default__subconscious__ltm",
        stm_window_size=50,
        stm_search=StmSearchConfig(
            engine="rapidfuzz",
            algorithm="token_set_ratio",
            threshold=55,
            top_k=12,
            recency_half_life_seconds=604800,
            weights=SearchWeights(
                similarity=1.0,
                recency=1.0,
                kind_boosts={
                    "subconscious_prompt": 0.8,
                    "subconscious_output": 1.0,
                    "user_input": 1.0,
                    "actor_output": 1.0,
                },
                visibility_boosts={"external": 1.0, "internal": 1.0},
            ),
        ),
    )


def _default_memory_config() -> MemoryConfig:
    """
    Builds the default memory configuration for a new identity.

    Returns:
        The default memory configuration.
    """
    return MemoryConfig(
        actor=_default_actor_memory_config(),
        subconscious=_default_subconscious_memory_config(),
    )


def _memory_config_for_agent(agent_id: str) -> MemoryConfig:
    """
    Builds a default memory configuration using an agent-specific prefix.

    Args:
        agent_id: The agent identifier.

    Returns:
        The memory configuration for the agent.
    """
    actor_config = _default_actor_memory_config()
    subconscious_config = _default_subconscious_memory_config()
    actor_config.ltm_collection = f"{agent_id}__actor__ltm"
    subconscious_config.ltm_collection = f"{agent_id}__subconscious__ltm"
    return MemoryConfig(actor=actor_config, subconscious=subconscious_config)


class Identity(BaseModel):
    """
    The persistent state of an agent, containing profile, instructions, and capabilities.

    Args:
        schema_version: Identity schema version.
        profile: Immutable identity profile.
        instructions: Mutable operational instructions.
        loop_definition: Loop definition identifier.
        tool_manifest: List of allowed tool names.
        memory: Memory configuration for actor and subconscious.
        tuning_policy: Identity tuning policy settings.
        skills_whitelist: Allowed skills (null = all).
        skills_blacklist: Forbidden skills.
        knowledge_whitelist: Allowed knowledge domains (null = all).
        knowledge_blacklist: Forbidden knowledge domains.
        tool_whitelist: Allowed tools (null = all).
        tool_blacklist: Forbidden tools.
    """

    schema_version: str = Field(
        default=SCHEMA_VERSION, description="Identity schema version."
    )
    profile: Profile
    instructions: Instructions
    loop_definition: str = Field(
        default="default", description="Loop definition identifier."
    )
    tool_manifest: List[str] = Field(
        default_factory=list, description="List of allowed tool names."
    )
    memory: MemoryConfig = Field(
        default_factory=_default_memory_config,
        description="Memory configuration for actor and subconscious.",
    )
    tuning_policy: TuningPolicy = Field(
        default_factory=TuningPolicy, description="Identity tuning policy settings."
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

    _agent_id: str = PrivateAttr("")

    model_config = ConfigDict(extra="forbid")

    @property
    def agent_id(self) -> str:
        """
        Returns the agent id derived from the identity path.

        Returns:
            The derived agent id.
        """
        return self._agent_id

    def set_agent_id(self, agent_id: str) -> None:
        """
        Sets the agent id on this identity.

        Args:
            agent_id: The derived agent id from the identity path.
        """
        self._agent_id = agent_id

    def resolve_tool_whitelist(self) -> Optional[List[str]]:
        """
        Resolves the effective tool whitelist for this identity.

        Returns:
            The effective whitelist to apply, or None to allow all tools.
        """
        if self.tool_whitelist is not None:
            return self.tool_whitelist
        if self.tool_manifest:
            return list(self.tool_manifest)
        return None

    @model_validator(mode="after")
    def _validate_schema_version(self) -> "Identity":
        """
        Validates the schema version for the identity.

        Returns:
            The validated identity.
        """
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported identity schema version: {self.schema_version}."
            )
        return self

    @classmethod
    def create_default(cls, agent_id: str) -> "Identity":
        """
        Creates a new identity using the default template.

        Args:
            agent_id: The identifier derived from the identity filename.

        Returns:
            A new Identity instance.
        """
        identity = cls(
            profile=Profile(
                name=agent_id or "Chaos",
                role="Assistant",
                core_values=["Helpful", "Harmless", "Honest"],
            ),
            instructions=Instructions(system_prompts=["You are a helpful assistant."]),
            tool_manifest=[],
            memory=_memory_config_for_agent(agent_id or "default"),
        )
        identity.set_agent_id(agent_id)
        return identity

    def save(self, path: Path) -> None:
        """
        Serializes the Identity to a JSON file.

        Args:
            path: The file path to save to.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            handle.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "Identity":
        """
        Loads an Identity from a JSON file.

        Args:
            path: The file path to load from.

        Returns:
            An Identity instance.
        """
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        identity = cls.model_validate(payload)
        identity.set_agent_id(agent_id_from_path(path))
        return identity

    def patch_instructions(self, note: str) -> None:
        """
        Updates the operational notes with a new learning.

        Args:
            note: The new instruction or observation to add.
        """
        self.instructions.operational_notes.append(note)
