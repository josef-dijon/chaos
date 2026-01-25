from chaos.domain import (
    Identity,
    Profile,
    Instructions,
    agent_id_from_path,
    SCHEMA_VERSION,
)
from pathlib import Path


def test_identity_serialization(tmp_path: Path):
    """Serializes and loads an identity without losing data."""
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
    """Appends operational notes when policy allows updates."""
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions(operational_notes=["Note 1"])
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    updated = identity.patch_instructions("Note 2")
    assert updated is True
    assert "Note 2" in identity.instructions.operational_notes


def test_patch_instructions_blocked_by_policy():
    """Blocks operational notes updates when policy forbids them."""
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions(operational_notes=["Note 1"])
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    identity.tuning_policy.whitelist = []
    updated = identity.patch_instructions("Note 2")

    assert updated is False
    assert identity.instructions.operational_notes == ["Note 1"]


def test_identity_defaults_include_memory_config():
    """Ensures memory defaults are set on new identities."""
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions()
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    assert identity.memory.actor.ltm_collection == "default__actor__ltm"
    assert identity.memory.subconscious.ltm_collection == "default__subconscious__ltm"


def test_agent_id_from_path():
    """Derives agent ids from identity file names."""
    assert agent_id_from_path(Path("alpha.identity.json")) == "alpha"
    assert agent_id_from_path(Path("beta.json")) == "beta"


def test_create_default_identity_sets_agent_id():
    """Uses the agent id in default identity creation."""
    identity = Identity.create_default("default")

    assert identity.agent_id == "default"
    assert identity.profile.name == "default"
    assert identity.memory.actor.ltm_collection == "default__actor__ltm"


def test_create_default_identity_uses_agent_prefix():
    """Prefixes memory collection names with the agent id."""
    identity = Identity.create_default("alpha")

    assert identity.memory.actor.ltm_collection == "alpha__actor__ltm"
    assert identity.memory.subconscious.ltm_collection == "alpha__subconscious__ltm"


def test_resolve_tool_whitelist_prefers_explicit_whitelist():
    """Prefers an explicit whitelist over tool manifest."""
    identity = Identity.create_default("default")
    identity.tool_manifest = ["tool_a"]
    identity.tool_whitelist = ["tool_b"]

    assert identity.resolve_tool_whitelist() == ["tool_b"]


def test_resolve_tool_whitelist_falls_back_to_manifest():
    """Falls back to tool manifest when no whitelist is set."""
    identity = Identity.create_default("default")
    identity.tool_manifest = ["tool_a"]
    identity.tool_whitelist = None

    assert identity.resolve_tool_whitelist() == ["tool_a"]


def test_resolve_tool_whitelist_allows_all_when_empty():
    """Returns None when no tool restrictions are configured."""
    identity = Identity.create_default("default")
    identity.tool_manifest = []
    identity.tool_whitelist = None

    assert identity.resolve_tool_whitelist() is None


def test_get_tunable_schema_masks_blacklisted_fields() -> None:
    """Masks schema fields not allowed by tuning policy."""
    identity = Identity.create_default("tester")

    schema = identity.get_tunable_schema()

    assert "schema_version" not in schema.get("properties", {})
    instructions = schema["properties"]["instructions"]
    assert "operational_notes" in instructions["properties"]
    assert "system_prompts" not in instructions["properties"]


def test_get_tunable_schema_exposes_weights() -> None:
    """Includes field weights in the tunable schema."""
    identity = Identity.create_default("tester")

    schema = identity.get_tunable_schema()
    operational_notes = schema["properties"]["instructions"]["properties"][
        "operational_notes"
    ]

    assert operational_notes["weight"] == 2


def test_get_masked_identity_hides_blacklisted_fields() -> None:
    """Removes blacklisted identity fields from the masked payload."""
    identity = Identity.create_default("tester")

    masked = identity.get_masked_identity()

    assert "schema_version" not in masked
    assert "tuning_policy" not in masked
    assert "loop_definition" not in masked
