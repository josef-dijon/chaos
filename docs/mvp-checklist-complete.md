# MVP Implementation Checklist

- [x] **Setup**
    - [x] Initialize `uv` project.
    - [x] Add dependencies (`langgraph`, `langchain-openai`, `chromadb`, `typer`, `rich`, `pydantic`, `pytest`).
    - [x] Create `src` directory structure.

- [x] **Core Domain**
    - [x] Implement `src/domain/soul.py` (Soul, Identity, Instructions).
    - [x] Implement `src/domain/tool.py` (Tool abstract base class).
    - [x] Implement `src/config.py`.

- [x] **Infrastructure**
    - [x] Implement `src/infra/memory.py` (MemoryContainer, LTM with Chroma, STM).
    - [x] Implement `src/infra/utils.py` (Logging, Helpers).

- [x] **Engine**
    - [x] Implement `src/engine/agent.py` (BasicAgent, LangGraph loop).
    - [x] Implement basic tools (Read/Write file).

- [x] **Orchestration**
    - [x] Implement `src/chaos/agent.py` (The main Agent class: Actor + Subconscious).
    - [x] Implement `learn()` logic.
    - [x] Implement `dream()` logic.

- [x] **CLI**
    - [x] Implement `src/cli/main.py`.
    - [x] Add `do`, `learn`, `dream` commands.

- [ ] **Verification**
    - [x] Run unit tests for Soul.
    - [ ] Run integration tests (Requires OPENAI_API_KEY).
