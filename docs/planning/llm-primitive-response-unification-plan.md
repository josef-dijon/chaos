# LLM Primitive + Response Unification Plan

## Status
Draft

## Purpose
Refine `LLMPrimitive` configuration and runtime behavior by clarifying the Pydantic model parameter, passing schema hints to the LLM when possible, and unifying success/failure responses into a single `Response` type with a `success()` helper.

## Scope
In scope:
- Rename `output_schema` -> `output_data_model` across code/docs/tests.
- Pass the Pydantic schema to LiteLLM when supported.
- Replace `SuccessResponse`/`FailureResponse` with a single `Response` type.
- Update all call sites, tests, and docs for the new response contract.

Out of scope:
- Changing the recovery policy catalog or error taxonomy.
- Modifying the block graph execution model beyond response handling.

## Contents

### Architecture References (Source of Truth)
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-recovery-semantics.md`
- `docs/architecture/core/02-llm-primitive.md`

### Implementation Steps
1. Update architecture docs to define the unified `Response` type and `success()` semantics.
2. Update `Response` model in `src/chaos/domain/messages.py`:
   - Remove `SuccessResponse`/`FailureResponse` classes.
   - Add `success: bool`, `data`, `reason`, `details`, `error_type`, and `success()` method.
3. Update all code paths to use `Response`:
   - Block execution and recovery handling.
   - Policy handlers and registries.
   - Tests and helpers.
4. Update `LLMPrimitive`:
   - Rename parameter to `output_data_model`.
   - Provide schema hints to LiteLLM (best-effort).
5. Update test harness and tests for new API.

### Acceptance Criteria
- All core docs reflect the single `Response` model.
- All runtime code uses `Response.success()` instead of `isinstance` checks.
- `LLMPrimitive` passes schema hints when supported.
- Tests pass with coverage >= 95%.

## References
- [Planning Index](index.md)
- [Core Architecture Index](../architecture/core/index.md)
- [Architecture Index](../architecture/index.md)
