# Block Responses

## Status
Draft

## Purpose
Define the polymorphic response system returned by `IBlock.execute`.

## Scope
Success and failure response semantics, payload expectations, and error metadata.

## Contents

### Response System (Polymorphic)
Blocks return a response object instead of raising control-flow exceptions. The manager decides handling logic based on the response type.

### Response Types

| Response | Meaning | Manager Behavior |
| --- | --- | --- |
| `SuccessResponse` | Work completed successfully. | Update ledger, proceed to next step or return to parent. |
| `FailureResponse` | Work failed or violated a constraint. | Look up recovery policies and apply escalation chain. |

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| `metadata` | dict | Provenance details such as creator id and execution time. |
| `payload` | dict | Response payload data. Contents vary by response type. |
| `error_type` | type[Exception] | Failure classification used to select recovery policies. Only present on failures. |

#### SuccessResponse Payload

| Field | Type | Description |
| --- | --- | --- |
| `data` | any | Result value produced by the block. |

#### FailureResponse Payload

| Field | Type | Description |
| --- | --- | --- |
| `reason` | str | Short error label or category. |
| `details` | dict | Structured diagnostic details for recovery. |

### Handling Guarantees
- A response always represents the final outcome of a block execution attempt.
- Managers treat failures as data and must not assume exceptions for control flow.
- Recovery policy selection depends on `error_type`, not `reason` text.

## References
- [Core Architecture Index](index.md)
- [Block Interface](block-interface.md)
- [Architecture Index](../index.md)
