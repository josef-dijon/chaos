# LLM Primitive Layered Implementation Plan

## Status
Draft

## Purpose
Refactor `LLMPrimitive` into a layered LLM stack (LLMService + StableTransport + LiteLLM adapter + instructor/Pydantic enforcement) while preserving the Block interface and recovery semantics.

## Scope
In scope:
- Define internal LLM request/response DTOs to isolate provider concerns.
- Add `StableTransport` with tenacity-based retries for transient errors.
- Add `LLMService` that integrates instructor for schema enforcement.
- Introduce a model selector skeleton that defaults to the configured model.
- Route through LiteLLM proxy by default, with a testing override for direct OpenAI access.
- Ensure metadata includes a `manager_id` (block name + unique suffix).
- Update tests with full mocking and deterministic behavior.

Out of scope:
- Final retry policy tuning (error list, backoff values).
- Full stats-driven model selection and budgeting.
- Real Postgres-backed stats store.

## Architecture References (Source of Truth)
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/block-recovery-semantics.md`
- `docs/architecture/core/02-llm-primitive.md`
- `docs/architecture/core/block-estimation.md`

## Implementation Plan

### 1. Internal LLM Layer Contracts
- Create internal DTOs in `src/chaos/llm/`:
  - `LLMRequest` (prompt, schema, model, metadata, attempt, history).
  - `LLMResponse` (status, data, error_details, raw_output, usage).
- Define a minimal `ResponseStatus` enum for internal use.

### 2. StableTransport (tenacity)
- Implement `StableTransport` with tenacity retry wrappers.
- Make the retry list configurable; use a placeholder set of transient exceptions initially.
- Ensure StableTransport raises a single domain error on exhausted retries.
- Initial defaults (subject to tuning): retry RateLimit/Timeout/5xx-style errors with exponential jitter backoff (initial 1s, max 8s) and 3 attempts.

### 3. LLMService (instructor + Pydantic)
- Add `LLMService` that:
  - Accepts `LLMRequest` and returns `LLMResponse` (no exceptions on expected errors).
  - Uses instructor to enforce schema output.
  - Sends schema hints to LiteLLM if supported by model/provider.
- Centralize error mapping (validation errors -> semantic, transport errors -> mechanical).

### 4. Model Selector Skeleton
- Add `ModelSelector` class that:
  - Accepts identity + request + optional stats adapter.
  - Returns the configured default model for now.
  - Exposes a method signature that can later incorporate stats/budgeting.

### 5. LLMPrimitive Orchestration
- Refactor `LLMPrimitive.execute`:
  - Build `LLMRequest` with manager_id (block name + unique suffix).
  - Use `ModelSelector` to pick model.
  - Call `LLMService` and run the semantic “nudge” loop inside `execute`.
  - Map final `LLMResponse` to `Block Response` with existing error taxonomy.

### 6. Config Support for Proxy vs Direct
- Extend `Config` with optional LiteLLM proxy settings (url/key) and a test flag to bypass proxy.
- Default to proxy; allow direct OpenAI configuration for tests only.

### 7. Tests
- Unit tests for:
  - StableTransport retries (tenacity) with mocked exceptions.
  - LLMService schema enforcement (ValidationError -> semantic failure).
  - LLMPrimitive semantic repair loop (nudge) and error mapping.
  - ModelSelector default behavior.
- Ensure LiteLLM and instructor calls are mocked and deterministic.

## Acceptance Criteria
- `LLMPrimitive.execute` orchestrates the layered system with internal DTOs.
- StableTransport uses tenacity and is configurable.
- LLMService uses instructor + Pydantic with clear error mapping.
- ModelSelector exists and defaults to the configured model.
- Proxy is default, with an explicit testing override for direct access.
- Tests pass with coverage >= 95%.

## References
- [Planning Index](index.md)
- [Architecture Index](../architecture/index.md)
