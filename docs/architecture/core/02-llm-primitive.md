# LLM Primitive Architecture

## Status
Draft

## Purpose
Define the LLMPrimitive block contract, configuration, and recovery behavior.

## Scope
LLMPrimitive interface, inputs/outputs, recovery policies, and execution flow.

## Contents

### 1. Definition and Role

*   **Definition:** The `LLMPrimitive` is a **Stateless Atomic Block** that wraps a raw Large Language Model interaction.
*   **Role:** The fundamental unit of "Intelligence" in the system. It handles prompt assembly, generation, and schema enforcement.
*   **Interface Compliance:** Implements `IBlock`.

### 2. Construction and Configuration

The primitive is configured at construction time via direct arguments. This configuration is immutable.

#### Configuration Surface
| Field | Type | Description |
| --- | --- | --- |
| `name` | str | Stable block identifier. |
| `system_prompt` | str | System instruction for schema-constrained output. |
| `output_schema` | Type[BaseModel] | Required schema for validation. |
| `model` | str | Provider model id. |
| `temperature` | float | Generation temperature. |

### 3. Inputs and Outputs

| Input | Type | Description |
| --- | --- | --- |
| `payload` | str | User message content. |
| `context` | dict | Not required; block is stateless. |

| Output | Type | Description |
| --- | --- | --- |
| `data` | dict | Parsed JSON that conforms to `output_schema`. |

Failure modes:
- `schema_error`: Output could not be parsed into the schema.
- `rate_limit_error`: Provider returned 429.
- `api_key_error`: Provider returned 401/403.
- `context_length_error`: Prompt exceeded model limits.

### 4. Policy Definition (Recovery)

The `RecoveryPolicy` for the LLMPrimitive is **hardcoded** within the class. It is not configurable per-instance because the failure modes of a raw LLM call (Schema violation, Rate limits) requires specific, universal handling strategies.

| Error Reason | Description | Intrinsic Strategy | Escalation Chain |
| --- | --- | --- | --- |
| `schema_error` | Output invalid JSON | `RETRY` (new request) | `RETRY_WITH_FEEDBACK -> RETRY_WITH_FEEDBACK -> BUBBLE` |
| `rate_limit_error` | Provider 429 | `WAIT_AND_RETRY` | `WAIT_AND_RETRY -> WAIT_AND_RETRY -> BUBBLE` |
| `api_key_error` | Auth failed | `BUBBLE` | `BUBBLE` |
| `context_length_error` | Prompt too long | `BUBBLE` | `BUBBLE` |

### 5. Execution Flow

| Stage | Responsibility | Output |
| --- | --- | --- |
| Prompt construction | Combine `system_prompt` with schema instructions and pass user payload as a separate role. | Provider request payload. |
| Generation | Invoke provider model. | Raw model output. |
| Validation | Parse output against `output_schema`. | `SuccessResponse` or `FailureResponse`. |

### 6. Example Flow (Schema Error)
- Attempt 1 fails validation with `schema_error`.
- Manager applies `RETRY_WITH_FEEDBACK` with validation hint.
- Attempt 2 succeeds and returns `SuccessResponse`.

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
