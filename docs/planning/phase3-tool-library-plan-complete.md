# Phase 3: Tool Library Implementation Plan (Revised)

## Goal
Implement a centralized `ToolLibrary` and abstract a base `Library` class to standardize access control across Tools, Skills, and future registries.

## 1. Domain Model Updates
- **Update `Identity`:**
    - Add `tool_whitelist` (Optional[List[str]]).
    - Add `tool_blacklist` (Optional[List[str]]).
    - Ensure mutually exclusive validation logic applies to tools as well.

## 2. Infrastructure Refactor (Base Library)
- **Create `src/chaos/infra/library.py`:**
    - **Class `Library(ABC)`:**
        - Generic base class for registry-based libraries.
        - Method `register(item)`: Abstract.
        - Method `get(name)`: Abstract.
        - Method `list()`: Abstract.
        - Method `apply_access_control(items, whitelist, blacklist)`: Concrete helper method implementing the standardized filtering logic.

## 3. Implement ToolLibrary & Refactor SkillsLibrary
- **Refactor `SkillsLibrary`:**
    - Inherit from `Library`.
    - Use `apply_access_control` for filtering.
- **Implement `ToolLibrary` (`src/chaos/infra/tools.py`):**
    - Inherit from `Library`.
    - Registry mapping `name` -> `Tool`.
    - Methods: `register`, `get`, `list`, `filter_tools`.

## 4. Engine Updates (BasicAgent)
- **Refactor `BasicAgent.__init__`:**
    - Inject `ToolLibrary`.
- **Update `BasicAgent` Logic:**
    - Retrieve allowed tools using `tool_lib.filter_tools(whitelist, blacklist)`.
    - Bind the filtered tools to the LLM.

## 5. Orchestration (Agent)
- **Update `Agent.__init__`:**
    - Initialize `ToolLibrary`.
    - Register default tools (`FileReadTool`, `FileWriteTool`).
    - Pass `ToolLibrary` to `Actor` and `Subconscious`.

## 6. Verification
- **Unit Tests:**
    - Test `Library` base class logic (filtering).
    - Test `ToolLibrary` registration and blacklist enforcement.
    - Verify `BasicAgent` respects tool restrictions.
