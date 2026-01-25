"""Tests for prompt construction utilities."""

from langchain_core.messages import HumanMessage, SystemMessage

from chaos.domain import Identity
from chaos.domain.skill import Skill
from chaos.engine.prompt_builder import PromptBuilder


def test_build_system_prompt_includes_identity_and_notes() -> None:
    """Builds a system prompt with identity and operational notes."""
    identity = Identity.create_default(agent_id="tester")
    identity.instructions.operational_notes.append("Follow the runbook.")
    skills = [Skill(name="audit", description="", content="Check logs")]

    builder = PromptBuilder(identity)
    prompt = builder.build_system_prompt(skills)

    assert identity.profile.name is not None
    assert identity.profile.name in prompt
    assert identity.profile.role in prompt
    assert "Follow the runbook." in prompt
    assert "- audit: Check logs" in prompt


def test_build_messages_inserts_context() -> None:
    """Prepends the relevant context system message."""
    identity = Identity.create_default(agent_id="tester")
    skills = []
    builder = PromptBuilder(identity)

    messages = builder.build_messages(
        messages=[HumanMessage(content="Hello")],
        context="LTM: context",
        skills=skills,
    )

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], SystemMessage)
    assert "Relevant Context: LTM: context" in messages[1].content


def test_build_system_prompt_for_subconscious_is_masked() -> None:
    """Builds a subconscious prompt with masked identity and schema."""
    identity = Identity.create_default(agent_id="tester")
    identity.instructions.operational_notes.append("Prefer detailed summaries.")
    skills = [Skill(name="audit", description="", content="Check logs")]

    builder = PromptBuilder(identity, persona="subconscious")
    prompt = builder.build_system_prompt(skills)

    assert "Subconscious Tuning Context" in prompt
    assert "Masked Identity" in prompt
    assert "Masked Identity Schema" in prompt
    assert "Prefer detailed summaries." in prompt
    assert "schema_version" not in prompt
