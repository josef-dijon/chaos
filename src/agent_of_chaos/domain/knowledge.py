from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class KnowledgeItem(BaseModel):
    """
    Represents a unit of static knowledge.
    """

    id: str = Field(..., description="Unique identifier for the knowledge item.")
    content: str = Field(..., description="The text content of the knowledge.")
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorization and access control."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata."
    )
