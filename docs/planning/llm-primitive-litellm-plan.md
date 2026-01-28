# LLM Primitive LiteLLM Integration Plan

## Status
Draft

## Purpose
Implement a real LLM call in `LLMPrimitive` using LiteLLM while preserving the architecture contract and testability standards.

## Scope
In scope:
- Wire `LLMPrimitive` to use LiteLLM for completions.
- Use `Config` for provider configuration (model + API key).
- Update tests to mock LiteLLM calls and validate error mapping.
- Update docs to note LiteLLM as the provider abstraction.

Out of scope:
- Reworking agent runtime or tool execution.
- Adding new provider-specific config beyond existing OpenAI fields.

## Contents

### Architecture References (Source of Truth)
- `docs/architecture/core/02-llm-primitive.md`
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/block-recovery-semantics.md`

### Implementation Steps
1. Add LiteLLM dependency to `pyproject.toml`.
2. Update `LLMPrimitive`:
   - Accept/configure `Config` to source `model` and API key.
   - Build messages and call LiteLLM completion.
   - Parse output into schema, returning a unified `Response`.
   - Map provider errors to `SchemaError`, `RateLimitError`, `ApiKeyError`, `ContextLengthError`.
3. Update tests to patch LiteLLM and assert:
   - Successful schema validation.
   - Failure mapping for rate limit/auth/schema errors.
   - Recovery policy selection behavior remains unchanged.
4. Update `docs/architecture/core/02-llm-primitive.md` to note LiteLLM usage.

### Acceptance Criteria
- `LLMPrimitive` performs real LiteLLM calls when not mocked.
- Tests remain deterministic and do not perform network calls.
- Coverage remains >= 95%.

## References
- [Planning Index](index.md)
- [Core Architecture Index](../architecture/core/index.md)
- [Architecture Index](../architecture/index.md)
