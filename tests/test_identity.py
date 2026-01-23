from agent_of_chaos.domain.identity import Identity, Profile, Instructions
from pathlib import Path


def test_identity_serialization(tmp_path: Path):
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions(operational_notes=["Note 1"])
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    path = tmp_path / "identity.json"
    identity.save(path)

    loaded_identity = Identity.load(path)
    assert loaded_identity.profile.name == "Test"
    assert loaded_identity.instructions.operational_notes == ["Note 1"]
    assert loaded_identity.profile.core_values == ["Test"]


def test_patch_instructions():
    profile = Profile(name="Test", role="Tester", core_values=["Test"])
    instructions = Instructions(operational_notes=["Note 1"])
    identity = Identity(profile=profile, instructions=instructions, tool_manifest=[])

    identity.patch_instructions("Note 2")
    assert "Note 2" in identity.instructions.operational_notes
