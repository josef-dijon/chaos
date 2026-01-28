from enum import Enum
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class RecoveryType(Enum):
    """Enumeration of available recovery strategies."""

    RETRY = "RETRY"
    REPAIR = "REPAIR"
    DEBUG = "DEBUG"
    BUBBLE = "BUBBLE"


class RecoveryPolicy(BaseModel):
    """Base configuration for a recovery strategy."""

    type: RecoveryType
    parameters: Dict[str, Any] = Field(default_factory=dict)


class RetryPolicy(RecoveryPolicy):
    """Policy to retry execution with the same input."""

    type: RecoveryType = RecoveryType.RETRY
    max_attempts: int = Field(default=3, description="Maximum number of retry attempts")
    delay_seconds: float = Field(default=0.0, description="Delay between attempts")


class RepairPolicy(RecoveryPolicy):
    """Policy to modify the request and retry."""

    type: RecoveryType = RecoveryType.REPAIR
    repair_function: str = Field(description="Name of the repair function to apply")


class DebugPolicy(RecoveryPolicy):
    """Policy to enter debug mode."""

    type: RecoveryType = RecoveryType.DEBUG


class BubblePolicy(RecoveryPolicy):
    """Policy to escalate failure to the parent."""

    type: RecoveryType = RecoveryType.BUBBLE
