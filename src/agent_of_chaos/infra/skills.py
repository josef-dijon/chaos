from typing import Dict, List, Optional
from agent_of_chaos.domain.skill import Skill
from agent_of_chaos.infra.library import Library


class SkillsLibrary(Library[Skill]):
    """
    Central repository for agent skills.
    """

    def __init__(self):
        self._registry: Dict[str, Skill] = {}
        # Pre-load some default skills (Stub)
        self.register(
            Skill(
                name="python_coding",
                description="Expertise in writing Python code.",
                content="Follow PEP 8 standards. Use type hints. Write docstrings.",
            )
        )
        self.register(
            Skill(
                name="creative_writing",
                description="Ability to write engaging narratives.",
                content="Use vivid imagery. Show, don't tell. Focus on emotional resonance.",
            )
        )

    def register(self, skill: Skill) -> None:
        self._registry[skill.name] = skill

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._registry.get(name)

    def list_skills(self) -> List[Skill]:
        return list(self._registry.values())

    def filter_skills(
        self,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[Skill]:
        """
        Returns skills based on access control lists.
        """
        return self.apply_access_control(self.list_skills(), whitelist, blacklist)
