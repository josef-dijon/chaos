"""Tests for the tuning policy access rules."""

from chaos.domain.tuning_policy import TuningPolicy


def test_whitelist_parent_scope_allows_children() -> None:
    """Allows child paths when a parent scope is whitelisted."""
    policy = TuningPolicy(whitelist=["profile"], blacklist=[])

    assert policy.is_allowed("profile.name", implicit_blacklist=[])


def test_blacklist_overrides_whitelist_for_child() -> None:
    """Blocks child paths when the child is explicitly blacklisted."""
    policy = TuningPolicy(whitelist=["profile"], blacklist=["profile.name"])

    assert not policy.is_allowed("profile.name", implicit_blacklist=[])


def test_blacklist_parent_overrides_whitelist_child() -> None:
    """Blocks child paths when the parent is blacklisted."""
    policy = TuningPolicy(whitelist=["profile.name"], blacklist=["profile"])

    assert not policy.is_allowed("profile.name", implicit_blacklist=[])


def test_implicit_blacklist_always_blocks() -> None:
    """Blocks implicit blacklist paths even when whitelisted."""
    policy = TuningPolicy(whitelist=["tuning_policy"], blacklist=[])

    assert not policy.is_allowed("tuning_policy", implicit_blacklist=["tuning_policy"])


def test_default_deny_when_not_whitelisted() -> None:
    """Denies access when no whitelist entry covers the path."""
    policy = TuningPolicy(whitelist=[], blacklist=[])

    assert not policy.is_allowed("profile.name", implicit_blacklist=[])
