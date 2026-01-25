from typing import List

from pydantic import BaseModel, ConfigDict, Field


def _path_covers_target(scope: str, target_path: str) -> bool:
    """
    Checks whether a scoped path covers the target path.

    Args:
        scope: The scoped path that may cover the target.
        target_path: The target path to evaluate.

    Returns:
        True if scope equals the target or is a parent path of the target.
    """
    if not scope:
        return False
    if scope == target_path:
        return True
    return target_path.startswith(f"{scope}.")


def _is_covered_by(target_path: str, scopes: List[str]) -> bool:
    """
    Determines whether the target path is covered by any scope path.

    Args:
        target_path: The path being checked.
        scopes: The list of scope paths.

    Returns:
        True if any scope path covers the target path.
    """
    return any(_path_covers_target(scope, target_path) for scope in scopes)


class TuningPolicy(BaseModel):
    """
    Controls which subconscious tuning operations are permitted.

    Args:
        whitelist: Allowed dot-separated identity paths.
        blacklist: Forbidden dot-separated identity paths.
    """

    whitelist: List[str] = Field(
        default_factory=lambda: ["instructions.operational_notes"],
        description="Allowed dot-separated identity paths.",
    )
    blacklist: List[str] = Field(
        default_factory=list,
        description="Forbidden dot-separated identity paths.",
    )

    model_config = ConfigDict(extra="forbid")

    def is_allowed(self, target_path: str, implicit_blacklist: List[str]) -> bool:
        """
        Determines whether a target path is allowed for modification.

        Args:
            target_path: The dot-separated path being modified.
            implicit_blacklist: Always-blocked paths enforced by the system.

        Returns:
            True if the target path is allowed, otherwise False.
        """
        if _is_covered_by(target_path, implicit_blacklist):
            return False
        if _is_covered_by(target_path, self.blacklist):
            return False
        return _is_covered_by(target_path, self.whitelist)
