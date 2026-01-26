# Agentic Operations and Lifecycle

## Status
Draft

## Purpose
Describe the learning and dreaming lifecycle operations for agentic behavior improvement.

## Scope
Learning circuit, dream cycle, and tuning policy controls.

## Contents

### The Learning Circuit
When `learn()` is called, the Agent enters a restricted state. The Subconscious receives access to all memory (Actor + Subconscious; idetic + derived layers) and the Architect's feedback.

Learning steps (conceptual):
1. Collect context: select recent Actor loops and Architect feedback.
2. Propose patch: generate a minimal patch to Identity (usually `instructions.operational_notes`).
3. Shadow simulation: test with a shadow actor using updated instructions.
4. Score improvement: evaluate against a rubric (completion correctness, instruction adherence, safety/tool constraints, latency/verbosity).
5. Apply patch: if score improves, patch Identity on disk.

Tuning levers:
- Subconscious proposes identity updates using dot-separated paths.
- Automatic application is controlled by `tuning_policy` allow/deny lists.
- Blacklist overrides whitelist entries, including parent-path scoping.
- Implicit blacklist for `schema_version`, `tuning_policy`, `memory.subconscious`, `memory.actor`, and `loop_definition`.
- Subconscious receives a masked identity and schema filtered by tuning policy, with per-field weights.

### The Dreaming Cycle
`dream()` is an asynchronous or idle-time process. The Subconscious performs maintenance over memory and retrieval indices.

Dream tasks (conceptual):
- Reconciliation: ensure derived layers mirror idetic coverage.
  - Create missing `ltm_entries` for idetic events without mirrors.
  - Create missing `stm_entries` for completed loops without summaries.
- Importance grading: adjust `ltm_entries.importance` based on heuristics.
- Embedding backfill: generate embeddings for `ltm_entries.embed_status='pending'`.
- Re-indexing: update vector metadata and ensure embedded LTM id set is correct.

## References
- [Agentic Architecture Index](index.md)
- [Architecture Index](../index.md)
