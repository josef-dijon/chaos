# MVP Implementation Plan (Detailed)

## Goal
Implement the version 1.0.0 (MVP Specification) of CHAOS as a Python CLI application.

## 1. Project Setup
- **Objective:** Initialize a robust Python environment.
- **Details:**
    - Initialize with `uv init`.
    - Dependencies:
        - `langgraph`, `langchain-openai`: Core cognitive architecture.
        - `chromadb`: Local vector database for Long-Term Memory (LTM).
        - `typer`: CLI framework.
        - `pydantic`: Data validation and schema definition.
        - `python-dotenv`: Environment variable management.
        - `rich`: Terminal UI formatting.
        - `pytest`, `pytest-cov`: Testing and coverage.
    - Directory Structure: Standard `src/` layout.

## 2. Core Domain Models (The Soul)
- **Objective:** Define the serializable identity of the agent.
- **Class: `Soul`**
    - **Attributes:**
        - `identity` (Identity): Immutable core (Name, Role, Core Values).
        - `instructions` (Instructions): Mutable operational notes and system prompts.
        - `tool_manifest` (List[str]): Allowed tool names.
    - **Behavior:**
        - `save(path)`: Serialize entire state to a JSON file.
        - `load(path)`: Validate and load from JSON.
        - `patch_instructions(notes)`: Method for the Subconscious to update operational notes.

## 3. Infrastructure
- **Class: `MemoryContainer`**
    - **LTM (Long-Term Memory):**
        - Implementation: `ChromaDB` collection.
        - Schema: `id`, `role`, `content`, `thinking_tokens`, `importance_score`, `timestamp`.
        - Behavior: `retrieve(query)` uses semantic search weighted by importance.
    - **STM (Short-Term Memory):**
        - Implementation: In-memory list/buffer (Deque).
        - Behavior: Holds the immediate conversation context window.
- **Class: `Tool` (Abstract)**
    - **Details:** Base class for all tools.
    - **Implementations:**
        - `LocalReadTool`: Safe file reading within a sandbox.
        - `LocalWriteTool`: Safe file writing within a sandbox.

## 4. The Engine (BasicAgent)
- **Objective:** The functional LLM loop processing engine.
- **Class: `BasicAgent`**
    - **Attributes:**
        - `soul`: The assigned Soul instance.
        - `memory`: MemoryContainer instance.
        - `graph`: The compiled LangGraph workflow.
    - **LangGraph Workflow:**
        - **Nodes:**
            1.  `Retrieve`: Fetch relevant context from LTM based on input.
            2.  `Plan/Think`: Internal monologue generation.
            3.  `Act`: Execute tools if necessary.
            4.  `Response`: Generate final answer.
        - **Edges:** Cyclic dependency for tool use (Think -> Act -> Think).

## 5. Orchestration (The Agent)
- **Objective:** The high-level interface managing the dual-process architecture.
- **Class: `Agent`**
    - **Attributes:**
        - `actor` (BasicAgent): The "Doing" agent. High temperature, task-focused.
        - `subconscious` (BasicAgent): The "Thinking" agent. Low temperature, reflection-focused.
    - **Methods:**
        - `do(task)`:
            1.  Add task to Actor's STM.
            2.  Run Actor's loop.
            3.  Log interaction to LTM.
        - `learn(feedback)`:
            1.  Subconscious reads Actor's recent logs + feedback.
            2.  Subconscious proposes update to `Soul.instructions`.
            3.  Run "Shadow Simulation" (optional for MVP/Stub): Validate change.
            4.  Call `Soul.patch_instructions()`.
            5.  `Soul.save()`.
        - `dream()`:
            1.  Subconscious iterates over recent LTM entries.
            2.  Re-scores `importance` based on heuristics (e.g., repetition = low, user correction = high).
            3.  Updates ChromaDB records.

## 6. CLI Interface
- **Objective:** User interaction point.
- **Details:**
    - `main.py` using `Typer`.
    - **Commands:**
        - `init`: Create a new `soul.json` template.
        - `do <task>`: Load agent, execute task, print Actor (Green) output.
        - `learn <feedback>`: Trigger Subconscious, print Subconscious (Blue) reflection.
        - `dream`: Run maintenance cycle.

## 7. Verification Strategy
- **Unit Tests:**
    - Verify `Soul` JSON serialization/deserialization.
    - Verify `MemoryContainer` storage and retrieval logic.
- **Integration Tests:**
    - Run a full `do()` loop with mocked LLM.
    - Verify `learn()` updates the Soul file.
