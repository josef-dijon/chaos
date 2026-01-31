# Python Best Practices Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but production code (e.g., `LLMPrimitive._coerce_payload`) accepts a `str` payload and treats non-dict values as valid.
  Impact: Type checkers will flag valid call sites, and runtime usage diverges from the declared contract, making API usage unclear.
  Recommendation: Broaden `Request.payload` to `Any` or `str | dict[str, Any]`, and update docstrings to reflect acceptable payload shapes.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Multiple test functions and helper classes (e.g., `StubLLMService`, most `test_*` functions) lack docstrings despite the project standard requiring docstrings on every function and class.
  Impact: Test intent and coverage boundaries are harder to audit, and the codebase violates its own documentation standard.
  Recommendation: Add concise docstrings to each test function and helper class/method to state purpose and expectation.
  Architecture alignment: Not Available

- Severity: Low
  File: tests/llm/test_llm_service.py
  Issue: Helper function `_build_request`, `MockSchema`, and several `test_*` functions lack docstrings even though docstrings are mandated for all functions/classes.
  Impact: Reduces clarity of test behavior and undermines documentation consistency across the test suite.
  Recommendation: Add one-line docstrings to helper functions, test cases, and test-only classes to state intent.
  Architecture alignment: Not Available

- Severity: Medium
  File: src/chaos/llm/llm_service.py
  Issue: `_run_agent` passes `system_prompt or ()` to `Agent`, but `_run_agent` is annotated with `Optional[str]` and the docstring promises a `str | None`; the actual value can be an empty tuple.
  Impact: Type checkers will flag the call site, and the API contract is misleading for future maintainers.
  Recommendation: Pass `None` instead of `()` or widen the annotation and docstring to `str | Sequence[str] | None` to match the runtime behavior.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/stats/estimate_builder.py
  Issue: `build_estimate_from_records` accepts a `request` parameter but immediately deletes it and never uses it.
  Impact: The signature and docstring suggest per-request estimation logic that does not exist, confusing readers and future callers.
  Recommendation: Remove the unused parameter and update docstrings, or implement request-sensitive estimation and document it.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/llm/test_llm_service.py
  Issue: `FakeAgent.run_sync` treats `model_settings` as a dict (`model_settings["temperature"]`), but the real `ModelSettings` is not a mapping.
  Impact: The test may pass even when the production integration would break, reducing confidence in behavior and typing accuracy.
  Recommendation: Access `model_settings.temperature` or assert via the public API shape of `ModelSettings` to match real usage.
  Architecture alignment: Not Available

- Severity: Low
  File: src/chaos/domain/messages.py
  Issue: `Response.__init__` overrides BaseModel initialization but lacks a docstring, despite the project requirement to document every function.
  Impact: The side effect of injecting `metadata["id"]` is not documented for callers and future maintainers.
  Recommendation: Add a short docstring explaining the initialization side effect and metadata behavior.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `_execute_graph` returns `Response` objects with inconsistent `error_type` population (e.g., the `unknown_node` branch omits `error_type` while other failure branches set it).
  Impact: Recovery policy selection and error classification become unreliable and harder to type-check or reason about.
  Recommendation: Populate `error_type` consistently for all failure responses (use a concrete exception type).
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `_record_attempt` swallows all exceptions without logging or surfacing the failure.
  Impact: Stats write failures become silent, making debugging and observability difficult and encouraging hidden data loss.
  Recommendation: Log the exception (or surface it via a structured error hook) while still preventing the stats failure from breaking execution.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: `_build_llm_request` casts `request.metadata.get("attempt", 1)` with `int(...)` without type-checking the metadata value.
  Impact: Non-numeric or `None` values in metadata will raise `TypeError`/`ValueError`, leading to unexpected failures in request building.
  Recommendation: Guard with `isinstance` checks and fall back to a safe default, or validate metadata earlier.
  Architecture alignment: Unknown
