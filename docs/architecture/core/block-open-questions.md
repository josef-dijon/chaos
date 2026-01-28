# Block Architecture Open Questions

## Status
Draft

## Purpose
List unresolved design decisions that materially affect block runtime behavior. These questions must be resolved in architecture docs before they are treated as normative requirements.

## Scope
Execution semantics, recovery semantics, ledger integration, and observability.

## Contents

### 1. What Does `WAITING` Mean?
The core docs list `WAITING` as "failed and awaiting recovery" but do not define when it is entered, what is persisted, and how resumption works.

Questions:
- Is `WAITING` used for synchronous recovery only, or also for long-running async/tool waits?
- What is the canonical resume contract (same request, patched request, or resume token)?

### 2. Transition Evaluation Order and Determinism
Branching transitions are described, but ordering and tie-breaking were historically unspecified.

The architecture now specifies deterministic first-match evaluation for ordered branches (see [Block Execution Semantics](block-execution-semantics.md)).

Questions:
- How is branch ordering represented and validated (especially if graphs are configured via JSON)?
- What is the required behavior when no condition matches and there is no explicit default branch?

### 3. Looping and Safety Limits in Composite Graphs
The composite control loop allows repeated node execution, but loop rules are unspecified.

The architecture now requires a bounded execution limit (`max_steps`) to prevent infinite loops (see [Block Execution Semantics](block-execution-semantics.md)).

Questions:
- Are cycles allowed?
- How is loop detection handled (if at all)?

### 4. Canonical Failure Classification
The docs state policy selection depends on `error_type`, but other docs list string "error reasons" (for example in the LLM primitive).

Questions:
- Is `error_type` required on every failed `Response`?
- If `error_type` is absent, what is the fallback classification rule?

### 5. Condition Implementation Strategy
Core docs say conditions are implemented in code and do not require a string registry.

The architecture now requires fail-fast validation if a condition identifier cannot be resolved during graph construction (see [Block Execution Semantics](block-execution-semantics.md)).

Questions:
- Are condition names part of the architecture contract (string-keyed), or is the condition mechanism purely structural (callables/hooks)?
- If condition identifiers are used, what is the canonical namespace and collision strategy?

### 6. Ledger Ownership and Mutation Permissions
Ledger permission boundaries are now defined.

The architecture specifies composite-owned mutation:
- A composite block is the only direct mutator of the ledger.
- Leaf blocks do not write to the ledger directly.

See:
- [State Ledger](03-state-ledger.md)

Questions:
- Do we need a restricted "child write" capability for advanced cases? If yes, what is the minimal safe API?
- If a restricted API exists, how is provenance enforced and validated?

### 7. Side-Effect Safety for Retry and Rollback
Side-effect safety rules are now defined at a high level.

See:
- [Block Tool and Side-Effect Safety](block-tool-safety.md)

Questions:
- What is the canonical mechanism for declaring side-effect class (static property vs metadata vs per-node config)?
- Do we support compensation flows, or must non-idempotent operations always bubble?

### 8. Observability Contract
The architecture now defines a minimal trace model and recommended events.

See:
- [Block Observability](block-observability.md)
- [Block Request and Metadata](block-request-metadata.md)

Questions:
- Which identifiers MUST always be present vs SHOULD (particularly for tests)?
- What is the policy for PII in `details` and metadata when emitting logs/telemetry?

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Architecture](block-interface.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Execution Semantics](block-execution-semantics.md)
- [Block Recovery Semantics](block-recovery-semantics.md)
- [Block Tool and Side-Effect Safety](block-tool-safety.md)
- [Block Observability](block-observability.md)
- [State Ledger](03-state-ledger.md)
- [Architecture Index](../index.md)
