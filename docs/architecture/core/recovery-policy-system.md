# Recovery Policy System

## Status
Draft

## Purpose
Define recovery policy stacks and the escalation chain for failures.

## Scope
Policy stack configuration, standard recovery policies, and tiered escalation.

## Contents

### Policy Configuration
Blocks map error types to a stack of `RecoveryPolicy` objects. On failure, the manager retrieves the ordered stack and attempts each strategy in sequence.

| Input | Output | Responsibility |
| --- | --- | --- |
| `error_type` | `RecoveryPolicy[]` | Block provides an ordered recovery stack for the manager. |

### Standard Recovery Policies
| Policy | Behavior | Use Case |
| --- | --- | --- |
| RetryRecoveryPolicy | Re-executes with the same input. | Transient network errors, flaky 5xx responses. |
| RepairRequestRecoveryPolicy | Manager modifies request payload and retries. | Schema validation errors, input typos. |
| DebugRecoveryPolicy | Time-travel debugging with checkpoints. | Complex logic failures, stuck states. |
| BubbleRecoveryPolicy | Give up locally and return failure to parent. | Irrecoverable errors, exhausted strategies. |

### Escalation Chain (Tiered Recovery)
| Tier | Strategy | Trigger |
| --- | --- | --- |
| 1 | Retry | Transient failures or timeouts. |
| 2 | Input repair | Validation errors or malformed output. |
| 3 | Deep diagnostic | Repeated failure or inconsistent state. |
| 4 | Bubble | Unrecoverable or policy exhausted. |

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
