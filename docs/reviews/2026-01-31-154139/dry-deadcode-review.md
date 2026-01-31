# DRY Dead Code Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Low
  File: `src/chaos/domain/block.py`
  Issue: Duplicate `unsafe_to_retry` guard and response construction appears in both `RetryPolicy` and `RepairPolicy` branches.
  Impact: Recovery logic diverges over time; small changes must be made in two places and bugs will be introduced inconsistently.
  Recommendation: Extract a single helper for retry-safety validation + response, then call it from both branches.
  Architecture alignment: Yes

- Severity: Medium
  File: `src/chaos/llm/model_selector.py`
  Issue: `ModelSelector` is a redundant abstraction; it ignores `request` and always returns `default_model`.
  Impact: Callers carry an unnecessary indirection and tests can falsely imply model selection behavior that does not exist.
  Recommendation: Inline the selection in `LLMPrimitive` or implement real selection logic; otherwise remove the class and parameter.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/domain/llm_primitive.py`
  Issue: `get_policy_stack` overrides the base implementation but returns the same `[BubblePolicy()]` stack.
  Impact: Duplicate logic invites drift between base and subclass without adding behavior.
  Recommendation: Remove the override or extend it with LLM-specific policies; keep a single source of truth.
  Architecture alignment: Yes

- Severity: Medium
  File: `src/chaos/stats/estimate_builder.py`
  Issue: `request` is accepted and immediately discarded; estimation does not use request features at all.
  Impact: The API advertises request-aware estimation but produces the same output regardless of input, encouraging copy/paste usage that never varies.
  Recommendation: Either remove the `request` parameter from the public estimation APIs or use request metadata (size, model, etc.) to shape estimates.
  Architecture alignment: Unknown

- Severity: Low
  File: `tests/llm/test_model_selector.py`
  Issue: Test asserts a passthrough behavior that mirrors the current no-op implementation.
  Impact: The test suite can pass even if real selection logic is missing or accidentally removed; it also cements redundant code.
  Recommendation: Replace with tests that validate selection rules, or delete the test when `ModelSelector` is removed.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/domain/block.py`
  Issue: `get_policy_stack` accepts `error_type` but ignores it, always returning `[BubblePolicy()]`.
  Impact: Error-specific recovery logic is effectively dead; policies cannot vary by error class as the API contract implies.
  Recommendation: Either remove the parameter and simplify the API, or implement error-aware policy selection and add tests.
  Architecture alignment: Unknown

- Severity: Low
  File: `tests/domain/test_llm_primitive.py`
  Issue: Separate tests for schema, rate-limit, and auth policies all assert the same `[BubblePolicy()]` result.
  Impact: Copy/paste tests add maintenance overhead without covering new behavior.
  Recommendation: Parameterize these cases or consolidate into a single table-driven test.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/domain/llm_primitive.py`
  Issue: `manager_id` and `attempt` are stored both as top-level `LLMRequest` fields and duplicated inside `metadata`.
  Impact: Two sources of truth can drift and force callers to update both fields to stay consistent.
  Recommendation: Keep `manager_id`/`attempt` in a single location (prefer top-level fields) and strip duplicates from `metadata`.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/llm/litellm_stats_adapter.py`
  Issue: Adapter re-checks for `prior`/empty estimates even though stores like `JsonBlockStatsStore` already return a prior on empty data.
  Impact: Duplicated fallback logic makes it unclear which layer owns the responsibility and risks inconsistent behavior across stores.
  Recommendation: Define a single fallback policy (store or adapter) and remove the redundant check from the other layer.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/llm/response_status.py`
  Issue: `BUDGET_ERROR` is defined but never produced by the LLM layer or error mapper.
  Impact: Dead enum values add maintenance burden and imply support that the code does not implement.
  Recommendation: Implement the budget error path end-to-end or remove the status until it is used.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/domain/block.py`
  Issue: Metadata initialization logic is duplicated across `_with_base_metadata` and `_build_child_request` (trace/run/span IDs, block name, attempt).
  Impact: Changes to correlation metadata rules must be updated in multiple places, increasing the chance of drift.
  Recommendation: Extract a shared helper that composes metadata updates for both root and child requests.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/llm/llm_request.py`
  Issue: `metadata` is populated in `LLMPrimitive` but never consumed by the LLM service layer.
  Impact: Dead data paths add noise and create false confidence that audit metadata is preserved end-to-end.
  Recommendation: Either wire `LLMRequest.metadata` through to providers/logging or remove the field and its population.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/llm/llm_error_mapper.py`
  Issue: Multiple branches return identical `schema_error` mappings for different exception types.
  Impact: Duplication increases the chance that future edits update one branch but not the others.
  Recommendation: Centralize schema-error mapping in a small helper (e.g., `return _schema_error(details)`).
  Architecture alignment: Unknown
