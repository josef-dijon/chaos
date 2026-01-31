# LLM Primitive Architecture

## Status
Draft

## Purpose
Define the LLMPrimitive block contract, configuration, and recovery behavior.

## Scope
LLMPrimitive interface, inputs/outputs, recovery policies, and execution flow.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### 1. Definition and Role

*   **Definition:** The `LLMPrimitive` is a **Stateless Atomic Block** that wraps a raw Large Language Model interaction.
*   **Role:** The fundamental unit of "Intelligence" in the system. It handles prompt assembly, generation, and schema enforcement.
*   **Interface Compliance:** Implements `Block`.

### 2. Construction and Configuration

The primitive is configured at construction time via direct arguments. This configuration is immutable.

#### Configuration Surface
| Field | Type | Description |
| --- | --- | --- |
| `name` | str | Stable block identifier. |
| `system_prompt` | str | System instruction for schema-constrained output. |
| `output_data_model` | Type[BaseModel] | Required schema for validation. |
| `model` | str | Provider model id. |
| `temperature` | float | Generation temperature. |

Implementation note:
- Provider calls are routed through LiteLLM. When `model` is omitted, the default is sourced from `Config.model_name`.
- When supported by the provider, the output schema is passed as a response-format hint.

### 3. Inputs and Outputs

| Input | Type | Description |
| --- | --- | --- |
| `payload` | str | User message content. |
| `context` | dict | Not required; block is stateless. |

| Output | Type | Description |
| --- | --- | --- |
| `data` | dict | Parsed JSON that conforms to `output_data_model`. |

Failure modes:
- `schema_error`: Output could not be parsed into the schema.
- `rate_limit_error`: Provider returned 429.
- `api_key_error`: Provider returned 401/403.
- `context_length_error`: Prompt exceeded model limits.

Note: These are example `reason` labels. Recovery policy selection is based on `error_type` (see [Block Responses](block-responses.md)).

### 3.1 Estimation Contract
`LLMPrimitive` MUST implement `estimate_execution(request) -> BlockEstimate` as a side-effect-free estimator.

Rules:
- The estimator MUST return a `BlockEstimate` for all inputs.
- When no historical data exists, the estimator MUST return a prior-based estimate with low confidence.
- The estimator MAY consult a stats adapter (read-only) to derive token/cost/time distributions.

See:
- [Block Estimation](block-estimation.md)

### 4. Policy Definition (Recovery)

The `LLMPrimitive` uses PydanticAI to manage both:

- API error retries (transient provider failures)
- schema validation retries (structured output validation failures)

As a result, the caller (including composites) MUST NOT manage API retry or schema retry for LLMPrimitive failures via the block recovery policy system.

The recovery policy system still applies to LLMPrimitive for local non-LLM errors (for example: invalid payload), but LLM-facing failures should generally bubble once PydanticAI has exhausted its internal retry budget.

The architecture does not require the mapping to be "hardcoded" in the class body, but it does require that:
- recovery selection is driven by `error_type`
- the policy stack is ordered and deterministic
- unsafe-to-recover failures (for example: missing API key) bubble immediately

| Failure Category | Description | Default Strategy | Escalation Chain |
| --- | --- | --- | --- |
| `schema_error` | Output does not validate against schema | Internal PydanticAI schema retry | `BubblePolicy` |
| `rate_limit_error` | Provider 429 / transient rate limiting | Internal PydanticAI API retry | `BubblePolicy` |
| `api_key_error` | Auth failed | `BubblePolicy` | `BubblePolicy` |
| `context_length_error` | Prompt too long | `BubblePolicy` | `BubblePolicy` |

### 5. Execution Flow

| Stage | Responsibility | Output |
| --- | --- | --- |
| Prompt construction | Combine `system_prompt` with schema instructions and pass user payload as a separate role. | Provider request payload. |
| Generation | Invoke provider model. | Raw model output. |
| Validation | Parse output against `output_data_model`. | `Response` (success or failure). |

Implementation note:
- Provider usage and cost data may be recorded or queried via a LiteLLM stats adapter. This adapter is an internal detail used to translate proxy aggregates into unified block estimates and execution records.

### 6. Example Flow (Schema Error)
- Block attempt 1 enters PydanticAI execution.
- PydanticAI performs schema validation; initial output fails.
- PydanticAI performs its internal schema retry/repair and re-queries the provider.
- If PydanticAI succeeds within its budget, the block returns success.
- If PydanticAI exhausts its budget, the block returns a failed `Response` and callers bubble (no additional block-level schema retry).

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Architecture](block-interface.md)
- [Block Responses](block-responses.md)
- [Recovery Policy System](recovery-policy-system.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [Architecture Index](../index.md)
