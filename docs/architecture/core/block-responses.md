# Block Responses

## Status
Draft

## Purpose
Define the unified response model returned by `Block.execute`.

## Scope
Unified response semantics, payload expectations, and error metadata.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Response System (Unified)
Blocks return a single `Response` object instead of raising control-flow exceptions. A caller decides how to proceed based on `response.success()`.

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| `metadata` | dict | Provenance details such as creator id and execution time. |
| `success` | bool | Indicates whether the attempt succeeded. |
| `data` | any | Result value produced by the block when successful. |
| `reason` | str | Short error label or category when failed. |
| `details` | dict | Structured diagnostic details for recovery when failed. |
| `error_type` | type[Exception] | Failure classification used to select recovery policies when failed. |

Notes:
- `reason` is intended for humans and diagnostics; it must not be used as the canonical selector for recovery.
- `error_type` is the canonical selector for recovery policy lookup.

#### Response Helpers

`Response.success()` returns `True` for successful attempts and `False` for failures.

### Handling Guarantees
- A response always represents the final outcome of a block execution attempt.
- Blocks treat failures as data and must not assume exceptions for control flow.
- Recovery policy selection depends on `error_type`, not `reason` text.

### Metadata and Serialization
Metadata conventions and reserved keys are defined in:
- [Block Request and Metadata](block-request-metadata.md)

Serialization guidance:
- If responses are serialized (for example: persisted in a ledger snapshot or transmitted), any fields used for recovery MUST be serializable.
- `error_type` may be runtime-only. If cross-process recovery is required, the failure MUST include a stable classifier in `reason` and any machine-required fields in `details`.

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Observability](block-observability.md)
- [Block Interface](block-interface.md)
- [Block Recovery Semantics](block-recovery-semantics.md)
- [State Ledger](03-state-ledger.md)
- [Architecture Index](../index.md)
