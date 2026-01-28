# Block Tool and Side-Effect Safety

## Status
Draft

## Purpose
Define how retries, repairs, debugging, and rollback interact with tool calls and other side effects so recovery remains safe and deterministic.

## Scope
Side-effect classification, retry eligibility, rollback limitations, and required failure behavior when safety cannot be guaranteed.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Side Effects
A side effect is any operation that changes state outside the composite-run ledger, including:
- network calls
- filesystem writes
- database writes
- spawning subprocesses

### Side-Effect Classes
Each block attempt belongs to one of these classes:

| Class | Meaning | Retry Eligible | Rollback Eligible |
| --- | --- | --- | --- |
| `none` | No external side effects occur | yes | yes (ledger-only) |
| `idempotent` | External effects are safe to repeat (same input yields same external state) | yes | no (external) |
| `non_idempotent` | Repeating the attempt may cause additional effects | no | no |

Requirements:
- A recovery engine MUST treat unknown side-effect class as `non_idempotent`.

### Retry Safety Rules
Retries are only safe when repeating the attempt will not cause unintended external changes.

Requirements:
- `RetryPolicy` MUST NOT be applied to `non_idempotent` attempts.
- If a block attempt performs side effects and cannot guarantee idempotency, the block MUST return a failure that bubbles (for example: by selecting `BubblePolicy`).

Recommended behavior:
- For `idempotent` attempts, retry may proceed, but the implementation SHOULD include jittered backoff.

### Repair Safety Rules
Repair re-executes a block with a new request.

Requirements:
- Repair MUST obey the same side-effect rules as retry.
- If repair changes inputs in a way that would cause additional external side effects, the recovery engine MUST treat the repaired attempt as `non_idempotent` unless it can prove idempotency.

### Debug and Rollback Limitations
Rollback only applies to ledger state.

Requirements:
- A debug strategy that uses rollback MUST NOT assume external side effects are undone.
- If external side effects occurred after a checkpoint, rollback MUST be treated as a logical rollback only (ledger state), not a physical rollback (external systems).

### Declaring Side-Effect Class
The architecture requires that retry eligibility be knowable, but it does not mandate the representation mechanism.

Implementations MAY:
- declare side-effect class as a static property of a block
- declare side-effect class per node in a composite
- attach a side-effect class value to request/response metadata

If a system persists failures across process boundaries, the side-effect class SHOULD be representable as a stable string.

### Recommended Failure Reasons
When recovery is blocked due to side-effect safety, use stable `reason` labels.

Recommended `reason` values:
- `unsafe_to_retry`
- `non_idempotent_side_effect`
- `rollback_not_supported_for_side_effects`

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Responses](block-responses.md)
- [Block Recovery Semantics](block-recovery-semantics.md)
- [State Ledger](03-state-ledger.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [Architecture Index](../index.md)
