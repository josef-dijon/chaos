from pydantic import BaseModel, Field


class Skill(BaseModel):
    """
    Represents a reusable capability or prompt pattern.
    """

    name: str = Field(..., description="The unique name of the skill.")
    description: str = Field(..., description="Description of what the skill does.")
    content: str = Field(
        ..., description="The actual prompt or instruction for the skill."
    )
