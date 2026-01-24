from langgraph.graph import StateGraph, END
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Union, Literal
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from agent_of_chaos.domain.identity import Identity
from agent_of_chaos.domain.memory_event_kind import MemoryEventKind
from agent_of_chaos.infra.memory import MemoryView
from agent_of_chaos.infra.skills import SkillsLibrary
from agent_of_chaos.infra.knowledge import KnowledgeLibrary
from agent_of_chaos.infra.tools import ToolLibrary
from agent_of_chaos.config import Config
from agent_of_chaos.engine.agent_context import AgentContext
from agent_of_chaos.engine.context_retriever import ContextRetriever
from agent_of_chaos.engine.prompt_builder import PromptBuilder
from agent_of_chaos.engine.tool_runner import ToolRunner
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
        self.prompt_builder = PromptBuilder(self.identity)
        self.context_retriever = ContextRetriever(
            identity=self.identity,
            memory=self.memory,
            knowledge=self.knowledge_lib,
            persona=self.persona,
        )
        self.tool_runner = ToolRunner(self.tool_lib)
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
        self.prompt_builder = PromptBuilder(self.identity)
        self.context_retriever = ContextRetriever(
            identity=self.identity,
            memory=self.memory,
            knowledge=self.knowledge_lib,
            persona=self.persona,
        )
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
        context = self.context_retriever.retrieve(messages)
        return {"context": context}

    def reason(self, state: AgentState) -> Dict[str, Any]:
        """
        Generates a response based on context and identity.
        """
        # Skills Injection
        available_skills = self.skills_lib.list_skills(
            whitelist=self.identity.skills_whitelist,
            blacklist=self.identity.skills_blacklist,
        )

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

        messages = self.prompt_builder.build_messages(
            messages=state["messages"],
            context=state.get("context", ""),
            skills=available_skills,
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

        tool_results = self.tool_runner.run(last_message.tool_calls)
        return {"messages": tool_results}

    def _collect_tool_events(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """
        Collects tool call and output events from graph messages.

        Args:
            messages: The messages emitted by the agent loop.

        Returns:
            A list of structured tool event payloads.
        """
        events: List[Dict[str, Any]] = []
        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                for tool_call in message.tool_calls:
                    events.append(
                        {
                            "kind": MemoryEventKind.TOOL_CALL,
                            "id": tool_call.get("id"),
                            "name": tool_call.get("name"),
                            "args": tool_call.get("args"),
                        }
                    )
            if isinstance(message, ToolMessage):
                events.append(
                    {
                        "kind": MemoryEventKind.TOOL_OUTPUT,
                        "id": message.tool_call_id,
                        "name": message.name,
                        "output": message.content,
                    }
                )
        return events

    def execute_with_events(self, task: str) -> tuple[str, List[Dict[str, Any]]]:
        """
        Executes a task and returns output plus tool events.

        Args:
            task: The user task or prompt.

        Returns:
            The output text and a list of tool call/output events.
        """
        self.refresh()
        context = AgentContext(messages=[HumanMessage(content=task)])
        initial_state: AgentState = {
            "messages": context.messages,
            "context": context.context,
        }
        result = self.graph.invoke(initial_state)
        messages = result["messages"]
        tool_events = self._collect_tool_events(messages)
        last_message = messages[-1]
        return str(last_message.content), tool_events

    def execute(self, task: str) -> str:
        """
        Executes a task through the agentic loop.
        """
        output, _ = self.execute_with_events(task)
        return output
