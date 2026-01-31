# Error Handling Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: The `unknown_node` failure response omits `error_type`, leaving it as `None`.
  Impact: Recovery policy selection falls back to `Exception`, losing the specific failure classification and undermining consistent recovery semantics.
  Recommendation: Set `error_type=Exception` (or a dedicated graph/validation error type) in the `unknown_node` response to keep recovery mapping deterministic.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `RetryPolicy.delay_seconds` is never applied in `_execute_child_with_recovery`.
  Impact: Retry behavior ignores configured backoff, increasing the likelihood of repeated transient failures and rate-limit amplification.
  Recommendation: Honor `delay_seconds` (e.g., `time.sleep`) or remove the field and document that delay is unsupported.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `RetryPolicy.max_attempts` is applied as additional retries after the initial attempt, yielding total attempts of `max_attempts + 1`.
  Impact: Recovery attempts may exceed configured limits, producing unexpected extra calls and violating policy semantics.
  Recommendation: Decide whether `max_attempts` is total attempts or retry attempts; adjust the loop and documentation to match.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `_record_attempt` swallows all exceptions without logging or surfacing diagnostics.
  Impact: Stats persistence failures are silent, obscuring systemic errors and making recovery behavior harder to audit.
  Recommendation: Log the exception (or return a failure metric) so dropped stats do not disappear silently.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Condition evaluation errors inside `condition_func(response)` are not caught; only condition registry lookup errors are handled.
  Impact: A buggy condition causes a generic `internal_error`, losing the condition name and preventing targeted recovery or debugging.
  Recommendation: Wrap `condition_func(response)` in a try/except and return a specific failure reason with condition context.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: When retry is unsafe (`side_effect_class` not retryable), the returned `unsafe_to_retry` response discards the original failure details and error type.
  Impact: Callers lose the root cause and cannot distinguish between the original failure and the retry safety gate.
  Recommendation: Preserve the original `error_type` and include the prior `reason/details` in the `unsafe_to_retry` response.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Recovery behavior for retries/repairs at the `Block` level is untested; there are no tests asserting retry limits, delay usage, or unsafe-to-retry behavior.
  Impact: Error-handling regressions in recovery semantics can slip through without detection.
  Recommendation: Add targeted tests for `_execute_child_with_recovery` covering retry counts, delay handling, and unsafe retry gating.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/llm_service.py
  Issue: `LLMService.execute` maps all exceptions (including internal bugs like `TypeError`) into LLM failures.
  Impact: Programming errors are misclassified as provider failures, masking defects and potentially triggering inappropriate recovery or retries.
  Recommendation: Restrict `map_llm_error` usage to known LLM/provider errors; re-raise or wrap unexpected exceptions as `internal_error` with explicit diagnostics.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/response_status.py
  Issue: `ResponseStatus.BUDGET_ERROR` is defined but never produced by `llm_error_mapper` or any caller.
  Impact: Budget-related failures have no concrete mapping path and will fall back to generic mechanical errors.
  Recommendation: Either implement explicit budget error mapping or remove the unused status to avoid dead-path semantics.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Context-length classification relies on a broad `context` substring match in error names/messages.
  Impact: Unrelated errors containing the word "context" can be misclassified as `ContextLengthError`, leading to incorrect recovery choices.
  Recommendation: Prefer provider-specific error codes/fields for context-length detection and fall back to string matching only when codes are unavailable.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: The default stats store is constructed at import time and will raise if the JSON stats file is corrupt or unreadable.
  Impact: A corrupted stats file can crash process startup, turning a recoverable stats issue into a hard failure.
  Recommendation: Lazily initialize the default store or handle `JSONDecodeError`/IO errors and fall back to an empty in-memory store.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal LLM retry metadata uses non-namespaced keys (`llm_attempt`, `llm_retry_count`).
  Impact: Increases collision risk with other metadata producers and complicates recovery/trace tooling that expects namespaced counters.
  Recommendation: Rename to a namespaced form (for example `llm.attempt`, `llm.retry_count`) per metadata guidance.
  Architecture alignment: No
