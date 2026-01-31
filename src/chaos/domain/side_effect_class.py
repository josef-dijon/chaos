"""Side-effect classifications for retry safety."""

from enum import Enum


class SideEffectClass(str, Enum):
    """Allowed side-effect classes for blocks."""

    NONE = "none"
    IDEMPOTENT = "idempotent"
    NON_IDEMPOTENT = "non_idempotent"
