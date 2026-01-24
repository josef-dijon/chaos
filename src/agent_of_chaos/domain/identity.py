from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator
from pathlib import Path
from typing import Dict, List, Optional
import json

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


class Profile(BaseModel):
    """
    Represents the immutable core description of an agent.
    """

    name: Optional[str] = Field(
        default=None, description="Optional human-friendly display name."
    )
    role: str = Field(..., description="The primary role or function of the agent.")
    core_values: List[str] = Field(
        default_factory=list,
        description="List of core values guiding the agent's behavior.",
    )

    model_config = ConfigDict(extra="forbid")


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

    model_config = ConfigDict(extra="forbid")


class SearchWeights(BaseModel):
    """
    Defines weighting configuration for short-term memory searches.
    """

    similarity: float = Field(default=1.0, description="Weight for similarity ranking.")
    recency: float = Field(default=1.0, description="Weight for recency scoring.")
    kind_boosts: Dict[str, float] = Field(
        default_factory=dict, description="Boosts applied per event kind."
    )
    visibility_boosts: Dict[str, float] = Field(
        default_factory=dict, description="Boosts applied per visibility category."
    )

    model_config = ConfigDict(extra="forbid")


class StmSearchConfig(BaseModel):
    """
    Controls the search behavior for short-term memory retrieval.
    """

    engine: str = Field(default="rapidfuzz", description="Search engine identifier.")
    algorithm: str = Field(default="token_set_ratio", description="Search algorithm.")
    threshold: float = Field(default=60, description="Search similarity threshold.")
    top_k: int = Field(default=8, description="Maximum results to return.")
    recency_half_life_seconds: int = Field(
        default=86400, description="Half-life for recency decay weighting."
    )
    weights: SearchWeights = Field(
        default_factory=SearchWeights, description="Weight tuning for ranking."
    )

    model_config = ConfigDict(extra="forbid")


class MemoryPersonaConfig(BaseModel):
    """
    Defines memory configuration for a persona.
    """

    ltm_collection: str = Field(
        ..., description="Chroma collection name for long-term memory."
    )
    stm_window_size: int = Field(..., description="Short-term memory window size.")
    stm_search: StmSearchConfig = Field(
        ..., description="Search configuration for short-term memory."
    )

    model_config = ConfigDict(extra="forbid")


class MemoryConfig(BaseModel):
    """
    Defines memory configuration for actor and subconscious personas.
    """

    actor: MemoryPersonaConfig
    subconscious: MemoryPersonaConfig

    model_config = ConfigDict(extra="forbid")


class TuningPolicy(BaseModel):
    """
    Controls which subconscious tuning operations are permitted.
    """

    allow_subconscious_identity_updates: bool = Field(
        default=True, description="Allow subconscious to update identity instructions."
    )
    allow_subconscious_memory_tuning: bool = Field(
        default=False, description="Allow subconscious to tune memory configuration."
    )

    model_config = ConfigDict(extra="forbid")


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


class Identity(BaseModel):
    """
    The persistent state of an agent, containing profile, instructions, and capabilities.
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
