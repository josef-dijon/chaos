"""Prompt construction utilities for agent personas."""

from typing import List

from langchain_core.messages import BaseMessage, SystemMessage

from agent_of_chaos.domain import Identity
from agent_of_chaos.domain.skill import Skill


class PromptBuilder:
    """
    Builds system prompts and message sequences for a given identity.

    Args:
        identity: The identity used to derive prompt content.
    """

    def __init__(self, identity: Identity) -> None:
        self.identity = identity

    def build_system_prompt(self, skills: List[Skill]) -> str:
        """
        Builds the system prompt text from identity and skills.

        Args:
            skills: The list of available skills for the agent.

        Returns:
            A formatted system prompt string.
        """
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
