# Agentic Memory System

## Status
Draft

## Purpose
Define the memory model, event semantics, and access rules for the agentic subsystem.

## Scope
Memory layers, event taxonomy, loop semantics, search interfaces, derivation pipelines, and access enforcement.

## Contents

### Memory Model (Idetic / Long-Term / Short-Term)
CHAOS uses a 3-layer memory model per agent and per persona.

- Personas:
  - Actor: interactive persona; must never see or infer Subconscious memories.
  - Subconscious: maintenance persona; has access to all memory layers for both personas.
- Layers (per persona):
  - Idetic Memory (Perfect Log): append-only record of all events; retrieved literally by id or time range.
  - Long-Term Memory (LTM, Compacted Mirror): 1:1 compacted representation of idetic events; searchable via RAG.
  - Short-Term Memory (STM, Rolling Window): rolling window of the last N loop summaries; searchable via fuzzy text search.

### Canonical Event Types and Loop Semantics
All idetic events are tagged.

- Required idetic fields (conceptual):
  - `id`, `ts`, `agent_id`, `persona`, `loop_id`, `kind`, `visibility`, `content`, `metadata`
- Event kinds:
  - `user_input`, `actor_output`, `tool_call`, `tool_result`, `subconscious_prompt`, `subconscious_output`, `system_event`, `error`
- STM loop summary rules:
  - Exactly one STM entry per `loop_id`.
  - Each STM entry references the LTM ids created during that loop.

#### Prompt Loop Boundaries (`loop_id`)
- A `loop_id` is generated at the start of a single Architect invocation of `do(task)`.
- The loop includes: `user_input`, any number of `tool_call`/`tool_result` pairs, and final `actor_output`.
- Subconscious `learn()` and `dream()` operations must generate separate `loop_id` values under `persona=subconscious`.

### Search Interfaces (Conceptual)
- Idetic: `get_by_id(id)`, `get_range(start_ts, end_ts)`
- LTM (RAG): `rag_query(text, filters)`
- STM (fuzzy): `fuzzy_query(text, heuristics)` using Identity-configured heuristics.

#### Derivation Pipelines (Consistency Rules)
- Idetic write is primary and append-only.
- LTM derivation is 1:1 for each idetic event.
- STM derivation is per loop; one STM entry summarizes the loop and references LTM ids.

Failure handling:
- If LTM derivation or embedding fails, raw DB records a retryable status (e.g., `pending_embedding`).
- Idetic events must still be committed even when derived layers fail.
- Dream cycle backfills derived layers to match idetic coverage.

#### STM Fuzzy Search (Algorithm + Scoring)
- Engine: RapidFuzz (or equivalent) on normalized text.
- Base similarity: `token_set_ratio(query, summary)` in range 0-100.
- Heuristic score:
  - Recency weight uses `recency_half_life_seconds`.
  - Kind and visibility boosts come from Identity config.

Conceptual scoring:

```text
similarity = token_set_ratio(query, summary) / 100.0
recency = exp(-ln(2) * age_seconds / half_life_seconds)
boost = kind_boosts[kind] * visibility_boosts[visibility]
score = (w_similarity * similarity + w_recency * recency) * boost
```

### Access Rules (Non-Negotiable)
- Actor access: may query only `actor` idetic/LTM/STM for its own `agent_id`.
- Subconscious access: may query all layers for both personas for its `agent_id`.
- Prompt hygiene: Actor prompts must never include Subconscious events or derived memories.

### Isolation Enforcement (Mechanism + Tests)
Access rules must be enforced in code by construction.

- Persona-scoped wrappers (conceptual):
  - `ActorMemoryView(agent_id)`: only queries `persona=actor` and uses `<agent_id>__actor__ltm`.
  - `SubconsciousMemoryView(agent_id)`: may query both personas and collections.
- Unit tests must assert:
  - Actor retrieval never returns `persona=subconscious` rows.
  - Actor vector queries never hit `<agent_id>__subconscious__ltm`.
  - Actor prompt construction contains no Subconscious-only events.

## References
- [Agentic Architecture Index](index.md)
- [Memory Storage Layout](agentic-memory-storage-layout.md)
- [Architecture Index](../index.md)
