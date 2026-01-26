# State Ledger Architecture

## Status
Draft

## Purpose
Describe the ledger model used by containers to track context, provenance, and recovery checkpoints.

## Scope
Ledger data structures, provenance, checkpointing, rollback, and manager interaction.

## Contents

### 1. Definition and Role

*   **Definition:** The `Ledger` is the definitive Source of Truth for a Container. It is a **Transactional, Append-Only Data Store** that manages the Context.
*   **Role:**
    *   **Storage:** Holds the shared state (variables, history) for a Container.
    *   **Provenance:** Tags every data modification with the Creator Block ID.
    *   **Time Travel:** Manages Checkpoints (Snapshots) to support Deep Diagnostic Rollbacks.
*   **Interface Compliance:** Used by `ContainerBlock` to manage state.

### 2. Construction and Configuration

The Ledger is instantiated by a `ContainerBlock` at runtime.

#### Configuration Surface
| Field | Type | Description |
| --- | --- | --- |
| `initial_context` | dict | Optional seed state for a container execution. |

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
When a Child Block returns `SuccessResponse(payload=X)`, the Container updates the Ledger.
* Action: `ledger.set(key="weather", value=X, source="WeatherBlock")`
* Result: `context["weather"]` returns `X`, but `ledger.get_entry("weather")` returns the full `LedgerEntry`.

#### 4.2 Checkpointing (Snapshots)
To support recovery, the Ledger can freeze its state.
* `snapshot_id = ledger.create_checkpoint()`
* Mechanism: deep copy of current state (structural sharing optional).
* Lifecycle: snapshots persist until container completes or is compacted.

#### 4.3 Rollback
* `ledger.rollback(snapshot_id)`
* Effect: state resets to checkpoint; later entries are discarded or marked orphaned.

### 5. Interaction with Manager

#### The "Snip and Patch" Flow
When a Manager decides to perform a **Deep Diagnostic** rollback:

1.  **Manager:** Identifies the target step (e.g., `Step_B`).
2.  **Manager:** Calls `ledger.rollback(checkpoint_id="PRE_STEP_B")`.
3.  **Manager:** Modifies the state slightly (The Patch).
    *   `ledger.set(key="constraint", value="Output JSON Only", source="Manager_Recovery")`
4.  **Manager:** Resumes execution of `Step_B`.

### 6. Example Usage
- Container seeds `initial_context` with user intent.
- Child updates ledger values with provenance.
- Manager checkpoints before sensitive steps.
- Rollback restores prior state if recovery triggers.

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
