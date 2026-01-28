# Block Architecture

## Status
Draft

## Purpose
Define what a `Block` is, what it is responsible for, and the standardized execution contract it exposes.

## Scope
Block state transitions, request/response expectations, graph execution behavior, and recovery policy execution at the block boundary.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### The Unified Block Model
The system uses a unified object model where **everything is a Block**.

- A `Block` is the only architectural unit.
- A block may be a leaf (atomic work) or composite (executes a graph of child blocks).
- There is no separate concept of "container" or "manager". A block that has children simply assumes orchestration responsibilities.

### Block State
`BlockState` is a small state machine used to guard execution.

| State | Meaning | Entry Trigger | Exit Trigger |
| --- | --- | --- | --- |
| READY | Idle and callable | Construction or reset | `execute` begins |
| BUSY | Currently executing | `execute` begins | Success or failure response |
| WAITING | Failed and awaiting recovery | Failure response | Recovery or explicit re-execution |

Note: The architecture currently treats `WAITING` as a placeholder for "execution cannot proceed without an explicit recovery/resume action". The full semantics (when it is entered, what is persisted, and how resumption works) are tracked in:
- [Block Architecture Open Questions](block-open-questions.md)

### API Definition
The `Block` API surface is intentionally small.

| Member | Type | Description |
| --- | --- | --- |
| `name` | `str` | Stable identifier for this block instance. |
| `state` | `BlockState` | Current execution state; used to prevent re-entrancy. |
| `get_policy_stack(error_type)` | `(type[Exception]) -> list[RecoveryPolicy]` | Returns ordered recovery strategies for a given error type. |
| `execute(request)` | `(Request) -> Response` | Runs the block with a standardized request and returns a unified response. |

### Request Contract (Summary)
Blocks receive a standardized `Request` that contains payload, context, and execution metadata. When one block calls another, the calling block is responsible for constructing and pruning the request.

Canonical request and metadata conventions are defined in:
- [Block Request and Metadata](block-request-metadata.md)

| Field | Type | Description |
| --- | --- | --- |
| `payload` | any | Block-specific input data. |
| `context` | dict | Pruned context and shared state relevant to the block. |
| `metadata` | dict | Execution metadata (trace ids, policy hints, timing). |

### Execution Semantics
`Block.execute` is the universal entry point.

Deterministic execution rules for composite graphs are defined in:
- [Block Execution Semantics](block-execution-semantics.md)

- A block must return a `Response` for every execution attempt.
- A block must not use exceptions for expected control flow. Exceptions may still occur, but they are treated as internal errors and converted into a failed `Response` at the block boundary.

### Graph Execution (Composite Blocks)
A block executes a graph when it is configured with child blocks.

#### Graph Components
- **Nodes**: a mapping of node names to child `Block` instances.
- **Entry Point**: the name of the first node.
- **Transitions**: the rules used to select the next node.

#### Transition Styles
- **Linear transition**: `"A" -> "B"`
- **Branching transition**: `"A" -> [ {condition: ... , target: "B"}, {condition: "default", target: "C"} ]`

Conditions are implemented in code (for example: predicates or overridden hooks). The architecture does not mandate how conditions are referenced (string registry vs direct callables), but it does require that condition resolution is deterministic and validated as part of graph construction.

Open question tracking:
- [Block Architecture Open Questions](block-open-questions.md)

#### Composite Control Loop
1. Ingest the parent `Request`.
2. Select the current node (starting at the entry point).
3. Construct a child `Request` (prune context; map prior outputs as needed).
4. Execute the child block.
5. On `response.success() == True`, apply transition logic and continue.
6. On `response.success() == False`, apply recovery policies.
7. If the graph reaches a terminal node, synthesize a final `Response` for the composite block.

### Recovery Policy Execution
Recovery is enforced by the calling block.

- When a child returns a failed `Response`, the caller consults `child.get_policy_stack(error_type)`.
- The caller attempts the ordered `RecoveryPolicy` strategies until success or exhaustion.
- If recovery is exhausted, the caller returns its own failed `Response` as the outcome of the composite execution.

Deterministic recovery semantics and attempt accounting are defined in:
- [Block Recovery Semantics](block-recovery-semantics.md)

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Execution Semantics](block-execution-semantics.md)
- [Block Responses](block-responses.md)
- [Recovery Policy System](recovery-policy-system.md)
- [Block Recovery Semantics](block-recovery-semantics.md)
- [Block Tool and Side-Effect Safety](block-tool-safety.md)
- [Block Observability](block-observability.md)
- [Block Testing Guidelines](block-testing-guidelines.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [Architecture Index](../index.md)
