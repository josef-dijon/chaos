from agent_of_chaos.domain import (
    Identity,
    Profile,
    Instructions,
    agent_id_from_path,
    SCHEMA_VERSION,
)
from pathlib import Path


def test_identity_serialization(tmp_path: Path):
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions(operational_notes=["Note 1"])
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    path = tmp_path / "agent.identity.json"
    identity.save(path)

    loaded_identity = Identity.load(path)
    assert loaded_identity.profile.name == "Test"
    assert loaded_identity.instructions.operational_notes == ["Note 1"]
    assert loaded_identity.profile.core_values == ["Test"]
    assert loaded_identity.schema_version == SCHEMA_VERSION
    assert loaded_identity.loop_definition == "default"
    assert loaded_identity.agent_id == "agent"


def test_patch_instructions():
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions(operational_notes=["Note 1"])
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    identity.patch_instructions("Note 2")
    assert "Note 2" in identity.instructions.operational_notes


def test_identity_defaults_include_memory_config():
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions()
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    assert identity.memory.actor.ltm_collection == "default__actor__ltm"
    assert identity.memory.subconscious.ltm_collection == "default__subconscious__ltm"


def test_agent_id_from_path():
    assert agent_id_from_path(Path("alpha.identity.json")) == "alpha"
    assert agent_id_from_path(Path("beta.json")) == "beta"


def test_create_default_identity_sets_agent_id():
    identity = Identity.create_default("default")

    assert identity.agent_id == "default"
    assert identity.profile.name == "default"
    assert identity.memory.actor.ltm_collection == "default__actor__ltm"


def test_create_default_identity_uses_agent_prefix():
    identity = Identity.create_default("alpha")

    assert identity.memory.actor.ltm_collection == "alpha__actor__ltm"
    assert identity.memory.subconscious.ltm_collection == "alpha__subconscious__ltm"


def test_resolve_tool_whitelist_prefers_explicit_whitelist():
    identity = Identity.create_default("default")
    identity.tool_manifest = ["tool_a"]
    identity.tool_whitelist = ["tool_b"]

    assert identity.resolve_tool_whitelist() == ["tool_b"]


def test_resolve_tool_whitelist_falls_back_to_manifest():
    identity = Identity.create_default("default")
    identity.tool_manifest = ["tool_a"]
    identity.tool_whitelist = None

    assert identity.resolve_tool_whitelist() == ["tool_a"]


def test_resolve_tool_whitelist_allows_all_when_empty():
    identity = Identity.create_default("default")
    identity.tool_manifest = []
    identity.tool_whitelist = None

    assert identity.resolve_tool_whitelist() is None
