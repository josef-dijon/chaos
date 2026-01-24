# Code Review Remediation Plan

## Purpose
Create a structured, end-to-end remediation plan that addresses all findings in `code-review.md` while keeping the implementation aligned with `docs/architecture.md` and `AGENTS.md` standards (docstrings, one-class-per-file, testing, coverage).

## Goals
- Align code with architecture requirements (memory model, identity path rules, persona separation).
- Improve separation of concerns and reduce SRP violations in the agent and memory layers.
- Eliminate duplicated configuration and path logic across modules.
- Harden tool safety and file access boundaries.
- Remove nondeterminism from tests and enforce coverage targets.
- Ensure every class/function has clear docstrings.

## Non-Goals
- Changing architecture definitions without updating `docs/architecture.md` first.
- Introducing new external dependencies unless a gap cannot be solved with existing tools.
- Implementing new features unrelated to quality improvements.

## Current State Summary (from code review)
- Agent pipeline responsibilities are concentrated in `BasicAgent` and `MemoryContainer`.
- Configuration and `.chaos` path construction are duplicated and partially hardcoded.
- Tool actions are not recorded as idetic memory events, reducing traceability.
- `RawMemoryStore` lifecycle management and STM transactionality are incomplete.
- File tools permit unrestricted filesystem access and non-atomic writes.
- Missing docstrings conflict with project standards.
- Functional tests rely on live LLMs, causing nondeterminism and cost.
- Coverage expectations are not enforced in tooling or CI.

## Constraints & Requirements
- Follow `docs/architecture.md` for memory semantics, identity paths, and persona boundaries.
- Use `uv` for running scripts/tests.
- Maintain >=95% test coverage with `pytest` + `pytest-cov`.
- Mock LLM calls in unit tests; use VCR for integration tests if needed.
- One-class-per-file rule except for documented/approved exceptions.

## Plan Overview
The plan is divided into phases that can be executed independently but should follow this order to minimize churn.

### Phase 0 Reference Notes (Architecture Extract)
- Identity files must live at `.chaos/identities/<agent_id>.identity.json` and the filesystem path is the source of truth for `agent_id`.
- CHAOS artifacts must live under `.chaos/` (no project-root writes).
- Vector collections must be `<agent_id>__actor__ltm` and `<agent_id>__subconscious__ltm`.
- Idetic events are append-only and must include `kind` and `visibility` with canonical values.
- LTM is a 1:1 mirror of idetic events, STM is a per-loop summary referencing LTM ids.
- Actor access is restricted to actor-only memories; Subconscious can access both.

### Phase 0: Alignment & Baseline
1. Confirm identity path and memory layout assumptions from `docs/architecture.md`.
2. Inventory all modules that construct `.chaos` paths and ensure a single source of truth.
3. Draft a migration strategy for identity and memory metadata if formats need to change.
4. Define acceptance criteria for each phase (see below).

### Phase 1: Configuration & Path Centralization
Objective: Remove duplicated path logic and eliminate import-time config loading.

Steps:
1. Introduce a `ConfigProvider` or factory function that returns `Config` instances.
2. Move `settings = Config.load()` out of module import side effects.
3. Add explicit path helpers (e.g., `Config.identity_path(agent_id)`), backed by the architecture spec.
4. Update CLI entrypoints to consume `Config` and use centralized helpers.
5. Update any modules with hardcoded `.chaos` paths to use the helpers.
6. Update `README.md` and `pyproject.toml` to agree on Python version.

Acceptance Criteria:
- No module reads config at import time.
- All filesystem paths are produced by a single helper and consistent with architecture.
- CLI behavior remains unchanged from user perspective.

## `.chaos` Path Inventory (Phase 0 Output)
This list will be used to centralize path handling in Phase 1.

Code:
- `src/agent_of_chaos/config.py` (DEFAULT_CHAOS_DIR, db path defaults, path validation)
- `src/agent_of_chaos/cli/main.py` (CHAOS_DIR constant and identity path help text)

Tests:
- `tests/functional/conftest.py` (chroma/raw db paths)
- `tests/functional/test_cli_workflow.py` (identity path assertion)
- `tests/functional/test_learning_circuit.py` (identity path read)
- `tests/test_config.py` (config path assertions)

Docs (reference only):
- `docs/architecture.md` (path requirements)
- `docs/planning/*` (plan/checklist references)

