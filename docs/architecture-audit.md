# Architecture Alignment Audit (2026-01-24)

## Scope
- Source of truth: `docs/architecture.md`
- Codebase: `src/agent_of_chaos`, `tests`

## High-level gaps
- Configuration uses env-based `BaseSettings` instead of JSON-backed `Config` class with schema validation.
- Identity model and storage rules are incomplete (missing required fields, agent_id derivation, schema versioning).
- Memory system lacks idetic/LTM/STM layering, loop_id, raw DB, and persona-specific access control.
- Tools do not implement the required type/schema/call contract; tool schemas are hardcoded in the agent.
- Knowledge library uses the same storage path as memory and lacks identity-level access control boundaries.
- Tests codify current behavior (including storage paths) rather than the architecture rules.

## Detailed deviations

### Configuration and storage layout
- `src/agent_of_chaos/config.py`: loads config from environment with `BaseSettings`; architecture and dev guide require JSON config wrapped by a `Config` class with schema validation and accessor properties.
- `src/agent_of_chaos/config.py`: default `chroma_db_path` is `.chaos/memories` instead of `.chaos/db/chroma`.
- `src/agent_of_chaos/infra/memory.py`: no raw event store at `.chaos/db/raw.sqlite`.
- `tests/functional/conftest.py`: patches `.chaos/memories`, reinforcing the non-architectural path.

### Identity model and persistence
- `src/agent_of_chaos/domain/identity.py`: missing required fields (schema_version, loop_definition, memory config, tuning policy) and no agent_id derivation.
- `src/agent_of_chaos/core/agent.py`: uses a default subconscious identity at `src/agent_of_chaos/default_subconscious.json`, not `.chaos/identities/<agent_id>.identity.json`.
- `src/agent_of_chaos/engine/basic_agent.py`: tool_manifest not used; access control only by whitelist/blacklist.

### Memory system
- `src/agent_of_chaos/infra/memory.py`: single chroma collection with STM deque; no idetic event log, no per-loop STM, no loop_id, no event schema, no explicit LTM/STM layering.
- `src/agent_of_chaos/core/agent.py`: actor and subconscious share one MemoryContainer; no persona-specific memory access restrictions.

### Tools and tool library
- `src/agent_of_chaos/domain/tool.py`: BaseTool lacks required `type` and `schema` attributes and `call(args)` API.
- `src/agent_of_chaos/infra/tools.py`: tool classes and ToolLibrary in one file (violates one-class-per-file rule), and tools expose `run()` only.
- `src/agent_of_chaos/engine/basic_agent.py`: tool schemas are hardcoded instead of supplied by each tool; tool_manifest not integrated.

### Skills and knowledge
- `src/agent_of_chaos/infra/knowledge.py`: uses same chroma base path as memory and access control limited to domain whitelist/blacklist.
- `src/agent_of_chaos/infra/skills.py`: uses generic access control but no link to tool_manifest/identity-level skill policy.

### Agent and execution flow
- `src/agent_of_chaos/engine/basic_agent.py`: no memory event logging for idetic records or tool calls; missing identity refresh behavior.
- `src/agent_of_chaos/core/agent.py`: learn/dream flows do not update memory per architecture (no loop_id, no idetic events).

### Tests
- `tests/test_infra_memory.py`, `tests/functional/test_memory_persistence.py`: validate current memory layout and retrieval without idetic events or loop_id.
- `tests/functional/conftest.py`: config setup depends on `.chaos/memories`.
- `tests/test_skills_knowledge.py`: contains placeholder coverage for knowledge behavior.
