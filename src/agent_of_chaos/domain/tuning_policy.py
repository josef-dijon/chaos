from pydantic import BaseModel, ConfigDict, Field


class TuningPolicy(BaseModel):
    """
    Controls which subconscious tuning operations are permitted.

    Args:
        allow_subconscious_identity_updates: Allow subconscious to update identity instructions.
        allow_subconscious_memory_tuning: Allow subconscious to tune memory configuration.
    """

    allow_subconscious_identity_updates: bool = Field(
        default=True, description="Allow subconscious to update identity instructions."
    )
    allow_subconscious_memory_tuning: bool = Field(
        default=False, description="Allow subconscious to tune memory configuration."
    )

    model_config = ConfigDict(extra="forbid")
