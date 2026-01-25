# Phase 2: Skills & Knowledge Expansion Plan (with Identity Refactor)

## Goal
Refactor `Soul` to `Identity` and expand the BasicAgent architecture to include centralized `Skills` and `Knowledge` libraries, with access control managed by the `Identity`.

## 1. Refactor: Soul -> Identity
- **Goal:** Rename core classes to avoid religious undertones.
- **Changes:**
    - `src/chaos/domain/soul.py` -> `src/chaos/domain/identity.py`
    - Class `Soul` -> Class `Identity`
    - Class `Identity` (inner) -> Class `Profile`
    - Update references in `BasicAgent`, `Agent`, `main.py`, `tests`.
    - Update JSON serialization format (backward compatibility not required for MVP).

## 2. Domain Model Updates
- **Update `Identity` class:**
    - Add `skills_whitelist` (Optional[List[str]])
    - Add `skills_blacklist` (Optional[List[str]])
    - Add `knowledge_whitelist` (Optional[List[str]])
    - Add `knowledge_blacklist` (Optional[List[str]])
    - Add validation to ensure whitelist and blacklist are mutually exclusive.
- **Create `Skill` class:**
    - Attributes: `name`, `description`, `content` (prompt/instruction).
- **Create `KnowledgeItem` class:**
    - Attributes: `id`, `content`, `tags`, `metadata`.

## 3. Infrastructure
- **Implement `SkillsLibrary`:**
    - A registry pattern to load skills from a directory or definition file.
    - Methods: `get_skill(name)`, `list_skills()`, `filter_skills(whitelist, blacklist)`.
- **Implement `KnowledgeLibrary`:**
    - A wrapper around a distinct ChromaDB collection (`knowledge_base`).
    - Methods: `add_document(content, tags)`, `search(query, tags_whitelist, tags_blacklist)`.

## 4. Engine Updates (BasicAgent)
- **Update `BasicAgent`:**
    - Inject `SkillsLibrary` and `KnowledgeLibrary` in `__init__`.
    - Update `reason` node:
        - Retrieve relevant skills based on context + Identity permissions.
        - Retrieve relevant knowledge based on context + Identity permissions.
        - Inject selected skills/knowledge into the System Prompt.

## 5. Orchestration (Agent)
- **Update `Agent`:**
    - Initialize `SkillsLibrary` and `KnowledgeLibrary`.
    - Pass them to both `Actor` and `Subconscious`.
    - Note: Subconscious gets full access.

## 6. Subconscious Configuration
- **Objective:** Create a standard configuration for the Subconscious.
- **Action:** Create `src/chaos/default_subconscious.json` to define the Subconscious profile and instructions.

## 7. Verification
- **Unit Tests:**
    - Test `Identity` (formerly Soul) serialization and whitelist/blacklist logic.
    - Test `SkillsLibrary` filtering.
    - Test `KnowledgeLibrary` search with tag filtering.
- **Integration:**
    - Verify Actor cannot access blacklisted skills.
    - Verify Subconscious can access all skills.
