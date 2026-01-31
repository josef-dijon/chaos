# Recovery Policy System

## Status
Draft

## Purpose
Define recovery policy stacks and the escalation chain for failures.

## Scope
Policy stack configuration, standard recovery policies, and tiered escalation.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Policy Configuration
Blocks map error types to a stack of `RecoveryPolicy` objects.

- A block defines its recovery behavior by overriding `get_policy_stack(error_type)`.
- When a child block returns a failed `Response`, the calling block retrieves the ordered policy stack from the child and attempts each strategy in sequence.

Important:
- The recovery policy system is for block-level recovery managed by the caller.
- A block MAY implement internal retries/repairs as part of its own `execute` semantics.
- Callers MUST NOT layer additional retries/repairs for failure categories that a block explicitly manages internally.

Example:
- `LLMPrimitive` uses PydanticAI to manage both API retries and schema validation retries internally. Callers must not apply `RetryPolicy`/`RepairPolicy` for those LLM-facing failures.

Notes:
- Recovery selection is driven by `error_type` (see [Block Responses](block-responses.md)).
- Deterministic policy application and attempt accounting are defined in [Block Recovery Semantics](block-recovery-semantics.md).
- Remaining unresolved design decisions are tracked in [Block Architecture Open Questions](block-open-questions.md).

| Input | Output | Responsibility |
| --- | --- | --- |
| `error_type` | `RecoveryPolicy[]` | Block provides an ordered recovery stack for its caller. |

### Standard Recovery Policies
| Policy | Behavior | Use Case |
| --- | --- | --- |
| `RetryPolicy` | Re-executes with the same input. | Transient network errors, flaky 5xx responses. |
| `RepairPolicy` | Calling block modifies request payload and retries. | Schema validation errors, input typos. |
| `DebugPolicy` | Time-travel debugging with checkpoints. | Complex logic failures, stuck states. |
| `BubblePolicy` | Give up locally and return failure to parent. | Irrecoverable errors, exhausted strategies. |

### Escalation Chain (Tiered Recovery)
| Tier | Strategy | Trigger |
| --- | --- | --- |
| 1 | Retry | Transient failures or timeouts. |
| 2 | Input repair | Validation errors or malformed output. |
| 3 | Deep diagnostic | Repeated failure or inconsistent state. |
| 4 | Bubble | Unrecoverable or policy exhausted. |

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Responses](block-responses.md)
- [Block Recovery Semantics](block-recovery-semantics.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [Architecture Index](../index.md)
