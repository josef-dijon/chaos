from pathlib import Path
import json
from typing import Any, Dict, List, Optional, cast

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from chaos.domain.instructions import Instructions
from chaos.domain.memory_config import MemoryConfig
from chaos.domain.memory_persona_config import MemoryPersonaConfig
from chaos.domain.profile import Profile
from chaos.domain.search_weights import SearchWeights
from chaos.domain.stm_search_config import StmSearchConfig
from chaos.domain.tuning_policy import TuningPolicy

SCHEMA_VERSION = "1.0"
IDENTITY_IMPLICIT_TUNING_BLACKLIST = [
    "schema_version",
    "tuning_policy",
    "memory.subconscious",
    "memory.actor",
    "loop_definition",
]


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


def _inline_schema_refs(schema: dict) -> Dict[str, Any]:
    """
    Inlines JSON schema $ref references for easier masking.

    Args:
        schema: The JSON schema to inline.

    Returns:
        A schema with $ref references replaced by definitions.
    """
    definitions = schema.get("$defs", {})

    def _resolve(node: object) -> object:
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if isinstance(ref, str) and ref.startswith("#/$defs/"):
                    key = ref.split("/")[-1]
                    resolved = definitions.get(key, {})
                    resolved_payload = _resolve(resolved)
                    merged = {k: v for k, v in node.items() if k != "$ref"}
                    if isinstance(resolved_payload, dict):
                        return {**resolved_payload, **merged}
                    return resolved_payload
            return {k: _resolve(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [_resolve(item) for item in node]
        return node

    resolved = _resolve(schema)
    if isinstance(resolved, dict):
        return cast(Dict[str, Any], resolved)
    return {}


def _schema_has_tunable_content(schema: dict) -> bool:
    """
    Determines whether a masked schema node contains tunable fields.

    Args:
        schema: The schema node to evaluate.

    Returns:
        True if the schema contains tunable content.
    """
    if not schema:
        return False
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        return True
    if "items" in schema and schema.get("items"):
        return True
    return False


def _mask_schema(
    schema: dict,
    tuning_policy: TuningPolicy,
    implicit_blacklist: List[str],
    prefix: str = "",
) -> Dict[str, Any]:
    """
    Masks a JSON schema based on tuning policy rules.

    Args:
        schema: The schema node to mask.
        tuning_policy: The tuning policy to enforce.
        implicit_blacklist: Always-blocked paths enforced by the system.
        prefix: The dot-path prefix for the schema node.

    Returns:
        The masked schema node.
    """
    if not schema:
        return {}
    properties = schema.get("properties")
    if isinstance(properties, dict):
        masked_properties: dict[str, dict] = {}
        required_fields = set(schema.get("required", []))
        new_required: list[str] = []
        for name, prop_schema in properties.items():
            path = f"{prefix}.{name}" if prefix else name
            masked_prop = _mask_schema(
                prop_schema, tuning_policy, implicit_blacklist, path
            )
            allowed = tuning_policy.is_allowed(path, implicit_blacklist)
            if not allowed and not _schema_has_tunable_content(masked_prop):
                continue
            if not masked_prop and not allowed:
                continue
            if not masked_prop and allowed:
                continue
            masked_properties[name] = masked_prop
            if name in required_fields:
                new_required.append(name)
        updated = dict(schema)
        updated["properties"] = masked_properties
        if new_required:
            updated["required"] = new_required
        else:
            updated.pop("required", None)
        if not _schema_has_tunable_content(updated):
            return {}
        return updated
    if "items" in schema:
        updated = dict(schema)
        updated["items"] = _mask_schema(
            schema.get("items", {}),
            tuning_policy,
            implicit_blacklist,
            prefix,
        )
        return updated
    if prefix and not tuning_policy.is_allowed(prefix, implicit_blacklist):
        return {}
    return dict(schema)


def _mask_payload(
    payload: dict,
    tuning_policy: TuningPolicy,
    implicit_blacklist: List[str],
    prefix: str = "",
) -> dict:
    """
    Masks an identity payload based on tuning policy rules.

    Args:
        payload: The payload to mask.
        tuning_policy: The tuning policy to enforce.
        implicit_blacklist: Always-blocked paths enforced by the system.
        prefix: The dot-path prefix for the payload node.

    Returns:
        The masked payload.
    """
    masked: Dict[str, Any] = {}
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else key
        allowed = tuning_policy.is_allowed(path, implicit_blacklist)
        if isinstance(value, dict):
            masked_child = _mask_payload(value, tuning_policy, implicit_blacklist, path)
            if allowed or masked_child:
                masked[key] = masked_child
            continue
        if isinstance(value, list):
            if allowed:
                masked[key] = value
            continue
        if allowed:
            masked[key] = value
    return masked


class Identity(BaseModel):
    """
    The persistent state of an agent, containing profile, instructions, memory,
    and capability access rules.
    """

    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description=(
            "Identity schema version for compatibility checks. This should not be "
            "changed by tuning workflows."
        ),
        json_schema_extra={"weight": 10},
    )
    profile: Profile = Field(
        ...,
        description="Identity profile containing name, role, and core values.",
        json_schema_extra={"weight": 9},
    )
    instructions: Instructions = Field(
        ...,
        description=(
            "Instruction set for system prompts and operational notes. "
            "Operational notes are the primary tunable behavior updates."
        ),
        json_schema_extra={"weight": 8},
    )
    loop_definition: str = Field(
        default="default",
        description=(
            "Loop definition identifier that selects the agent reasoning flow. "
            "Changing this alters the core loop behavior."
        ),
        json_schema_extra={"weight": 10},
    )
    tool_manifest: List[str] = Field(
        default_factory=list,
        description=(
            "Legacy list of allowed tool names. When tool_whitelist is set, "
            "it overrides this list."
        ),
        json_schema_extra={"weight": 6},
    )
    memory: MemoryConfig = Field(
        default_factory=_default_memory_config,
        description=(
            "Memory configuration for actor and subconscious personas, including "
            "STM behavior and collection names."
        ),
        json_schema_extra={"weight": 8},
    )
    tuning_policy: TuningPolicy = Field(
        default_factory=TuningPolicy,
        description=(
            "Tuning policy that declares which identity paths the subconscious "
            "may modify."
        ),
        json_schema_extra={"weight": 10},
    )

    # Access Control (Phase 2 Expansion)
    skills_whitelist: Optional[List[str]] = Field(
        default=None,
        description=(
            "Explicit list of allowed skill names. Null means all skills are available."
        ),
        json_schema_extra={"weight": 7},
    )
    skills_blacklist: Optional[List[str]] = Field(
        default=None,
        description="Explicit list of forbidden skill names.",
        json_schema_extra={"weight": 7},
    )
    knowledge_whitelist: Optional[List[str]] = Field(
        default=None,
        description=(
            "Explicit list of allowed knowledge domains. Null means all domains "
            "are available."
        ),
        json_schema_extra={"weight": 7},
    )
    knowledge_blacklist: Optional[List[str]] = Field(
        default=None,
        description="Explicit list of forbidden knowledge domains.",
        json_schema_extra={"weight": 7},
    )
    tool_whitelist: Optional[List[str]] = Field(
        default=None,
        description=(
            "Explicit list of allowed tool names. Null means all tools are available."
        ),
        json_schema_extra={"weight": 7},
    )
    tool_blacklist: Optional[List[str]] = Field(
        default=None,
        description="Explicit list of forbidden tool names.",
        json_schema_extra={"weight": 7},
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

    @property
    def implicit_tuning_blacklist(self) -> List[str]:
        """
        Returns the implicit tuning policy blacklist for this identity.

        Returns:
            The implicit blacklist entries enforced by the system.
        """
        return list(IDENTITY_IMPLICIT_TUNING_BLACKLIST)

    def get_tunable_schema(self) -> dict:
        """
        Returns the JSON schema masked by the tuning policy.

        Returns:
            The masked JSON schema the subconscious is allowed to use.
        """
        raw_schema = self.model_json_schema()
        inlined_schema = _inline_schema_refs(raw_schema)
        masked_schema = _mask_schema(
            inlined_schema,
            self.tuning_policy,
            self.implicit_tuning_blacklist,
        )
        masked_schema.pop("$defs", None)
        return masked_schema

    def get_masked_identity(self) -> dict:
        """
        Returns a masked identity payload based on tuning policy rules.

        Returns:
            The masked identity payload.
        """
        payload = self.model_dump(mode="json")
        return _mask_payload(
            payload, self.tuning_policy, self.implicit_tuning_blacklist
        )

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

    def patch_instructions(self, note: str) -> bool:
        """
        Updates the operational notes with a new learning.

        Args:
            note: The new instruction or observation to add.

        Returns:
            True if the note was added, otherwise False.
        """
        allowed = self.tuning_policy.is_allowed(
            "instructions.operational_notes", self.implicit_tuning_blacklist
        )
        if not allowed:
            return False
        self.instructions.operational_notes.append(note)
        return True
