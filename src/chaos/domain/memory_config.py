from pydantic import BaseModel, ConfigDict

from chaos.domain.memory_persona_config import MemoryPersonaConfig


class MemoryConfig(BaseModel):
    """
    Defines memory configuration for actor and subconscious personas.

    Args:
        actor: Memory configuration for the actor persona.
        subconscious: Memory configuration for the subconscious persona.
    """

    actor: MemoryPersonaConfig
    subconscious: MemoryPersonaConfig

    model_config = ConfigDict(extra="forbid")
