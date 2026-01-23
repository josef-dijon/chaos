from typing import List, Optional, TypeVar, Generic, Protocol

T = TypeVar("T")


class NamedItem(Protocol):
    name: str


class Library(Generic[T]):
    """
    Abstract base class for registry-based libraries with access control.
    """

    def apply_access_control(
        self,
        items: List[T],
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[T]:
        """
        Filters a list of named items based on whitelist/blacklist.
        Assumes items have a 'name' attribute.
        """
        # We need T to have a 'name' attribute. Protocol NamedItem handles this in static typing,
        # but at runtime we just access .name

        if whitelist is not None:
            return [item for item in items if getattr(item, "name", "") in whitelist]

        if blacklist is not None:
            return [
                item for item in items if getattr(item, "name", "") not in blacklist
            ]

        return items
