from pydantic import BaseModel, ConfigDict, Field

from chaos.domain.memory_persona_config import MemoryPersonaConfig


class MemoryConfig(BaseModel):
    """
    Defines memory configuration for actor and subconscious personas.

    Args:
        actor: Memory configuration for the actor persona.
        subconscious: Memory configuration for the subconscious persona.
    """

    actor: MemoryPersonaConfig = Field(
        ...,
        description=(
            "Memory configuration for the actor persona, including STM behavior and "
            "collection identifiers."
        ),
        json_schema_extra={"weight": 8},
    )
    subconscious: MemoryPersonaConfig = Field(
        ...,
        description=(
            "Memory configuration for the subconscious persona, including STM behavior "
            "and collection identifiers."
        ),
        json_schema_extra={"weight": 8},
    )

    model_config = ConfigDict(extra="forbid")
