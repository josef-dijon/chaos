# PydanticAI Migration Plan

## Status
Draft

## Purpose
Replace both `instructor` and `tenacity` with PydanticAI, and move responsibility for (1) API error retry and (2) data schema retry/repair entirely into PydanticAI.

This plan also folds in the deferred audit items that become redundant or materially easier once PydanticAI owns retries and schema validation.

## Scope
- Dependencies:
  - Add PydanticAI.
  - Remove `instructor`.
  - Remove `tenacity`.
- Architecture/spec updates (must land before implementation):
  - `docs/architecture/core/02-llm-primitive.md`
  - `docs/architecture/core/recovery-policy-system.md`
  - `docs/architecture/core/block-recovery-semantics.md`
  - `docs/architecture/core/block-observability.md`
  - `docs/architecture/core/block-estimation.md` (if stats/usage contracts change)
- Code:
  - `src/chaos/domain/llm_primitive.py` (primary integration)
  - Supporting LLM transport/service modules as needed
  - Recovery/policy plumbing as needed to remove tenacity-driven behavior for LLM calls
- Tests:
  - Unit tests that mock PydanticAI to simulate API retries and schema retries.
  - Coverage >= 95%.

### Key Requirement
PydanticAI handles the entire API error retry and data schema retry mechanisms. The Block runtime must not manage either mechanism.

## Contents
### Plan
1. Architecture update (source of truth first):
   - Update `docs/architecture/core/02-llm-primitive.md` to specify:
     - The LLMPrimitive execution path uses PydanticAI for structured outputs.
     - API error retries happen inside PydanticAI (not Block recovery, not tenacity).
     - Schema validation retries/repairs happen inside PydanticAI.
     - How exhausted retries surface as stable failure categories.
   - Update `docs/architecture/core/recovery-policy-system.md` and `docs/architecture/core/block-recovery-semantics.md` to clarify:
     - Which failure categories Block recovery may handle (and explicitly exclude API/schema retry responsibilities).
     - Whether repair/debug policies apply to LLMPrimitive post-migration (likely narrowed or removed).
   - Update observability/stats specs to ensure attempt/span metadata remains coherent when retries happen inside PydanticAI.
2. Dependency migration:
   - Add PydanticAI dependency in `pyproject.toml`.
   - Remove `instructor` and `tenacity` dependencies.
   - Ensure imports and typing stubs are updated.
3. Implement PydanticAI-based LLMPrimitive execution:
   - Define the Pydantic response model(s) used for structured outputs.
   - Configure PydanticAI retry behavior for:
     - API/transient provider failures.
     - Schema validation failures.
   - Ensure model selection (if present) is respected and the actual selected model is recorded.
4. Remove block-managed retry/repair for LLM calls:
   - Ensure Block and policy stacks do not attempt to retry LLMPrimitive for API failures or schema validation failures.
   - Remove/disable any tenacity-based wrappers around LLM calls.
   - Eliminate duplicate/overlapping repair loops:
     - Remove the internal semantic repair loop in `LLMPrimitive`.
     - Remove/disable repair policies that are solely doing schema repair.
5. Deferred audit item remediation (post-PydanticAI integration, while behavior is still in flux):
   - Unify recovery implementation location and delete dead paths (e.g., `PolicyHandler.retry` if unused).
   - Reconcile retry semantics docs/tests to match the new reality:
     - Block attempts vs PydanticAI attempts must be clearly differentiated.
   - Fix stats/usage accounting:
     - Accurately count effective attempts.
     - Record the actual selected model.
     - Ensure composite-level stats reflect underlying PydanticAI attempt behavior.
6. Tests:
   - Add unit tests that mock PydanticAI to simulate:
     - API transient failure followed by success (internal retry).
     - Schema validation failure followed by success (internal schema retry).
     - Exhausted retries leading to stable failure.
   - Add assertions that Block does not add additional retries for these scenarios.
   - Keep/extend the pre-migration metadata propagation tests.
7. Verification:
   - Run `uv run pytest` and confirm coverage >= 95%.
   - Confirm `pyproject.toml` no longer includes `instructor` or `tenacity`.

### Outputs
- Updated architecture docs reflecting the new retry responsibilities.
- PydanticAI integration in `LLMPrimitive`.
- Removed instructor/tenacity usage.
- Updated stats/observability behavior and tests.

## References
- `docs/planning/index.md`
- `docs/dev/llm-primitive-block-audit.md`
- [PydanticAI Pre-Migration Stabilization Plan](pydanticai-pre-migration-plan.md)
