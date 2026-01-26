# Architecture Alignment Plan

## Goal
Align the current implementation with the system architecture in `docs/architecture.md`, using the deviations captured in `docs/architecture-audit.md`.

## Principles
- Architecture is the source of truth; update code and tests to match the spec.
- Keep changes small and testable; prefer incremental migrations with compatibility shims only when required.
- Maintain one-class-per-file and add docstrings to every function/class touched.

## Plan by audit area

### 1) Configuration and storage layout
1. Define JSON configuration schema in a new `Config` class and its dedicated module.
2. Replace environment-driven `BaseSettings` with JSON-backed loading (from `.chaos/config.json` or an explicit path).
3. Add schema validation (Pydantic or explicit validation helpers) and accessor methods.
4. Update default storage paths to match architecture:
   - `.chaos/db/chroma` for vector stores.
   - `.chaos/db/raw.sqlite` for idetic events.
5. Update any CLI or tests that depend on the old `.chaos/memories` path.
6. Add tests for configuration validation, file location discovery, and default path behavior.

### 2) Identity model and persistence
1. Extend `Identity` schema with required fields:
   - `schema_version`
   - `loop_definition`
   - memory configuration
   - tuning policy
2. Add `agent_id` derivation from `.chaos/identities/<agent_id>.identity.json`.
3. Update identity load/save to enforce required fields and version compatibility checks.
4. Replace any default subconscious identity file with the standard identity path.
5. Ensure tool/skill/knowledge manifests are connected to identity-level access control.
6. Expand tests to validate required fields, version handling, and identity path behavior.

### 3) Memory system
1. Introduce idetic event log with canonical schema (event kinds, timestamps, loop_id, actor/subconscious source).
2. Implement raw event store at `.chaos/db/raw.sqlite`.
3. Split memory into layers:
   - Idetic append-only log.
   - LTM vector store (1:1 with idetic events).
   - STM window per loop with loop_id.
4. Add persona-specific memory views and access controls.
5. Update agent flows to record events, loop metadata, and tool calls in the idetic log.
6. Create tests for the layered memory system, loop_id behavior, and access restrictions.

### 4) Tools and tool library
1. Update `BaseTool` with `type`, `schema`, and `call(args)` per architecture.
2. Move tool classes to one-class-per-file modules.
3. Update ToolLibrary to register and expose tool schemas, types, and call signatures.
4. Refactor `BasicAgent` to rely on tool-provided schemas instead of hardcoded specs.
5. Align tool manifest handling with identity-level policies.
6. Update tests to validate schema exposure, tool call behavior, and access control.

### 5) Skills and knowledge
1. Separate knowledge storage path from memory (`.chaos/db/chroma` with distinct collections).
2. Expand identity-level access control for knowledge and skills (whitelist/blacklist and manifest rules).
3. Update knowledge ingestion/search to enforce access boundaries.
4. Add tests for access control enforcement and storage isolation.

### 6) Agent and execution flow
1. Add identity refresh behavior aligned to architecture (reload or refresh as defined by loop definition).
2. Ensure `do/learn/dream` flows capture loop_id and idetic events.
3. Separate actor vs subconscious memory usage based on memory access rules.
4. Update agent prompts or flow steps as required by loop definition.
5. Add/adjust tests to validate event logging and persona separation.

### 7) Test alignment
1. Update tests to validate the new config and storage paths.
2. Replace old memory assumptions with idetic/LTM/STM layering tests.
3. Fill in knowledge/skills coverage gaps.
4. Adjust functional tests to the new identity and memory mechanics.

## Dependencies and sequencing
1. Configuration and identity changes first (foundation for storage paths and access policies).
2. Memory system next (depends on config paths and identity details).
3. Tools/skills/knowledge updates (dependent on identity access rules).
4. Agent flow updates (depends on memory and tool/skill changes).
5. Tests updated alongside each step to preserve coverage.

## Deliverables
- Updated configuration system and storage paths.
- Expanded identity schema with required fields and validations.
- Layered memory implementation with idetic log, LTM, STM, and persona access control.
- Tool system aligned to type/schema/call architecture.
- Skills and knowledge libraries with proper access boundaries.
- Tests updated for new architecture expectations and coverage.
