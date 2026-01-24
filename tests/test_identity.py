from agent_of_chaos.domain.identity import (
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
