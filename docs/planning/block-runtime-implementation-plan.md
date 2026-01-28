# Block Runtime Implementation Plan

## Status
Draft

## Purpose
Implement the core block runtime (leaf + composite) to match the architecture specification, including deterministic execution, recovery, and metadata propagation.

## Scope
In scope:
- Implement/adjust `Block` runtime behavior to match core architecture docs.
- Align recovery execution with policy semantics.
- Add/adjust tests to keep coverage >= 95%.

Out of scope:
- Large refactors unrelated to blocks.
- New product features built on top of blocks.

## Contents

### Architecture References (Source of Truth)
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-request-metadata.md`
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/block-execution-semantics.md`
- `docs/architecture/core/recovery-policy-system.md`
- `docs/architecture/core/block-recovery-semantics.md`
- `docs/architecture/core/03-state-ledger.md`
- `docs/architecture/core/block-tool-safety.md`

### Implementation Targets

#### 1. Block API and State Machine
- Ensure `execute(request) -> Response` is the single entrypoint.
- Ensure state transitions (`READY -> BUSY -> READY`) are enforced for attempts.
- Define/implement `WAITING` behavior only if required by current runtime; otherwise keep it unused but documented.

#### 2. Composite Graph Determinism
- Enforce graph validation (entry point exists, targets exist, conditions resolvable).
- Enforce deterministic first-match branching semantics.
- Enforce `max_steps` safety bound with stable failure reason.

#### 3. Recovery Execution
- Implement a deterministic `execute_with_recovery` flow:
  - ordered policy application
  - attempt accounting in metadata
  - retry/repair/debug/bubble behavior
- Enforce side-effect safety constraints for retry/repair.

#### 4. Metadata Propagation
- Implement parent->child metadata propagation rules (trace/span/run/attempt/node_name).
- Ensure responses contain minimum required metadata for correlation.

#### 5. Ledger Ownership Boundary
- Ensure ledger writes (if present) are composite-owned.
- Ensure rollback is treated as ledger-only.

#### 6. Tests
- Add unit tests for:
  - transition selection
  - graph validation failures
  - max_steps exceeded
  - recovery attempt accounting
  - retry forbidden for non-idempotent side effects

### Files Likely to Change
- `src/chaos/domain/block.py`
- `src/chaos/engine/conditions.py`
- `src/chaos/engine/policy_handlers.py`
- `src/chaos/domain/messages.py` (metadata helpers if needed)
- `tests/**` (new/updated tests)

### Acceptance Criteria
- Composite execution is deterministic and bounded.
- Recovery execution is deterministic and policy-ordered.
- Unknown/unresolvable conditions fail fast.
- Metadata includes attempt counters and trace correlation.
- Test coverage remains >= 95%.

## References
- [Planning Index](index.md)
- [Core Architecture Index](../architecture/core/index.md)
- [Architecture Index](../architecture/index.md)
