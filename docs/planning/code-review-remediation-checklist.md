# Code Review Remediation Checklist

## Phase 0: Alignment & Baseline
- [x] Re-read `docs/architecture.md` and extract explicit path/memory requirements.
- [x] Identify every location that constructs `.chaos` paths (CLI, config, tests).
- [x] Capture a list of memory event types currently used (user_input, actor_output, etc.).
- [x] Decide whether new memory event types require a schema change and document it.
- [x] Define acceptance criteria for each refactor phase and share with stakeholders.

## Phase 1: Configuration & Path Centralization
- [x] Add a `ConfigProvider` (or factory) to construct `Config` without import-time side effects.
- [x] Remove `settings = Config.load()` from module import paths.
- [x] Add centralized helper for identity file path: `.chaos/identities/<agent_id>.identity.json`.
- [x] Add centralized helper for memory paths (chroma + raw db) using `Config`.
- [x] Update `src/agent_of_chaos/cli/main.py` to use centralized helpers.
- [x] Update all modules with hardcoded `.chaos` values to use `Config` helpers.
- [x] Update `README.md` Python requirement to match `pyproject.toml`.

## Phase 2: Agent Pipeline Decomposition
- [x] Create `PromptBuilder` class with explicit inputs (identity, system prompts, context).
- [x] Create `ContextRetriever` class that reads `MemoryView` + `KnowledgeLibrary`.
- [x] Create `ToolRunner` class that invokes tools and returns structured results.
- [x] Define dataclass for agent step inputs/outputs (e.g., `AgentContext`).
- [x] Update `BasicAgent` to orchestrate the components only.
- [ ] Add unit tests for each component (prompt ordering, context composition, tool run errors).
- [ ] Add docstrings for each new class and method.

## Phase 3: Memory Model Fidelity
- [ ] Add memory event types for `tool_call` and `tool_output` in `Agent.do()` flow.
- [ ] Add memory event type for `feedback` and record it during `learn()`.
- [ ] Update `MemoryContainer` to accept new event types and metadata.
- [ ] Add explicit schema or enum for memory event types (avoid ad-hoc strings).
- [ ] Implement bounded STM strategy (truncate or summarize at max tokens/lines).
- [ ] Add `RawMemoryStore.close()` and ensure it is called on shutdown.
- [ ] Wrap STM delete + insert inside an explicit transaction.
- [ ] Surface vector store upsert failures to callers or mark embed status for retry.
- [ ] Add tests covering STM summarization bounds and tool-call memory retention.

## Phase 4: Tool Safety & IO Boundaries
- [ ] Define config-driven allowed root for file tools (workspace or `.chaos`).
- [ ] Validate file paths against the allowed root and block traversal escapes.
- [ ] Add maximum size limits for read/write operations.
- [ ] Implement atomic writes (temp file + rename) for `FileWriteTool`.
- [ ] Use explicit error objects or error codes for tool failures.
- [ ] Add tests for path validation, size limits, and atomic write behavior.

## Phase 5: Domain Model Reorganization
- [ ] Split `Identity`-related Pydantic models into separate files.
- [ ] Add `src/agent_of_chaos/domain/__init__.py` exports for domain models.
- [ ] Update imports across code and tests to the new module layout.
- [ ] Ensure each class has a docstring with params and return values.

## Phase 6: Documentation & Docstrings
- [ ] Add module docstring to `infra/utils.py` explaining logging side effects.
- [ ] Add docstrings to `BasicAgent` and its public methods.
- [ ] Add docstrings to `RawMemoryStore` and persistence methods.
- [ ] Add docstrings to `KnowledgeLibrary`, `ToolLibrary`, `SkillsLibrary`.
- [ ] Add docstrings to file tools and their call methods.
- [ ] Validate docstrings for all new and modified classes/functions.

## Phase 7: Testing, Determinism, and Coverage
- [ ] Replace live OpenAI calls in functional tests with VCR fixtures.
- [ ] Add unit test mocks for all LLM invocations.
- [ ] Add tests for config injection and path helper behavior.
- [ ] Add tests for new memory event types and schema enforcement.
- [ ] Add coverage threshold configuration (>=95%).
- [ ] Update `README.md` with explicit test commands and coverage expectation.

## Validation
- [ ] Run `uv run pytest --cov` and confirm >=95% coverage.
- [ ] Run CLI `init`, `do`, `learn`, `dream` workflows locally.
- [ ] Verify LTM/STM retrieval includes tool calls and feedback.
- [ ] Confirm file tools cannot access paths outside the allowed root.
