# Block Glossary

## Status
Draft

## Purpose
Define the shared vocabulary used by the core block architecture documents.

## Scope
Terminology for blocks, graph execution, recovery, ledger/provenance, and observability.

## Contents

### Block
The fundamental architectural unit. A block exposes `execute(request) -> response` and may be either leaf (atomic) or composite (orchestrates child blocks).

### Leaf Block (Atomic Block)
A block that performs work directly and does not orchestrate a child graph as part of its execution.

### Composite Block
A block that executes a graph of child blocks (nodes) and synthesizes a final response from their results.

### Node
A named slot in a composite graph that points to a child block instance.

### Graph
The execution structure owned by a composite block, consisting of nodes, an entry point, and transitions.

### Entry Point
The node name that starts composite execution.

### Transition
The rule(s) used by a composite block to select the next node after a node succeeds.

### Condition
A predicate evaluated by a composite block when selecting among branching transitions.

### Request
The standardized input envelope passed to `Block.execute`.

### Payload
The block-specific input data carried by a request.

### Context
Pruned shared state carried by a request. The caller decides what context to provide to a child.

### Metadata
Execution metadata carried by a request/response (for example: tracing identifiers, attempt counters, policy hints).

### Response
The standardized output envelope returned by `Block.execute`.

### Response Success Flag
The boolean indicator used to distinguish a successful response (`success == True`) from a failed response (`success == False`).

### Error Type
The failure classification used to select a recovery policy stack. This is distinct from the human-readable `reason` string.

### Reason
A short string label describing a failure category (for example: "schema_error"). This is not the canonical selector for recovery.

### Details
Structured diagnostics included with a failure response, intended to power repair/debug strategies.

### Recovery Policy
A declarative strategy describing how a caller should attempt to recover from a child failure.

### Policy Stack
An ordered list of recovery policies returned by `get_policy_stack(error_type)`.

### Escalation Chain
The intended tiered progression of recovery strategies (for example: retry -> repair -> deep diagnostic -> bubble).

### Attempt
A single execution try of a block with a specific request (including retries and repairs).

### Run
The full execution lifecycle of a composite block, potentially containing many child attempts.

### Ledger
The composite-run source of truth that stores shared state, provenance, and checkpoint/rollback information.

### Provenance
Metadata attached to stored values describing origin (which block produced it, when, and under which conditions).

### Ledger Entry
A provenance-wrapped stored value in the ledger.

### Transaction Log
An append-only log of ledger operations (for example: APPEND, UPDATE, DELETE) used for auditability and reconstruction.

### Checkpoint (Snapshot)
A captured ledger state used to support rollback during deep diagnostic recovery.

### Rollback
Restoring ledger state to a prior checkpoint, discarding or orphaning later changes.

### Tool Call (Side Effect)
An operation that interacts with external systems (network, filesystem, subprocess). Tool calls influence retry/rollback safety.

## References
- [Core Architecture Index](index.md)
- [Block Architecture](block-interface.md)
- [Block Responses](block-responses.md)
- [Recovery Policy System](recovery-policy-system.md)
- [State Ledger](03-state-ledger.md)
- [Architecture Index](../index.md)
