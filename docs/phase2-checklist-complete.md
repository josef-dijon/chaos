# Phase 2 Checklist

- [x] **Refactor: Soul -> Identity**
    - [x] Rename `src/agent_of_chaos/domain/soul.py` to `src/agent_of_chaos/domain/identity.py`.
    - [x] Rename Class `Soul` to `Identity` and `Identity` (inner) to `Profile`.
    - [x] Update all import references (`BasicAgent`, `Agent`, `main.py`).
    - [x] Rename `soul.json` references to `identity.json`.
    - [x] Rename `tests/test_soul.py` to `tests/test_identity.py` and update tests.

- [x] **Domain Models**
    - [x] Update `src/agent_of_chaos/domain/identity.py` (Add whitelists/blacklists).
    - [x] Create `src/agent_of_chaos/domain/skill.py`.
    - [x] Create `src/agent_of_chaos/domain/knowledge.py`.

- [x] **Infrastructure**
    - [x] Implement `src/agent_of_chaos/infra/skills.py` (SkillsLibrary).
    - [x] Implement `src/agent_of_chaos/infra/knowledge.py` (KnowledgeLibrary).

- [x] **Engine**
    - [x] Update `src/agent_of_chaos/engine/basic_agent.py` to use new libraries.
    - [x] Update System Prompt generation to include Skills/Knowledge.

- [x] **Core**
    - [x] Create `src/agent_of_chaos/default_subconscious.json`.
    - [x] Update `src/agent_of_chaos/core/agent.py` to initialize libraries and load default Subconscious config.

- [x] **Verification**
    - [x] Add tests for library filtering and access control.
