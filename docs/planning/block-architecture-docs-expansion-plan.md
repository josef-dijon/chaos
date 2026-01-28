# Block Architecture Docs Expansion Plan

## Status
Draft

## Purpose
Expand and harden the block architecture documentation so an independent implementer can build a compatible runtime (leaf + composite) with deterministic execution, recovery, and ledger behavior.

## Scope
In scope:
- Core block architecture docs in `docs/architecture/core/` (interface, responses, recovery policy system, state ledger, recursive block overview/scenarios, LLM primitive).
- Adding new core docs where needed to keep topics small and testable.
- Updating core indexes so every doc is discoverable and appears exactly once.

Out of scope (for this plan):
- Implementing code changes beyond small “doc-code alignment” fixes discovered during documentation work.
- Updating legacy agentic architecture docs unless required to remove contradictions.

## Contents

### Goals (What “Done” Looks Like)
- The `Block` contract is stated in normative language (MUST/SHOULD/MAY) with explicit invariants.
- `Request`/`Response` schemas are canonical (fields, types, required/optional, serialization rules, reserved metadata keys).
- Composite execution semantics are deterministic (transition evaluation order, terminal conditions, no-match behavior, loop limits).
- Recovery semantics are specified (policy interfaces, attempt budgeting, backoff rules, repair boundaries, bubble rules).
- Ledger semantics are concrete (ownership, mutation permissions, checkpoint/rollback contract, side-effect constraints).
- Observability and provenance are specified (trace/span model, correlation IDs, provenance fields).
- Each doc is small, focused, cross-linked, and indexed from `docs/architecture/core/index.md`.

### Work Phases

#### Phase 1: Audit + Terminology Lock
1. Inventory current statements across:
   - `docs/architecture/core/block-interface.md`
   - `docs/architecture/core/block-responses.md`
   - `docs/architecture/core/recovery-policy-system.md`
   - `docs/architecture/core/03-state-ledger.md`
   - `docs/architecture/core/recursive-block-overview.md`
   - `docs/architecture/core/recursive-block-scenarios.md`
   - `docs/architecture/core/02-llm-primitive.md`
2. Create a short glossary and shared vocabulary (block, node, composite, run, attempt, policy, ledger transaction, checkpoint).
3. Identify contradictions and unresolved design decisions; capture them explicitly as “Open Questions”.

Deliverable:
- New glossary doc (see “New Docs to Add”).

#### Phase 2: Canonical Data Model (Request/Response/Metadata)
1. Specify the canonical `Request` model:
   - required fields and their meaning
   - immutability expectations (what can mutate, where)
   - size/shape guidance for `payload`, `context`, `metadata`
2. Specify the canonical `Response` model(s):
   - unified `Response` fields
   - error classification rules (`error_type` vs `reason`)
   - serialization requirements (what must/must not serialize)
3. Define reserved `metadata` keys and propagation rules across nested blocks.

Deliverable:
- Updated `docs/architecture/core/block-responses.md`
- New “request + metadata” doc if needed

#### Phase 3: Execution Semantics (Leaf + Composite)
1. Define the block state machine (including `WAITING`):
   - state transitions
   - re-entrancy expectations
   - cancellation/timeout expectations (even if “not supported yet”)
2. Define composite execution as a deterministic algorithm:
   - node selection and ordering
   - transition evaluation order and tie-breaking
   - terminal node rules
   - no-match behavior
   - loop limits / max steps
3. Specify how child execution is wrapped:
   - provenance capture
   - per-node attempt counters

Deliverable:
- Updated `docs/architecture/core/block-interface.md`
- New execution-semantics doc if the interface doc becomes too large

#### Phase 4: Recovery Semantics
1. Define `RecoveryPolicy` as an interface with explicit inputs/outputs.
2. Specify attempt budgeting:
   - per-policy vs per-node vs per-block
   - how attempt counts propagate through nested composites
3. Specify standard policies precisely:
   - Retry (delay/backoff/jitter, max attempts)
   - Repair (what can be changed, how to validate repairs)
   - Debug (checkpoint contract + required artifacts)
   - Bubble (how to preserve failure provenance)
4. Define override rules:
   - whether a parent can wrap/extend a child policy stack

Deliverable:
- Updated `docs/architecture/core/recovery-policy-system.md`
- New recovery-semantics doc if needed

#### Phase 5: Ledger Semantics + Side-Effect Safety
1. Specify ledger ownership and mutation permissions:
   - which layer writes to the ledger
   - how provenance is represented
2. Define checkpoint/rollback semantics and limitations.
3. Specify rules for tool calls and side effects:
   - idempotency requirements for retries
   - “unsafe-to-retry” classifications
   - compensation or explicit non-support rules

Deliverable:
- Updated `docs/architecture/core/03-state-ledger.md`
- New “tool + side effect safety” doc

#### Phase 6: Observability + Testing Guidance
1. Specify minimal observability surface:
   - trace IDs/span IDs
   - event logging vocabulary
   - correlation between ledger entries and block runs
2. Add testing guidance that supports the 95% coverage mandate:
   - deterministic time for backoff
   - mocking tool calls and LLM calls
   - golden trace tests for composite runs

Deliverable:
- New testing/observability doc(s)

#### Phase 7: Index + Consistency Pass
1. Update `docs/architecture/core/index.md` to include all new/updated docs.
2. Ensure each doc links back to the core index and follows the documentation template.
3. Ensure no duplicate indexing across sections.

### New Docs to Add (Proposed)
- `docs/architecture/core/block-glossary.md`
- `docs/architecture/core/block-request-metadata.md`
- `docs/architecture/core/block-execution-semantics.md`
- `docs/architecture/core/block-recovery-semantics.md`
- `docs/architecture/core/block-ledger-integration.md` (optional; may stay within `03-state-ledger.md`)
- `docs/architecture/core/block-tool-safety.md`
- `docs/architecture/core/block-observability.md`
- `docs/architecture/core/block-testing-guidelines.md`

### Open Questions (To Resolve During Phase 1)
- Does `WAITING` represent “needs user input”, “needs tool result”, or both?
- Are composite transitions first-match or priority-ordered? How is ordering represented?
- Is `error_type` the canonical selector for recovery, and is it required?
- Who owns the ledger: root composite only, or can child blocks write via a restricted API?
- What are the retry rules for side-effectful tool calls (allowed only if idempotent)?

### Acceptance Criteria
- A new engineer can implement a compatible block runtime using only the docs.
- All core block docs are internally consistent, indexed, and use stable terminology.
- Examples pin down edge cases (no-match transition, unknown condition, loop limit, repair exhaustion).

## References
- [Core Architecture Index](../architecture/core/index.md)
- [Architecture Index](../architecture/index.md)
- [Documentation Standard](../documentation-standard.md)
