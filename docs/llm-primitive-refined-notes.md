# LLMPrimitive (Refined) Layering Notes

## Status
Temporary Draft

## Purpose
Extract LLM-specific layering, validation, budgeting, and observability concepts from `docs/llm-primitive-refined.md` into a focused scratch document for later integration into the architecture spec.

## Scope
- In scope: LLM execution stack layers, request/response contract concept, schema enforcement loop ("nudge"), transport shielding, model selection via stats, centralized auditing metadata.
- Out of scope: final names, concrete implementation, and any specific provider SDK details.

## Contents

### 1. LLM Execution Stack (LLM-Specific "Turducken")
The brainstorming document proposes the following strict ownership chain for LLM execution:

Manager (Strategy) -> LLMService (Abstraction) -> StableTransport (Shielding) -> LiteLLM Proxy (Transport)

Responsibilities:
- **Manager:** orchestration, multi-turn logic, semantic repair loop ("the nudge").
- **LLMService:** exception concealment, request/response mapping, schema validation integration.
- **StableTransport:** retries for transient provider/network errors with exponential backoff.
- **LiteLLM Proxy:** routing, key management, and centralized usage/cost auditing.

### 1.1. Class Hierarchy Sketch (Guide)
The brainstorming doc includes an OO sketch; the LLM-relevant hierarchy and wiring looks like:

```text
Config
  - source of truth for proxy URL + keys

Domain Objects
  UsageStats
    - avg_output_tokens, std_dev_output_tokens
    - safety_ceiling = mean + 2*sigma

  AIModel
    - proxy_name, tags
    - cost_per_1k_input/output

  LLMRequest
    - prompt, schema, model
    - manager_id, budget, tag
    - history, attempt
    - dry_run (optional)

  ResponseStatus (enum)
    - SUCCESS
    - SEMANTIC_ERROR
    - MECHANICAL_ERROR
    - CAPACITY_ERROR
    - CONFIG_ERROR
    - BUDGET_ERROR

  LLMResponse
    - status, data
    - error_message, error_details
    - raw_response, metadata
    - estimated_* / actual_* (time/cost)

Infrastructure
  StableTransport
    - call(...) with bounded retries + exponential backoff

  ModelStatsService (or StatsService)
    - queries proxy logs/metrics -> UsageStats

Intelligence / Orchestration
  ModelSelector
    - uses StatsService + catalog[AIModel]
    - selects best model within budget using safety ceiling

  LLMService
    - owns StableTransport
    - execute(LLMRequest) -> LLMResponse
    - swallows mechanical exceptions, maps to LLMResponse
    - integrates schema validation (e.g., instructor + pydantic)

  BaseManager (Manager)
    - owns stateful history + retry loop ("nudge")
    - selects model via ModelSelector
    - runs semantic repair loop based on LLMResponse.status
```

Notes:
- Names are illustrative; the key is that the Manager owns the semantic loop, while `StableTransport` owns transient retries.
- The service boundary is functional: `execute(LLMRequest) -> LLMResponse`.

### 2. Request/Response Contract (Conceptual)
The brainstorming document uses a unified request/response shape for LLM calls:

Request concept (examples of fields):
- `prompt`: user/task prompt
- `schema`: required output model (Pydantic)
- `model`: selected model/capability
- `manager_id`: stable caller identifier
- `budget`: maximum allowed spend
- `tag`: capability tier (for example, fast/cheap)
- `history`: prior conversation/messages (for semantic repair)
- `attempt`: attempt counter
- `dry_run`: optional estimation-only mode

Response concept (examples of fields):
- `status`: high-level outcome category
- `data`: parsed/validated output
- `error_message` / `error_details`: structured failure details (including schema validation errors)
- `raw_response`: raw provider output for debugging
- `metadata`: echoed/attached metadata for auditing
- `estimated_cost` / `actual_cost`, `estimated_time` / `actual_time`

Intent: the service boundary returns a response object instead of propagating provider exceptions.

### 3. Schema Enforcement and the Multi-Turn Repair Loop
The brainstorming document distinguishes:
- **Structural/schema failures:** treated as semantic errors that can be repaired by feedback.
- **Mechanical failures:** handled via transport retries; surfaced to the manager as a response when exhausted.

Repair loop concept (Manager layer):
- Attempt call.
- If `SEMANTIC_ERROR`, scrape validation errors and append them to the conversation as corrective feedback.
- Retry with updated prompt/history up to a fixed attempt limit.
- If repair fails repeatedly, abort with a semantic failure response.

### 4. Transport Shielding (StableTransport)
StableTransport is responsible for shielding the system from transient issues:
- retries (bounded)
- exponential backoff
- only for a narrow, explicit class of transient errors (timeouts, 429/5xx equivalents)

### 5. Centralized Auditing and Metadata
The brainstorming document emphasizes that every LLM call includes an explicit metadata block containing at least:
- `manager_id`
- `attempt`

The intent is granular auditing per attempt in the proxy/central store (cost, latency, model, outcome).

### 6. Stats-Driven Model Selection and Budgeting
The brainstorming document proposes selecting models using historical performance data:
- Stats are fetched via a stats service (conceptually, from proxy logs).
- Selection uses an estimated output-token ceiling (example: mean + 2*sigma) to budget conservatively.
- If no model fits the budget for the required tier/tag, return a budget failure (do not guess).

This implies two stats concerns:
- **Recording:** capturing per-call usage/cost/latency into a central store.
- **Reporting:** querying aggregates to support selection and reliability monitoring.

### 7. Configuration Boundary
Provider/proxy URLs and keys are configuration concerns and must not leak into manager logic. LLMService/transport reads these via a configuration wrapper.

## References
- `docs/llm-primitive-refined.md`
- `docs/architecture/core/02-llm-primitive.md`
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/recovery-policy-system.md`
- `docs/architecture/core/block-request-metadata.md`
- `docs/architecture/core/block-observability.md`
- `docs/architecture/index.md`
