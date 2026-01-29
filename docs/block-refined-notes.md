# Block (Refined) Layering Notes

## Status
Temporary Draft

## Purpose
Capture the layered structure, reliability patterns, and observability expectations described in `docs/llm-primitive-refined.md`, generalized to the `Block` abstraction. This document is a scratch source to help update the architecture docs later.

## Scope
- In scope: execution layering, functional response pattern, error taxonomy, centralized stats/auditing concepts, configuration boundaries.
- Out of scope: final names, concrete class definitions, provider-specific details, database schema, and implementation steps.

## Contents

### 1. Design Goals (Generalized)
- **Precision:** blocks return validated/typed data (when applicable), not best-effort strings.
- **Resilience:** transient failures are retried and/or escalated deterministically.
- **Observability:** costs, latency, attempts, and outcomes are recorded centrally.

### 2. Layered Execution Model (Reliability "Turducken")
The brainstorming document proposes a strict ownership chain that separates orchestration, mapping, retries, and transport.

Generalized chain (block-agnostic):

Orchestrator/Caller (Strategy) -> BlockService (Abstraction) -> StableTransport (Shielding) -> Provider/Adapter (Transport)

Responsibilities by layer:
- **Orchestrator/Caller:** multi-step logic, retries that involve changing input/state, escalation decisions.
- **BlockService:** request/response mapping, exception concealment, stable interface boundary.
- **StableTransport:** transient error shielding (timeouts, 5xx), exponential backoff.
- **Provider/Adapter:** actual execution (LLM, tool, HTTP API, etc.), key management/routing where applicable.

### 2.1. Conceptual Class Hierarchy (Guide)
The brainstorming document includes an OO sketch for the LLM path. The relevant parts generalized to `Block` are:

```text
Config
  - source of truth for infrastructure secrets/URLs

Block (interface)
  - execute(payload/context/metadata) -> BlockResponse
  - get_policy_stack(error_type) -> PolicyStack

BlockRequest
  - payload
  - context
  - metadata (caller_id/attempt/tags)
  - budget (optional)
  - attempt

BlockResponse
  - status (SUCCESS / *_ERROR)
  - data
  - error_message
  - error_details
  - raw_response (optional)
  - estimated_* / actual_* (time/cost)

ResponseStatus (enum)
  - SUCCESS
  - SEMANTIC_ERROR
  - MECHANICAL_ERROR
  - CAPACITY_ERROR
  - CONFIG_ERROR
  - BUDGET_ERROR

StableTransport
  - call(...) with bounded retries + exponential backoff

ProviderAdapter
  - provider-specific execution (LLM, HTTP API, tool runner)
  - no business logic; may attach metadata for auditing

BlockService
  - owns StableTransport + ProviderAdapter
  - execute(BlockRequest) -> BlockResponse
  - swallows mechanical exceptions, maps to BlockResponse

BlockOrchestrator (aka Manager/Runner)
  - owns multi-step logic
  - performs semantic repair loops (when applicable)
  - may escalate to alternate strategies based on status

BlockStatsService / StatsService
  - record per-attempt facts (latency/cost/outcome)
  - query aggregates to support selection/budgeting
```

Notes:
- Names are illustrative; the point is the *separation of responsibilities* and ownership chain.
- The `BlockService` boundary is intended to be exception-free for callers (returns `BlockResponse`).
- Stats separation is cross-cutting and should be usable by any `Block`, not just LLM-backed ones.

### 3. Functional Response Pattern
Prefer a functional style interface at the abstraction boundary:

execute(BlockRequest) -> BlockResponse

Key intent: callers should not need broad try/except for mechanical failures; the service returns a response object describing success/failure.

### 4. Error Taxonomy (Cross-Cutting)
The brainstorming document uses a small set of high-level failure categories that can be applied to blocks broadly:
- `SUCCESS`: request executed and output is valid.
- `SEMANTIC_ERROR`: output is structurally correct but fails validation (schema/type/constraints).
- `MECHANICAL_ERROR`: transport/provider execution failed after retries (timeouts, 5xx).
- `CAPACITY_ERROR`: request exceeded limits (context window, payload size).
- `CONFIG_ERROR`: configuration/auth failure (missing keys, permissions).
- `BUDGET_ERROR`: no feasible execution plan within budget/constraints.

Note: final naming should align with the canonical `error_type` vocabulary used by Block responses/recovery policies.

### 5. Recovery and Escalation Concepts
The brainstorming document implies two distinct retry classes:
- **Transport retries:** handled inside `StableTransport` with backoff for transient failures.
- **Logic retries:** handled by the orchestrator/caller when the response indicates a recoverable semantic failure (for example, repair/feedback).

The default posture is deterministic and ordered: a stable mapping from failure category to a policy stack (retry/repair/bubble) with immediate bubbling for unsafe failures (for example, auth/config).

### 6. Stats, Auditing, and Reporting (Cross-Cutting)
The brainstorming document introduces the idea that both blocks and LLM-specific primitives should have:
- **Recording:** per-attempt records of time/cost/outcome.
- **Reporting:** aggregate queries for latency, reliability, and cost.

Suggested separation (conceptual):
- `BlockStatsService`: block-level aggregated metrics (average block time/cost, reliability rate, counts).
- `StatsService`: a higher-level stats/query service used by selectors/orchestrators.

### 7. Configuration Boundary
Centralize provider URLs/keys/secrets in a configuration singleton/class and keep them out of block logic. Blocks/services consume configuration via accessors, not by reading environment variables directly.

### 8. Metadata Expectations
The brainstorming document emphasizes attaching metadata to each execution attempt for centralized auditing, including:
- stable block/manager identifier
- attempt number
- optional tags (tier, budget class)

Exact key names should align with existing reserved metadata keys in the block request/trace model.

## References
- `docs/llm-primitive-refined.md`
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/recovery-policy-system.md`
- `docs/architecture/core/block-observability.md`
- `docs/architecture/index.md`
