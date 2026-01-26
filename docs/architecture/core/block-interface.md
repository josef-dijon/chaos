# Block Interface

## Status
Draft

## Purpose
Define the `IBlock` interface contract used by all blocks.

## Scope
Block state transitions, interface methods, and request/response expectations. Detailed response semantics live in the responses document.

## Contents

### Interface Contract
Every node in the system, whether it is an atomic tool wrapper or a massive parallel workflow, must implement the `IBlock` interface. The interface is intentionally small to make orchestration explicit and testable.

### Block State
`BlockState` is a small state machine used to guard execution.

| State | Meaning | Entry Trigger | Exit Trigger |
| --- | --- | --- | --- |
| READY | Idle and callable | Construction or reset | `execute` begins |
| BUSY | Currently executing | `execute` begins | Success or failure response |
| WAITING | Failed and awaiting recovery | Failure response | Recovery or explicit re-execution |

### API Definition
The `IBlock` API surface is limited to four core members.

| Member | Type | Description |
| --- | --- | --- |
| `get_name()` | `() -> str` | Returns a stable identifier for this block instance. |
| `state` | `BlockState` | Current execution state; used to prevent re-entrancy. |
| `get_policy_stack(error_type)` | `(type[Exception]) -> list[RecoveryPolicy]` | Returns ordered recovery strategies for a given error type. |
| `execute(request)` | `(Request) -> IResponse` | Runs the block with a standardized request and returns a polymorphic response. |

### Request Contract (Summary)
Blocks receive a standardized `Request` that contains payload, context history, and configuration metadata. Managers are responsible for constructing and pruning the request.

| Field | Type | Description |
| --- | --- | --- |
| `payload` | any | Block-specific input data. |
| `context` | dict | Pruned context and shared state relevant to the block. |
| `metadata` | dict | Execution metadata (trace ids, policy hints, timing). |

## References
- [Core Architecture Index](index.md)
- [Block Responses](block-responses.md)
- [Architecture Index](../index.md)
