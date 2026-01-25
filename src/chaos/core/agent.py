import json
from pathlib import Path

from chaos.config import Config
from chaos.config_provider import ConfigProvider
from chaos.domain import Identity, agent_id_from_path
from chaos.domain.memory_event_kind import MemoryEventKind

from chaos.infra.memory import MemoryContainer
from chaos.infra.memory_container import VISIBILITY_EXTERNAL
from chaos.infra.skills import SkillsLibrary
from chaos.infra.knowledge import KnowledgeLibrary
from chaos.infra.tools import ToolLibrary, FileReadTool, FileWriteTool
from chaos.engine.basic_agent import BasicAgent


class Agent:
    """
    The main Chaos agent, orchestrating the Actor and Subconscious.
    """

    def __init__(self, identity_path: Path, config: Config | None = None):
        self.identity_path = identity_path
        self.config = config or ConfigProvider().load()
        if identity_path.exists():
            self.identity = Identity.load(identity_path)
        else:
            agent_id = agent_id_from_path(identity_path)
            self.identity = Identity.create_default(agent_id)
            self.identity.save(identity_path)

        self.memory = MemoryContainer(
            agent_id=self.identity.agent_id,
            identity=self.identity,
            config=self.config,
        )
        self.actor_memory = self.memory.actor_view()
        self.subconscious_memory = self.memory.subconscious_view()
        self.skills_lib = SkillsLibrary()
        self.knowledge_lib = KnowledgeLibrary(self.config)

        # Initialize ToolLibrary and register default tools
        self.tool_lib = ToolLibrary()
        self.tool_lib.register(FileReadTool(root=self.config.get_tool_root()))
        self.tool_lib.register(FileWriteTool(root=self.config.get_tool_root()))

        self.actor = BasicAgent(
            identity=self.identity,
            config=self.config,
            memory=self.actor_memory,
            skills_lib=self.skills_lib,
            knowledge_lib=self.knowledge_lib,
            tool_lib=self.tool_lib,
            identity_path=self.identity_path,
            persona="actor",
        )

        # Subconscious setup uses the same identity source of truth.
        self.sub_identity = self.identity

        self.subconscious = BasicAgent(
            identity=self.sub_identity,
            config=self.config,
            memory=self.subconscious_memory,
            skills_lib=self.skills_lib,
            knowledge_lib=self.knowledge_lib,
            tool_lib=self.tool_lib,
            identity_path=self.identity_path,
            persona="subconscious",
        )

    def do(self, task: str) -> str:
        """
        Executes a task using the Actor (BasicAgent).
        """
        loop_id = self.memory.create_loop_id()
        self.memory.record_event(
            persona="actor",
            loop_id=loop_id,
            kind=MemoryEventKind.USER_INPUT,
            visibility=VISIBILITY_EXTERNAL,
            content=task,
        )
        response, tool_events = self.actor.execute_with_events(task)
        for event in tool_events:
            if event["kind"] == MemoryEventKind.TOOL_CALL:
                tool_args = event.get("args") or {}
                content = f"{event.get('name')} {json.dumps(tool_args, sort_keys=True)}"
                metadata = {
                    "tool_name": event.get("name"),
                    "tool_args": tool_args,
                    "tool_call_id": event.get("id"),
                }
                self.memory.record_event(
                    persona="actor",
                    loop_id=loop_id,
                    kind=MemoryEventKind.TOOL_CALL,
                    visibility=VISIBILITY_EXTERNAL,
                    content=content,
                    metadata=metadata,
                )
            if event["kind"] == MemoryEventKind.TOOL_OUTPUT:
                metadata = {
                    "tool_name": event.get("name"),
                    "tool_call_id": event.get("id"),
                }
                self.memory.record_event(
                    persona="actor",
                    loop_id=loop_id,
                    kind=MemoryEventKind.TOOL_OUTPUT,
                    visibility=VISIBILITY_EXTERNAL,
                    content=str(event.get("output")),
                    metadata=metadata,
                )
        self.memory.record_event(
            persona="actor",
            loop_id=loop_id,
            kind=MemoryEventKind.ACTOR_OUTPUT,
            visibility=VISIBILITY_EXTERNAL,
            content=response,
        )
        self.memory.finalize_loop(persona="actor", loop_id=loop_id)
        return response

    def learn(self, feedback: str) -> str:
        """
        Triggers the learning cycle: Subconscious analyzes logs + feedback.
        """
        loop_id = self.memory.create_loop_id()
        self.memory.record_event(
            persona="subconscious",
            loop_id=loop_id,
            kind=MemoryEventKind.FEEDBACK,
            visibility=VISIBILITY_EXTERNAL,
            content=feedback,
        )
        recent_logs = self.subconscious_memory.get_recent_stm_as_string(limit=1)
        prompt = f"""
        Analyze the recent interaction logs and the user's feedback: '{feedback}'.
        Logs:
        {recent_logs}
        
        Based on the feedback and logs, generate a specific, actionable instruction for the agent to follow in the future.
        Example feedback: "You are too verbose" -> Note: "Keep responses concise and under 2 sentences."
        
        Return ONLY the instruction text, no quotes or preamble.
        """
        note = self.subconscious.execute(prompt)

        # Patch and Save
        if self.identity.patch_instructions(note):
            self.identity.save(self.identity_path)
        self.memory.finalize_loop(persona="subconscious", loop_id=loop_id)
        return note

    def dream(self) -> str:
        """
        Triggers the dreaming cycle (Maintenance).
        """
        # MVP Stub
        return "Dream cycle complete (Stub)."

    def close(self) -> None:
        """
        Closes underlying resources for this agent.
        """
        self.memory.close()
