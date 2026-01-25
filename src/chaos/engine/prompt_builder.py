"""Prompt construction utilities for agent personas."""

import json

from typing import List

from langchain_core.messages import BaseMessage, SystemMessage

from chaos.domain import Identity
from chaos.domain.skill import Skill


class PromptBuilder:
    """
    Builds system prompts and message sequences for a given identity.

    Args:
        identity: The identity used to derive prompt content.
    """

    def __init__(self, identity: Identity, persona: str = "actor") -> None:
        self.identity = identity
        self.persona = persona

    def _build_subconscious_prompt(self, skills: List[Skill]) -> str:
        """
        Builds the system prompt for the subconscious persona.

        Args:
            skills: The list of available skills for the agent.

        Returns:
            A formatted system prompt string.
        """
        masked_identity = self.identity.get_masked_identity()
        masked_schema = self.identity.get_tunable_schema()
        skills_text = "\n".join(
            [f"- {skill.name}: {skill.content}" for skill in skills]
        )
        identity_text = json.dumps(masked_identity, indent=2, sort_keys=True)
        schema_text = json.dumps(masked_schema, indent=2, sort_keys=True)
        return (
            "\n"
            "Subconscious Tuning Context\n"
            "You MUST only use the masked identity and schema below.\n"
            "Any fields not present are forbidden and must be ignored.\n\n"
            "Available Skills:\n"
            f"{skills_text}\n\n"
            "Masked Identity (Source of Truth):\n"
            f"{identity_text}\n\n"
            "Masked Identity Schema (Tunable Parameters + Weights):\n"
            f"{schema_text}\n"
        )

    def build_system_prompt(self, skills: List[Skill]) -> str:
        """
        Builds the system prompt text from identity and skills.

        Args:
            skills: The list of available skills for the agent.

        Returns:
            A formatted system prompt string.
        """
        if self.persona == "subconscious":
            return self._build_subconscious_prompt(skills)

        system_instructions = "\n".join(self.identity.instructions.system_prompts)
        operational_notes = "\n".join(self.identity.instructions.operational_notes)
        skills_text = "\n".join(
            [f"- {skill.name}: {skill.content}" for skill in skills]
        )

        return (
            "\n"
            "Identity: "
            f"{self.identity.profile.name} ({self.identity.profile.role})\n"
            f"Values: {', '.join(self.identity.profile.core_values)}\n\n"
            "Available Skills:\n"
            f"{skills_text}\n\n"
            "Core Instructions:\n"
            f"{system_instructions}\n\n"
            "Operational Notes (MANDATORY BEHAVIORAL UPDATES):\n"
            f"{operational_notes}\n\n"
            "Always prioritize Operational Notes over Core Instructions if there is a conflict.\n"
        )

    def build_messages(
        self,
        messages: List[BaseMessage],
        context: str,
        skills: List[Skill],
    ) -> List[BaseMessage]:
        """
        Builds the message list including system prompts and optional context.

        Args:
            messages: Existing conversation messages.
            context: Retrieved context to prepend.
            skills: Available skills used for prompt construction.

        Returns:
            The ordered list of messages for LLM invocation.
        """
        full_system_prompt = self.build_system_prompt(skills)
        output_messages: List[BaseMessage] = [
            SystemMessage(content=full_system_prompt)
        ] + messages

        if context:
            output_messages.insert(
                1, SystemMessage(content=f"Relevant Context: {context}")
            )

        return output_messages
