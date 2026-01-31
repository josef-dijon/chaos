from chaos.infra.library import Library, NamedItem
from dataclasses import dataclass
from typing import List


@dataclass
class MockItem:
    name: str


class MockLibrary(Library[MockItem]):
    pass


def test_library_filtering():
    """Filters items using whitelist and blacklist access control."""
    lib = MockLibrary()
    items = [MockItem("a"), MockItem("b"), MockItem("c")]

    # Test Whitelist
    whitelist = ["a", "c"]
    result = lib.apply_access_control(items, whitelist=whitelist)
    assert len(result) == 2
    assert result[0].name == "a"
    assert result[1].name == "c"

    # Test Blacklist
    blacklist = ["b"]
    result = lib.apply_access_control(items, blacklist=blacklist)
    assert len(result) == 2
    assert result[0].name == "a"
    assert result[1].name == "c"

    # Test None
    result = lib.apply_access_control(items)
    assert len(result) == 3


def test_empty_lists():
    """Handles empty whitelist/blacklist inputs."""
    lib = MockLibrary()
    items = [MockItem("a")]

    # Empty whitelist -> Empty result? No, whitelist logic usually implies "only these".
    # If whitelist is [], result should be [].
    assert lib.apply_access_control(items, whitelist=[]) == []

    # Empty blacklist -> Full result.
    assert len(lib.apply_access_control(items, blacklist=[])) == 1
