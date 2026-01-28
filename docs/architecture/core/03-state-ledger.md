# State Ledger Architecture

## Status
Draft

## Purpose
Describe the ledger model used by blocks to track context, provenance, and recovery checkpoints.

## Scope
Ledger data structures, provenance, checkpointing, rollback, and orchestration interaction.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### 1. Definition and Role

*   **Definition:** The `Ledger` is the definitive Source of Truth for a composite block execution. It is a **Transactional, Append-Only Data Store** that manages shared execution context.
*   **Role:**
    *   **Storage:** Holds the shared state (variables, history) for a block execution.
    *   **Provenance:** Tags every data modification with the Creator Block ID.
    *   **Time Travel:** Manages Checkpoints (Snapshots) to support Deep Diagnostic Rollbacks.
*   **Interface Usage:** Used by composite blocks to manage state.

#### 1.1 Ownership and Mutation Permissions
The ledger is owned by the composite run.

Requirements:
- A composite block MUST be the only direct mutator of the ledger.
- Leaf blocks MUST NOT write to the ledger directly.

Rationale:
- This keeps leaf blocks testable and deterministic.
- Provenance and rollback behavior stays centralized.

#### 1.2 Rollback Scope
Rollback applies only to ledger state.

Requirements:
- Rollback MUST NOT be treated as undoing external side effects.
- Any recovery strategy that uses rollback MUST follow the side-effect safety rules in:
  - [Block Tool and Side-Effect Safety](block-tool-safety.md)

### 2. Construction and Configuration

The Ledger is instantiated by a composite block at runtime.

#### Configuration Surface
| Field | Type | Description |
| --- | --- | --- |
| `initial_context` | dict | Optional seed state for a block execution. |

### 3. Data Structures

#### Provenance Wrapper
Every value in the Ledger is wrapped to track its origin.
| Field | Type | Description |
| --- | --- | --- |
| `value` | any | Stored value. |
| `source_block_id` | str | Block id that produced the value. |
| `timestamp` | float | Write time. |
| `metadata` | dict | Additional provenance details. |

#### The Transaction Log
The Ledger does not just store the current state; it stores a log of operations (APPEND, UPDATE, DELETE). This allows for auditability and reconstruction.

### 4. Key Mechanisms

#### 4.1 Provenance Tracking
When a child block returns a successful `Response` with `data=X`, the calling block updates the Ledger.
* Action: `ledger.set(key="weather", value=X, source="WeatherBlock")`
* Result: `context["weather"]` returns `X`, but `ledger.get_entry("weather")` returns the full `LedgerEntry`.

Recommended provenance metadata:
- `trace_id`, `run_id`, `span_id`
- `block_name`, `node_name`, `attempt`

See:
- [Block Observability](block-observability.md)

#### 4.2 Checkpointing (Snapshots)
To support recovery, the Ledger can freeze its state.
* `snapshot_id = ledger.create_checkpoint()`
* Mechanism: deep copy of current state (structural sharing optional).
* Lifecycle: snapshots persist until the block execution completes or is compacted.

#### 4.3 Rollback
* `ledger.rollback(snapshot_id)`
* Effect: state resets to checkpoint; later entries are discarded or marked orphaned.

### 5. Interaction with Orchestration

#### The "Snip and Patch" Flow
When a composite block decides to perform a **Deep Diagnostic** rollback:

1.  **Block:** Identifies the target step (e.g., `Step_B`).
2.  **Block:** Calls `ledger.rollback(checkpoint_id="PRE_STEP_B")`.
3.  **Block:** Modifies the state slightly (The Patch).
    *   `ledger.set(key="constraint", value="Output JSON Only", source="Recovery")`
4.  **Block:** Resumes execution of `Step_B`.

Side-effect warning:
- "Snip and patch" is safe only for ledger state. If side effects occurred after `PRE_STEP_B`, they are not undone.

#### Checkpoint Timing and Rollback Flow
- When: typically before executing a child block (or before any sensitive/expensive step).
- What: snapshot of current context/ledger.
- Snapshot naming: use deterministic ids tied to graph nodes/steps when possible (e.g., `pre_step_b`).
- Rolling window: keep a small rolling window for long-running executions.
- Retention: snapshots persist for the duration of the block execution.
- Purge: snapshots discarded after the block returns success (or when compacted).

When a deep diagnostic strategy requests a rollback to Step B:
1. Block pauses execution.
2. Block retrieves `Snapshot_Pre_Step_B`.
3. Block overwrites current context with snapshot.
4. Block applies the fix to Step B input.
5. Block resumes execution from Step B.

### 6. Example Usage
- Block seeds `initial_context` with user intent.
- Child updates ledger values with provenance.
- Composite block checkpoints before sensitive steps.
- Rollback restores prior state if recovery triggers.

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Tool and Side-Effect Safety](block-tool-safety.md)
- [Block Observability](block-observability.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [Architecture Index](../index.md)
