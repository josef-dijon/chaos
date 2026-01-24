from pathlib import Path
from agent_of_chaos.domain.identity import Identity, Profile, Instructions
from agent_of_chaos.infra.memory import MemoryContainer
from agent_of_chaos.infra.skills import SkillsLibrary
from agent_of_chaos.infra.knowledge import KnowledgeLibrary
from agent_of_chaos.infra.tools import ToolLibrary, FileReadTool, FileWriteTool
from agent_of_chaos.engine.basic_agent import BasicAgent

DEFAULT_SUB_PATH = Path("src/agent_of_chaos/default_subconscious.json")


def _agent_id_from_identity_path(identity_path: Path) -> str:
    """Derives an agent id from an identity filename.

    Expected format: `<agent_id>.identity.json`.
    """

    filename = identity_path.name
    suffix = ".identity.json"
    if filename.endswith(suffix):
        return filename[: -len(suffix)]
    if filename.endswith(".json"):
        return filename[: -len(".json")]
    return identity_path.stem


class Agent:
    """
    The main Agent of CHAOS, orchestrating the Actor and Subconscious.
    """

    def __init__(self, identity_path: Path):
        self.identity_path = identity_path
        if identity_path.exists():
            self.identity = Identity.load(identity_path)
        else:
            agent_id = _agent_id_from_identity_path(identity_path)
            # Default template
            self.identity = Identity(
                profile=Profile(
                    name=agent_id or "Chaos",
                    role="Assistant",
                    core_values=["Helpful", "Harmless", "Honest"],
                ),
                instructions=Instructions(
                    system_prompts=["You are a helpful assistant."]
                ),
                tool_manifest=[],
            )
            self.identity.save(identity_path)

        self.memory = MemoryContainer()
        self.skills_lib = SkillsLibrary()
        self.knowledge_lib = KnowledgeLibrary()

        # Initialize ToolLibrary and register default tools
        self.tool_lib = ToolLibrary()
        self.tool_lib.register(FileReadTool())
        self.tool_lib.register(FileWriteTool())

        self.actor = BasicAgent(
            identity=self.identity,
            memory=self.memory,
            skills_lib=self.skills_lib,
            knowledge_lib=self.knowledge_lib,
            tool_lib=self.tool_lib,
        )

        # Subconscious setup
        # For MVP, we load from the default json relative to the package
        sub_path = Path(__file__).parent.parent / "default_subconscious.json"
        if sub_path.exists():
            self.sub_identity = Identity.load(sub_path)
        else:
            # Fallback if file missing
            self.sub_identity = Identity(
                profile=Profile(name="Subconscious", role="Analyst", core_values=[]),
                instructions=Instructions(),
                tool_manifest=[],
            )

        self.subconscious = BasicAgent(
            identity=self.sub_identity,
            memory=self.memory,
            skills_lib=self.skills_lib,
            knowledge_lib=self.knowledge_lib,
            tool_lib=self.tool_lib,
        )

    def do(self, task: str) -> str:
        """
        Executes a task using the Actor (BasicAgent).
        """
        self.memory.record(role="user", content=task)
        response = self.actor.execute(task)
        self.memory.record(role="assistant", content=response)
        return response

    def learn(self, feedback: str) -> str:
        """
        Triggers the learning cycle: Subconscious analyzes logs + feedback.
        """
        recent_logs = self.memory.get_stm_as_string()
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
        self.identity.patch_instructions(note)
        self.identity.save(self.identity_path)
        return note

    def dream(self) -> str:
        """
        Triggers the dreaming cycle (Maintenance).
        """
        # MVP Stub
        return "Dream cycle complete (Stub)."
