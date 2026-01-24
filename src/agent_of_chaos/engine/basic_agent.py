from langgraph.graph import StateGraph, END
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Union, Literal
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)
from langchain_openai import ChatOpenAI
from agent_of_chaos.domain.identity import Identity
from agent_of_chaos.infra.memory import MemoryView
from agent_of_chaos.infra.skills import SkillsLibrary
from agent_of_chaos.infra.knowledge import KnowledgeLibrary
from agent_of_chaos.infra.tools import ToolLibrary
from agent_of_chaos.config import Config
import json


class AgentState(TypedDict):
    messages: List[BaseMessage]
    context: str


class BasicAgent:
    """
    The processing engine that runs the LangGraph loop.
    """

    def __init__(
        self,
        identity: Identity,
        config: Config,
        memory: MemoryView,
        skills_lib: SkillsLibrary,
        knowledge_lib: KnowledgeLibrary,
        tool_lib: ToolLibrary,
        identity_path: Path,
        persona: str = "actor",
    ):
        self.identity = identity
        self.config = config
        self.memory = memory
        self.skills_lib = skills_lib
        self.knowledge_lib = knowledge_lib
        self.tool_lib = tool_lib
        self.identity_path = identity_path
        self.persona = persona
        self.loop_definition = identity.loop_definition

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.config.get_model_name(),
            api_key=self.config.get_openai_api_key(),  # type: ignore
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        if self.identity.loop_definition != "default":
            raise ValueError(
                f"Unsupported loop definition: {self.identity.loop_definition}"
            )
        return self._build_default_graph()

    def _build_default_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("recall", self.recall)
        builder.add_node("reason", self.reason)
        builder.add_node("act", self.act)

        builder.set_entry_point("recall")
        builder.add_edge("recall", "reason")

        # Conditional edge: Reason -> Act (if tool calls) or END
        builder.add_conditional_edges(
            "reason", self.should_continue, {"continue": "act", "end": END}
        )

        builder.add_edge("act", "reason")

        return builder.compile()

    def refresh(self) -> None:
        """
        Reloads the identity from disk to pick up patches.
        """
        self.identity = Identity.load(self.identity_path)
        if self.identity.loop_definition != self.loop_definition:
            self.loop_definition = self.identity.loop_definition
            self.graph = self._build_graph()

    def should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        messages = state["messages"]
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"
        return "end"

    def recall(self, state: AgentState) -> Dict[str, Any]:
        """
        Retrieves relevant context from LTM and Knowledge Library.
        """
        messages = state["messages"]
        if not messages:
            return {"context": ""}

        # Find the last user message for context retrieval
        # In a loop, the last message might be an AIMessage or ToolMessage
        # We generally want to recall based on the user's intent or the latest progress.
        # For simplicity MVP, we look for the last HumanMessage.
        last_human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )

        if not last_human or not isinstance(last_human.content, str):
            return {"context": ""}

        query = last_human.content
        context_parts = []

        # 1. LTM Retrieval
        ltm_context = self.memory.retrieve(query)
        if ltm_context:
            context_parts.append(f"LTM: {ltm_context}")

        # 2. Knowledge Retrieval
        knowledge_whitelist = self.identity.knowledge_whitelist
        knowledge_blacklist = self.identity.knowledge_blacklist
        if self.persona == "subconscious":
            knowledge_whitelist = None
            knowledge_blacklist = None

        knowledge = self.knowledge_lib.search(
            query=query,
            whitelist=knowledge_whitelist,
            blacklist=knowledge_blacklist,
        )
        if knowledge:
            context_parts.append(f"Reference Knowledge: {knowledge}")

        return {"context": "\n\n".join(context_parts)}

    def reason(self, state: AgentState) -> Dict[str, Any]:
        """
        Generates a response based on context and identity.
        """
        # Construct system prompt
        system_instructions = "\n".join(self.identity.instructions.system_prompts)
        operational_notes = "\n".join(self.identity.instructions.operational_notes)

        # Skills Injection
        available_skills = self.skills_lib.list_skills(
            whitelist=self.identity.skills_whitelist,
            blacklist=self.identity.skills_blacklist,
        )
        skills_text = "\n".join([f"- {s.name}: {s.content}" for s in available_skills])

        full_system_prompt = f"""
        Identity: {self.identity.profile.name} ({self.identity.profile.role})
        Values: {", ".join(self.identity.profile.core_values)}
        
        Available Skills:
        {skills_text}
        
        Core Instructions:
        {system_instructions}
        
        Operational Notes (MANDATORY BEHAVIORAL UPDATES):
        {operational_notes}
        
        Always prioritize Operational Notes over Core Instructions if there is a conflict.
        """

        # Bind Tools
        tool_whitelist = self.identity.resolve_tool_whitelist()
        available_tools = self.tool_lib.list_tools(
            whitelist=tool_whitelist,
            blacklist=self.identity.tool_blacklist,
        )

        formatted_tools = [tool.as_openai_tool() for tool in available_tools]

        llm_with_tools = self.llm
        if formatted_tools:
            llm_with_tools = self.llm.bind_tools(formatted_tools)

        messages: List[BaseMessage] = [
            SystemMessage(content=full_system_prompt)
        ] + state["messages"]

        if state.get("context"):
            messages.insert(
                1, SystemMessage(content=f"Relevant Context: {state['context']}")
            )

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def act(self, state: AgentState) -> Dict[str, Any]:
        """
        Executes tool calls requested by the LLM.
        """
        messages = state["messages"]
        last_message = messages[-1]

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        tool_results = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            # Fetch tool from library
            tool = self.tool_lib.get_tool(tool_name)
            if tool:
                # Execute
                try:
                    output = tool.call(tool_args)
                except Exception as exc:
                    output = f"Error executing {tool_name}: {exc}"
            else:
                output = f"Error: Tool {tool_name} not found or access denied."

            tool_results.append(
                ToolMessage(content=output, tool_call_id=tool_id, name=tool_name)
            )

        return {"messages": tool_results}

    def execute(self, task: str) -> str:
        """
        Executes a task through the agentic loop.
        """
        self.refresh()
        initial_state: AgentState = {
            "messages": [HumanMessage(content=task)],
            "context": "",
        }
        result = self.graph.invoke(initial_state)
        last_message = result["messages"][-1]
        return str(last_message.content)