### Phase 2: Agent Pipeline Decomposition
Objective: Reduce responsibility load and improve testability of the agent execution loop.

Steps:
1. Extract `PromptBuilder` responsible for system prompts, instruction layering, and context injection.
2. Extract `ContextRetriever` responsible for memory + knowledge retrieval (persona aware).
3. Extract `ToolRunner` responsible for tool execution and error handling.
4. Define clear data contracts between the components (input/output objects or dataclasses).
5. Add unit tests for each component with deterministic inputs.

Acceptance Criteria:
- `BasicAgent` orchestrates components but does not implement their internals.
- Each component has its own unit tests and docstrings.
- Prompt content boundaries are explicit and ordered.

### Phase 3: Memory Model Fidelity
Objective: Ensure memory pipeline adheres to architecture, captures tool calls, and handles persistence safely.

Steps:
1. Add idetic events for tool calls and tool outputs (persona-scoped).
2. Formalize event types (e.g., `user_input`, `actor_output`, `tool_call`, `tool_output`, `feedback`).
3. Update STM summarization to avoid unbounded growth; consider truncation or LLM summary.
4. Add `RawMemoryStore` connection lifecycle management and ensure it is closed.
5. Wrap STM delete + insert in a transaction to avoid partial state.
6. Add retryable embed status for vector failures and surface errors to callers.

Acceptance Criteria:
- Tool calls are visible in STM/LTM for later retrieval.
- STM generation is bounded and consistent.
- Raw memory operations are atomic and safely closed.

### Phase 4: Tool Safety & IO Boundaries
Objective: Reduce risk of arbitrary filesystem access and unsafe writes.

Steps:
1. Define a workspace root policy (config-driven) for read/write tools.
2. Validate paths against the workspace root and disallow traversal escapes.
3. Enforce size limits for reads and writes.
4. Introduce atomic write behavior (write to temp + rename).
5. Add explicit error types or structured errors for tool failures.

Acceptance Criteria:
- Tools cannot access paths outside the allowed root.
- Writes are atomic and bounded by size.
- Tool errors are structured and testable.

### Phase 5: Domain Model Reorganization
Objective: Align with one-class-per-file rule and clean domain layering.

Steps:
1. Split domain models in `identity.py` into separate files by class.
2. Add explicit re-exports in `src/agent_of_chaos/domain/__init__.py`.
3. Ensure each model has a full docstring and explicit validation notes.
4. Update import paths across the codebase and tests.

Acceptance Criteria:
- Each class resides in its own module (except documented exceptions).
- No import cycles introduced.

### Phase 6: Documentation & Docstrings
Objective: Meet the "document every function and class" rule.

Steps:
1. Add docstrings to all missing classes/functions in infra, engine, CLI, and tools.
2. Update module docstrings to describe side effects (logging, settings, etc.).
3. Ensure docstrings include parameters and return values.

Acceptance Criteria:
- A docstring linter or review confirms complete coverage.

### Phase 7: Testing, Determinism, and Coverage
Objective: Remove nondeterministic tests and enforce coverage goals.

Steps:
1. Replace functional tests that hit the live OpenAI API with VCR fixtures.
2. Add LLM mocks to unit tests for any model invocation paths.
3. Add tests for new behaviors: tool-call memory, path validation, config injection.
4. Add coverage config (e.g., `pyproject.toml` or `pytest.ini`) to fail below 95%.
5. Ensure `uv run pytest --cov` is documented in `README.md`.

Acceptance Criteria:
- CI/test runs are deterministic without external API calls.
- Coverage is enforced at or above 95%.

## Risks & Mitigations
- Risk: Refactors break implicit interfaces. Mitigation: create characterization tests before refactor.
- Risk: Path restrictions break existing workflows. Mitigation: make root configurable and document it.
- Risk: Memory changes alter retrieval behavior. Mitigation: add regression tests for memory retrieval outputs.

## Deliverables
- Updated source code with refactors and safety improvements.
- Updated docs and configuration alignment.
- Updated tests and coverage enforcement.
- Completed checklist in `docs/planning/code-review-remediation-checklist.md`.

## Validation Steps
- `uv run pytest --cov` passes and meets the 95% threshold.
- CLI commands `init`, `do`, `learn`, and `dream` behave as expected.
- Tool access respects sandbox boundaries.
- Memory retrieval returns expected LTM/STM data for both personas.
