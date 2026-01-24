"""Context retrieval for agent loops."""

from typing import List

from langchain_core.messages import BaseMessage, HumanMessage

from agent_of_chaos.domain import Identity
from agent_of_chaos.infra.knowledge import KnowledgeLibrary
from agent_of_chaos.infra.memory import MemoryView


class ContextRetriever:
    """
    Retrieves long-term memory and knowledge context.

    Args:
        identity: The identity used for access control.
        memory: Memory view used to retrieve LTM.
        knowledge: Knowledge library used to fetch references.
        persona: Persona string that affects knowledge access.
    """

    def __init__(
        self,
        identity: Identity,
        memory: MemoryView,
        knowledge: KnowledgeLibrary,
        persona: str,
    ) -> None:
        self.identity = identity
        self.memory = memory
        self.knowledge = knowledge
        self.persona = persona

    def retrieve(self, messages: List[BaseMessage]) -> str:
        """
        Retrieves relevant context from LTM and knowledge sources.

        Args:
            messages: The current conversation messages.

        Returns:
            A formatted context string.
        """
        if not messages:
            return ""

        last_human = next(
            (
                message
                for message in reversed(messages)
                if isinstance(message, HumanMessage)
            ),
            None,
        )
        if not last_human or not isinstance(last_human.content, str):
            return ""

        query = last_human.content
        context_parts = []

        ltm_context = self.memory.retrieve(query)
        if ltm_context:
            context_parts.append(f"LTM: {ltm_context}")

        knowledge_whitelist = self.identity.knowledge_whitelist
        knowledge_blacklist = self.identity.knowledge_blacklist
        if self.persona == "subconscious":
            knowledge_whitelist = None
            knowledge_blacklist = None

        knowledge_context = self.knowledge.search(
            query=query,
            whitelist=knowledge_whitelist,
            blacklist=knowledge_blacklist,
        )
        if knowledge_context:
            context_parts.append(f"Reference Knowledge: {knowledge_context}")

        return "\n\n".join(context_parts)
