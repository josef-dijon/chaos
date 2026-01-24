from typing import Dict, List, Optional
from agent_of_chaos.domain.skill import Skill
from agent_of_chaos.infra.library import Library


class SkillsLibrary(Library[Skill]):
    """
    Central repository for agent skills.
    """

    def __init__(self):
        """
        Initializes the skills library with default entries.
        """
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
        """
        Registers a skill in the library.

        Args:
            skill: The skill instance to register.
        """
        self._registry[skill.name] = skill

    def get_skill(self, name: str) -> Optional[Skill]:
        """
        Retrieves a skill by name.

        Args:
            name: The skill name to look up.

        Returns:
            The matching skill or None.
        """
        return self._registry.get(name)

    def list_skills(
        self,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[Skill]:
        """
        Returns skills based on access control lists.

        Args:
            whitelist: Allowed skill names.
            blacklist: Forbidden skill names.

        Returns:
            The filtered list of skills.
        """
        skills = list(self._registry.values())
        return self.apply_access_control(skills, whitelist, blacklist)
