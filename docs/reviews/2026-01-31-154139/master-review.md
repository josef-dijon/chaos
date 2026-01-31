# Master Review

## Top Risks
- Severity: High
  Source: Logging Observability Review
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Error details include `str(error)` and `str(__cause__)`, which may embed raw prompts, model outputs, or credentials from upstream exceptions.
  Impact: PII and sensitive data can be persisted in responses/logs and grow without bounds, violating logging hygiene and privacy controls.
  Recommendation: Sanitize error strings (redact tokens, prompts, headers) and cap detail size; prefer stable error codes plus minimal safe fields (e.g., status_code).

- Severity: High
  Source: Performance Scalability Review
  File: src/chaos/stats/json_block_stats_store.py
  Issue: `record_attempt` rewrites the full JSON file on every attempt via `_save`, and `_save` serializes the entire in-memory list each time.
  Impact: O(n) disk I/O per attempt causes severe latency spikes and poor throughput as history grows; can become a bottleneck on busy systems.
  Recommendation: Switch to append-only journaling or a real datastore; at minimum batch writes, rotate files, or checkpoint periodically instead of per attempt.

- Severity: High
  Source: Dependency Config Review
  File: src/chaos/config.py
  Issue: `Config.load()` uses `model_validate(payload)` which bypasses `BaseSettings` sources, so environment variables and `.env` are ignored whenever a JSON config exists.
  Impact: Deploy-time overrides (secrets, endpoints, model settings) silently stop working, increasing risk of running with stale or checked-in values.
  Recommendation: Load JSON via `Config(**payload)` or implement a custom settings source order that merges JSON with env, explicitly documenting precedence (env should override file for secrets).

- Severity: High
  Source: Architecture Solid Review
  File: src/chaos/domain/block.py
  Issue: Composite responses retain child correlation metadata because _attach_correlation_metadata uses setdefault, so child span/attempt IDs remain instead of the composite's own attempt identifiers.
  Impact: Observability and recovery tracing become ambiguous; composite-level attempts cannot be reliably distinguished from child attempts, violating the request/metadata propagation rules.
  Recommendation: When a composite returns a synthesized response, explicitly overwrite trace/span/run/attempt/block_name in response.metadata with the composite's request metadata (not setdefault).

## Architecture Solid Review
# Architecture Solid Review
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
  Issue: Request.payload is typed as Dict[str, Any], which contradicts the architecture contract that payload can be any type (strings, objects, etc.).
  Impact: This constrains callers and blocks that legitimately accept non-dict payloads, forcing coercions or silent schema drift away from the documented block contract.
  Recommendation: Change Request.payload to Any (or a union that includes str) and update validation/tests to preserve the architecture's payload flexibility.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Composite responses retain child correlation metadata because _attach_correlation_metadata uses setdefault, so child span/attempt IDs remain instead of the composite's own attempt identifiers.
  Impact: Observability and recovery tracing become ambiguous; composite-level attempts cannot be reliably distinguished from child attempts, violating the request/metadata propagation rules.
  Recommendation: When a composite returns a synthesized response, explicitly overwrite trace/span/run/attempt/block_name in response.metadata with the composite's request metadata (not setdefault).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Several failure responses omit error_type (e.g., unknown_node in _execute_graph), despite error_type being the canonical selector for recovery policies.
  Impact: Callers cannot consistently select recovery policies, and failures become less deterministic across the block boundary.
  Recommendation: Set error_type on all Response failures, using a stable error classification (or Exception as a default) per the response contract.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: Request objects never receive a unique metadata id, and _build_child_request does not generate one, despite the request/metadata spec recommending per-envelope ids.
  Impact: Request/response correlation breaks at the request layer; tracing and recovery replay cannot reliably identify individual request envelopes.
  Recommendation: Generate a metadata "id" in Request.__init__ or in Block._with_base_metadata and Block._build_child_request to ensure each request has a unique envelope id.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Domain-level Block depends directly on engine registries (ConditionRegistry, RepairRegistry, PolicyHandler), coupling core domain primitives to orchestration/infrastructure modules.
  Impact: Breaks clean layering and makes the domain block untestable without engine wiring, violating dependency inversion and impeding reuse of Block in other runtimes.
  Recommendation: Invert these dependencies via interfaces injected at construction or move orchestration concerns into an engine-layer composite executor.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: LLMPrimitive constructs Config and LiteLLMStatsAdapter via global defaults, baking infrastructure configuration and persistence into a domain block.
  Impact: Violates dependency inversion and makes the core block lifecycle dependent on environment/file I/O, reducing portability and test isolation.
  Recommendation: Require Config and stats adapter as injected dependencies (or factory-injected) and keep the block constructor side-effect free.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: LLMPrimitive accepts dict payloads with keys like "prompt"/"content", but the architecture contract defines payload as a plain string for LLMPrimitive.
  Impact: Input contract drift makes block usage inconsistent with docs and complicates composition because callers cannot rely on the documented payload shape.
  Recommendation: Enforce a string-only payload or update the architecture doc to explicitly allow the dict shape and required keys.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Invalid input payloads are classified as SchemaError, conflating input validation failures with output schema failures.
  Impact: Recovery policy selection and analytics cannot distinguish between bad input and model output schema errors.
  Recommendation: Introduce a dedicated input validation error type (or use a generic validation error) and map invalid payloads to that error_type with a distinct reason.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: Default stats store is instantiated at import time using Config.load(), performing configuration and file-system decisions during module import.
  Impact: Hidden side effects at import violate clean boundaries, complicate testing, and make dependency injection harder for domain blocks.
  Recommendation: Lazily initialize the default store on first access or inject it from the application layer.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal retry metadata uses generic keys like "llm_attempt" instead of the recommended namespaced form (e.g., "llm.attempt").
  Impact: Increases risk of metadata key collisions in composites that merge metadata from multiple blocks or tools.
  Recommendation: Namespace internal metadata keys per the request/metadata guidelines and document them.
  Architecture alignment: Yes

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Tests never assert the documented payload contract or request metadata requirements (string payloads, unique request ids, propagation rules).
  Impact: Contract drift can ship unnoticed, and architecture compliance becomes a documentation-only check.
  Recommendation: Add tests that cover string payloads and request/response metadata propagation, including request id creation and attempt/spans.
  Architecture alignment: Unknown

## Error Handling Review
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

## Testability Review
# Testability Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: `_build_manager_id` hardcodes `uuid4()` with no injectable seam.
  Impact: Tests cannot deterministically assert manager_id values or verify downstream metadata without brittle regex assertions.
  Recommendation: Inject an ID generator or allow `manager_id` override for tests; default to `uuid4()` in production.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_with_base_metadata` and `_build_child_request` hardcode `uuid4()` for trace/run/span IDs with no injection point.
  Impact: Correlation metadata is nondeterministic, making unit tests for metadata propagation and retry/repair tracking brittle.
  Recommendation: Add a configurable ID factory or allow request metadata seeding to bypass UUID generation in tests.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `get_default_store()` is called directly in `estimate_execution` and `_record_attempt` with no dependency injection.
  Impact: Unit tests must patch global state to prevent file I/O or cross-test contamination, increasing flakiness and setup complexity.
  Recommendation: Accept a stats store dependency (constructor or setter) and use it consistently; default to `get_default_store()` in production.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Recovery and transition logic rely on global registries (`ConditionRegistry`, `RepairRegistry`) without injectable seams.
  Impact: Tests must monkeypatch global registries to simulate conditions/repairs, which makes isolation and parallel test execution harder.
  Recommendation: Pass registry interfaces into `Block` or `PolicyHandler`, or provide override hooks for tests.
  Architecture alignment: Unknown

- Severity: Medium
  File: tests/domain/test_llm_primitive.py
  Issue: No tests exercise composite `Block` recovery paths (retry, repair, bubble, unsafe_to_retry, max_steps, invalid_graph, condition errors).
  Impact: Core recovery behavior can regress without detection, undermining the 95% coverage mandate for error handling.
  Recommendation: Add focused unit tests using a minimal composite block to cover each recovery branch and failure response.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/messages.py
  Issue: `Response.__init__` mutates metadata with a random UUID and provides no way to inject a deterministic ID.
  Impact: Unit tests that validate response metadata must either ignore IDs or use brittle pattern assertions.
  Recommendation: Accept an optional `id` in constructor or allow an injectable ID factory for tests.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: `_DEFAULT_STORE` is initialized at import time via `Config.load()` and `JsonBlockStatsStore`, with no lazy initialization.
  Impact: Importing the module can trigger config/file system side effects in tests, forcing heavy monkeypatching and slowing test startup.
  Recommendation: Lazily create the default store on first access or allow injecting a factory during tests.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/stats/json_block_stats_store.py
  Issue: The constructor eagerly reads from disk and `_save` always writes to disk with no injectable filesystem or serializer.
  Impact: Unit tests must use real files or monkeypatch `Path`, reducing isolation and slowing test runs.
  Recommendation: Add an optional file I/O interface or allow injecting read/write callables for tests.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: `__init__` calls `Config.load()` by default, triggering filesystem/env reads during object construction.
  Impact: Unit tests that forget to pass `config` implicitly depend on local config files and environment variables.
  Recommendation: Accept a config provider/factory or default to a lazy `Config.load()` call in execution paths only.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: No tests cover the LiteLLM proxy branch in `_resolve_api_settings` (api_base and proxy key selection).
  Impact: Proxy routing regressions can slip through without detection, and config-to-request wiring is unverified.
  Recommendation: Add tests for `litellm_use_proxy=True` with and without `litellm_proxy_api_key` to assert `api_base`/`api_key` behavior.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Metadata propagation rules in `block-request-metadata.md` are not covered by tests (trace/run/span/id/attempt updates across child requests and retries).
  Impact: Observability and recovery metadata can silently drift from the architecture contract without failing tests.
  Recommendation: Add tests that assert reserved metadata keys are propagated and incremented correctly for child, retry, and repair attempts.
  Architecture alignment: Yes

- Severity: Low
  File: tests/llm/test_llm_service.py
  Issue: Missing coverage for `map_llm_error` handling of HTTP 401/403 responses.
  Impact: Authentication error mapping can regress without detection, undermining recovery and user feedback for auth failures.
  Recommendation: Add tests that build `httpx.HTTPStatusError` with 401 and 403 and assert `api_key_error` mapping.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/stats/test_block_estimation.py
  Issue: No assertions cover `build_estimate_from_records` fallback notes when cost/llm_calls/block_executions are missing.
  Impact: Note-generation regressions can slip in without detection, reducing transparency of estimation quality.
  Recommendation: Add tests with partial records to assert `*_fell_back_to_prior` notes are present.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_record_attempt` swallows all exceptions without logging or signaling failure.
  Impact: Stats recording failures are silent and difficult to test; coverage cannot validate error handling or observability behavior.
  Recommendation: Emit a warning/log or expose a hook so tests can assert recording failures are surfaced.
  Architecture alignment: Unknown

- Severity: Low
  File: scripts/llm_primitive_demo.py
  Issue: `run_demo` constructs `LLMPrimitive` with real `LLMService` and reads config directly, with no dependency injection.
  Impact: The demo logic cannot be unit tested without live network calls and real config files.
  Recommendation: Accept optional `config` and `llm_service` parameters or use a factory to allow stubbing in tests.
  Architecture alignment: Not Available

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: `_coerce_payload` branches for `content` and `input` keys are untested.
  Impact: Payload normalization can regress for non-`prompt` inputs without being detected.
  Recommendation: Add tests for `payload={'content': '...'}` and `payload={'input': '...'}` to assert success.
  Architecture alignment: Unknown

## DRY Dead Code Review
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

## Python Best Practices Review
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

## Naming Maintainability Review
# Naming Maintainability Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: The identifier name `manager_id` and `_build_manager_id` are domain-opaque; “manager” does not describe what is being managed (request, execution, trace, or correlation).
  Impact: Readers cannot infer whether this is a request-id, execution-id, or audit correlation id, making cross-service tracing harder to maintain and easy to misuse.
  Recommendation: Rename to something explicit like `execution_id` or `correlation_id` and align field names in `LLMRequest`/metadata to the same term.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_execute_child_with_recovery` mixes retry, repair, and generic policy handling with deep nesting and repeated request/response bookkeeping.
  Impact: Complex control flow makes recovery behavior hard to reason about and risky to modify, increasing maintenance cost and bug likelihood.
  Recommendation: Split into smaller helpers (e.g., `_apply_retry_policy`, `_apply_repair_policy`, `_apply_generic_policy`) and keep the high-level loop declarative.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: Response uses `ok` as the field name but exposes `success` as an alias, while most call sites pass `success=` and use `success()` method.
  Impact: Dual naming creates cognitive overhead and easy-to-miss inconsistencies when refactoring or searching usages.
  Recommendation: Pick a single canonical field name (`success` preferred for clarity) and remove the alias/secondary name.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but `LLMPrimitive` accepts raw `str` payloads and treats dict keys as optional fallbacks.
  Impact: The public request contract is unclear and encourages inconsistent call patterns, making API usage harder to discover and validate.
  Recommendation: Widen `payload` type to `Any` or introduce a dedicated `prompt` field/type for LLM primitives and document the expected shapes.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block_estimate.py
  Issue: `estimate_source` and `confidence` are free-form strings with no enum/typed guardrails.
  Impact: Inconsistent or misspelled values are easy to introduce, reducing downstream readability and making analytics brittle.
  Recommendation: Replace with enums (or `Literal[...]`) and document the allowed values in one place.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `side_effect_class` is a free-form string with normalization logic and magic values scattered across the class.
  Impact: New contributors can introduce incompatible values, and the normalization behavior is easy to miss.
  Recommendation: Use an enum (or `Literal`) for side effect classes and validate at construction time to make intent explicit.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_request.py
  Issue: `manager_id` is stored both as a top-level field and duplicated in `metadata`, but only metadata appears to be consumed.
  Impact: Redundant fields invite drift and make it unclear which value is authoritative when debugging requests.
  Recommendation: Keep a single source of truth (either top-level `manager_id` or `metadata['manager_id']`) and remove the duplicate.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_error_mapper.py
  Issue: `map_llm_error` contains duplicated branches that map multiple schema-related cases to the exact same `LLMErrorMapping`.
  Impact: Redundant logic makes the function longer and harder to audit, increasing the chance of inconsistent edits.
  Recommendation: Consolidate schema-error checks into a single guard (e.g., helper predicate) and return once.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/messages.py
  Issue: `Response.__init__` mutates `metadata` by injecting an `id` field, but this implicit behavior is undocumented in the model fields.
  Impact: Hidden side effects make response creation harder to reason about and can surprise maintainers who rely on metadata being caller-owned.
  Recommendation: Document the auto-generated `metadata.id` (field description or class docstring) or expose it as an explicit field.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: Composite terminal responses inject `source`, `composite`, and `last_node` into `Response.metadata` without any explicit contract or typed structure.
  Impact: Downstream code has to rely on undocumented ad-hoc keys, making API ergonomics and refactors brittle.
  Recommendation: Define a structured metadata schema (or constants) for these keys and document them in the public response contract.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: `_DEFAULT_STORE` is constructed at import time via `Config.load()`, which can read disk and bind config before callers have a chance to configure paths.
  Impact: Hidden side effects at import make behavior order-dependent and harder to test or override cleanly.
  Recommendation: Lazy-load the default store on first access, or move initialization into an explicit setup function.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Metadata uses both `attempt` and `block_attempt`, with `attempt` coming from the request and `block_attempt` reintroduced in `_build_llm_request`.
  Impact: Multiple names for the same concept make logs and downstream analytics harder to interpret and maintain.
  Recommendation: Standardize on a single field name for block attempt metadata and remove the redundant alias.
  Architecture alignment: Unknown

## Logging Observability Review
# Logging Observability Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
- File: `src/chaos/domain/block.py`
- Issue: `Block._record_attempt` swallows all exceptions from the stats store without emitting any log or error signal.
- Impact: Metrics loss becomes silent, breaking observability for failed or successful attempts and hiding storage outages.
- Recommendation: Log record-attempt failures with trace_id/span_id/block_name and exception details; optionally surface a health metric/counter for stats failures.
- Architecture alignment: Unknown

- Severity: Low
- File: `src/chaos/domain/block.py`
- Issue: Request/child request metadata never sets a new `id` value, despite the architecture propagation rule to generate a unique envelope id per child request.
- Impact: Request envelopes are not uniquely identifiable, making it harder to correlate retries/repairs and nested executions in logs or traces.
- Recommendation: Populate `metadata["id"]` in `_with_base_metadata` and regenerate it in `_build_child_request` for each child attempt.
- Architecture alignment: No

- Severity: Medium
- File: `src/chaos/llm/llm_service.py`
- Issue: `LLMRequest.metadata` (including trace/run/span identifiers) is never propagated to the underlying provider call, so upstream LLM logs cannot be correlated with internal traces.
- Impact: Provider-side observability is blind to request lineage, making incident debugging and cost attribution significantly harder.
- Recommendation: Pass trace/run/span identifiers via provider metadata/tags if supported, or emit a structured log around the provider call with those IDs.
- Architecture alignment: Unknown

- Severity: Low
- File: `src/chaos/domain/llm_primitive.py`
- Issue: Internal attempt counters use non-namespaced keys (`block_attempt`, `llm_attempt`) instead of the namespaced form recommended for internal retry metadata.
- Impact: Metadata keys are more likely to collide with caller-provided fields and make log filters inconsistent across components.
- Recommendation: Rename to namespaced keys like `llm.block_attempt` and `llm.attempt` (or similar) and update downstream usage.
- Architecture alignment: No

- Severity: High
- File: `src/chaos/llm/llm_error_mapper.py`
- Issue: Error details include `str(error)` and `str(__cause__)`, which may embed raw prompts, model outputs, or credentials from upstream exceptions.
- Impact: PII and sensitive data can be persisted in responses/logs and grow without bounds, violating logging hygiene and privacy controls.
- Recommendation: Sanitize error strings (redact tokens, prompts, headers) and cap detail size; prefer stable error codes plus minimal safe fields (e.g., status_code).
- Architecture alignment: Unknown

- Severity: Medium
- File: `src/chaos/domain/block.py`
- Issue: Unhandled exceptions in `Block.execute` are converted to a failure response without any structured log entry.
- Impact: Hard failures vanish from logs and tracing systems, forcing operators to infer outages only from missing stats or downstream errors.
- Recommendation: Emit an error log on exception with `trace_id`, `span_id`, `block_name`, `node_name`, and the exception type/message.
- Architecture alignment: Unknown

## Documentation Review
# Documentation Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: docs/architecture/core/block-request-metadata.md
  Issue: The doc says `payload` is "any", but `Request.payload` is typed as `Dict[str, Any]` and rejects string payloads.
  Impact: Readers will follow the doc and send raw string payloads, which fail validation before `LLMPrimitive` can coerce them.
  Recommendation: Update the doc to reflect `payload` is a dict envelope (or document the accepted keys), or update `Request` to allow `Any` if strings are truly supported.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The Inputs table claims `payload` is a `str`, but `Request.payload` is a dict and LLMPrimitive tests only use dict envelopes.
  Impact: Documentation encourages an input shape that the runtime rejects, causing validation errors before execution.
  Recommendation: Update the Inputs table to describe the dict envelope (`prompt`/`content`/`input`) or revise the Request model to accept raw strings.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The policy section states PydanticAI manages API retries, but API retries are actually handled by the OpenAI SDK `max_retries` in `LLMService`.
  Impact: Readers debugging retry behavior will look in the wrong layer and misconfigure retry expectations.
  Recommendation: Clarify that output validation retries are in PydanticAI and API retries come from the OpenAI SDK client configuration.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/block-request-metadata.md
  Issue: The propagation rules require generating a new `id` for child requests, but `Block._build_child_request` never sets an `id` and `Request` does not auto-generate one.
  Impact: Implementers relying on the documented `id` correlation will not see it in runtime metadata, breaking traceability guarantees.
  Recommendation: Either document that `id` is response-only today or update the implementation to set `metadata["id"]` on requests per the spec.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: The doc mandates callers "MUST" prune child `context`, but `Block._build_child_request` forwards the full parent context unchanged.
  Impact: The documented context-minimization guarantee is not true in the default implementation, which can lead to over-sharing and heavier payloads.
  Recommendation: Update the spec to mark pruning as a caller responsibility (not enforced by the base class), or implement actual pruning hooks in the base class.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/block-interface.md
  Issue: The document states block state is used to guard execution and prevent re-entrancy, but `Block.execute` does not check or enforce state before running.
  Impact: The contract implies safety that the implementation does not provide, which can mislead callers about concurrency guarantees.
  Recommendation: Either document that state is informational-only today or add explicit guard logic in `Block.execute` and update docs accordingly.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: The doc recommends namespaced internal retry counters (e.g., `"llm.retry_count"`), but `LLMPrimitive` emits `llm_calls`/`llm_retry_count` and `llm_attempt` without a namespace.
  Impact: Users following the doc will search for namespaced keys and miss the actual metadata fields in responses and stats.
  Recommendation: Either update the doc to list the current keys or rename emitted metadata keys to the recommended namespace format.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The configuration surface omits runtime-relevant constructor options like `output_retries`, `config`, `stats_adapter`, `llm_service`, and `model_selector` that change behavior.
  Impact: Developers can unknowingly miss important tuning knobs or assume the primitive is less configurable than it is.
  Recommendation: Expand the configuration table to include these parameters or explicitly document them as internal/testing hooks.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The implementation note states provider calls are routed through LiteLLM, but `Config.litellm_use_proxy` can disable proxy routing entirely.
  Impact: Operational docs are misleading for direct-to-provider deployments and can cause misconfigured routing expectations.
  Recommendation: Update the note to say routing is conditional on `litellm_use_proxy` and document the fallback path.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The recovery section says local non-LLM errors (e.g., invalid payload) still use the recovery policy system, but `LLMPrimitive.get_policy_stack` always returns only `BubblePolicy`.
  Impact: Readers will expect recovery policies to apply to invalid payloads, but the implementation will always bubble without recovery.
  Recommendation: Either document that LLMPrimitive always bubbles (including invalid payloads) or implement a distinct policy stack for local errors.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: The reserved key table specifies `duration_ms` as an int, but `Block.execute` records it as a float.
  Impact: Consumers relying on integer duration values may mis-handle the data or fail strict schema validation.
  Recommendation: Update the doc to allow float milliseconds or cast duration to int in code and document the rounding behavior.
  Architecture alignment: No

## Security Privacy Review
# Security Privacy Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: src/chaos/config.py
  Issue: API keys are stored as plain strings in Config and are not marked secret/excluded from serialization or repr.
  Impact: Secrets can leak into logs, debug output, or accidental JSON dumps of the settings object.
  Recommendation: Use `pydantic.SecretStr` (or equivalent) for API key fields and set `repr=False`/`exclude=True` where appropriate; avoid exposing keys via model_dump unless explicitly requested.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/llm_request.py
  Issue: `api_key` is a plain string field on `LLMRequest`, making it easy to leak via serialization, logging, or exception traces.
  Impact: Accidental leakage of provider credentials into logs or persisted artifacts can compromise the LLM account.
  Recommendation: Replace `api_key: Optional[str]` with `SecretStr` (or a dedicated credential wrapper) and exclude it from `model_dump`/repr by default.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Error mapping captures raw `str(error)` and `str(cause)` into `details` without redaction.
  Impact: Provider exceptions and validation errors often include request/response payloads, which can leak prompts, model outputs, or other sensitive data into user-visible responses or logs.
  Recommendation: Redact/whitelist error fields before storing them, and avoid including raw exception strings in responses by default.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Unhandled exceptions are converted into `Response.details` with raw `str(e)`.
  Impact: Internal exceptions can carry secrets, prompt content, or PII and will be exposed to callers or logs without redaction.
  Recommendation: Replace raw exception strings with stable error codes and sanitized metadata; keep full exceptions only in restricted internal logs.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/stats/json_block_stats_store.py
  Issue: Stats are persisted to a JSON file without retention limits, access controls, or redaction of identifiers.
  Impact: Trace/run identifiers and model metadata can accumulate indefinitely on disk, increasing privacy exposure and forensic risk if the file is read by unauthorized users.
  Recommendation: Add retention/rotation, minimize stored fields, and consider writing with restrictive file permissions (e.g., 0o600) or a secured store.
  Architecture alignment: Unknown

- Severity: Low
  File: scripts/llm_primitive_demo.py
  Issue: Demo script prints raw failure details directly to stdout.
  Impact: Failure details may contain provider error messages or validation payloads that include sensitive prompt/output content, leading to inadvertent disclosure in terminals or logs.
  Recommendation: Redact sensitive fields or print only stable error codes; optionally gate verbose details behind a `--debug` flag.
  Architecture alignment: Not Available

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: When `litellm_use_proxy` is true but no proxy URL is configured, `_resolve_api_settings` silently falls back to direct OpenAI base URL.
  Impact: Intended data-governance/egress controls can be bypassed, sending prompts to the public endpoint without explicit approval.
  Recommendation: Fail closed when proxy usage is enabled but `litellm_proxy_url` is missing; require explicit override to allow direct routing.
  Architecture alignment: Unknown

## Performance Scalability Review
# Performance Scalability Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: `src/chaos/domain/block.py`
  Issue: `_execute_graph` calls `_validate_graph` on every execution, re-walking nodes/transitions for a graph that is effectively static after `build()`.
  Impact: Adds O(nodes + transitions) overhead per request and scales poorly for large composite graphs or high QPS.
  Recommendation: Validate once during `build()`/`set_graph()` and cache a validated flag; only revalidate when graph config changes.
  Architecture alignment: Yes

- Severity: Medium
  File: `src/chaos/domain/block.py`
  Issue: `_with_base_metadata` and `_build_child_request` use `model_copy(deep=True)` for every step/retry, cloning full payload/context even when unchanged.
  Impact: Deep copies amplify memory use and CPU time on large payloads and increase latency with nested composites and retries.
  Recommendation: Prefer shallow copies with targeted metadata mutation (or immutable metadata struct) and only deep-copy payload/context when mutation is required.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/llm/llm_service.py`
  Issue: `_build_model` constructs a new `AsyncOpenAI` client and `OpenAIChatModel` on every request with no reuse or pooling.
  Impact: Repeated client/model instantiation increases latency and connection churn under high QPS, and prevents efficient connection reuse.
  Recommendation: Cache `OpenAIChatModel`/provider by (model, api_base, api_key, retries) or inject a long-lived client via `model_builder` for reuse.
  Architecture alignment: Unknown

- Severity: High
  File: `src/chaos/stats/json_block_stats_store.py`
  Issue: `record_attempt` rewrites the full JSON file on every attempt via `_save`, and `_save` serializes the entire in-memory list each time.
  Impact: O(n) disk I/O per attempt causes severe latency spikes and poor throughput as history grows; can become a bottleneck on busy systems.
  Recommendation: Switch to append-only journaling or a real datastore; at minimum batch writes, rotate files, or checkpoint periodically instead of per attempt.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/stats/json_block_stats_store.py`
  Issue: `estimate` linearly scans all stored records to filter by block identity on every call.
  Impact: O(n) CPU time per estimate increases latency as attempt history grows and scales poorly with many blocks.
  Recommendation: Maintain an index keyed by (block_name, block_type, version) or pre-group records when loading to make estimates O(k) for relevant samples.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/stats/json_block_stats_store.py`
  Issue: `_load` reads the entire JSON file into memory and keeps all records resident for the lifetime of the process.
  Impact: Memory usage grows unbounded with historical attempts and can degrade performance or crash long-lived services.
  Recommendation: Use a bounded store (rolling window), streaming/append-only format with paging, or a database with query limits.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/domain/block.py`
  Issue: `_execute_graph` resolves `ConditionRegistry.get` for each transition branch on every execution instead of pre-resolving conditions.
  Impact: Adds repeated registry lookups on hot paths and increases latency with many branching transitions.
  Recommendation: Resolve condition callables once during graph setup and store them in the transition config for direct invocation.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/llm/llm_service.py`
  Issue: `_run_agent` creates a new PydanticAI `Agent` for every request, even when model/output schema are identical.
  Impact: Per-request object construction adds overhead and GC pressure for high-throughput workloads.
  Recommendation: Cache agents keyed by (model, output schema, system prompt) or introduce a lightweight agent factory with reuse.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/domain/block.py`
  Issue: `RetryPolicy.delay_seconds` is never honored in `_execute_child_with_recovery`, resulting in tight retry loops.
  Impact: Burst retries can overwhelm upstream providers, increase rate-limit errors, and amplify latency spikes under load.
  Recommendation: Implement backoff/sleep using `delay_seconds` (and consider jitter/exponential backoff) before each retry attempt.
  Architecture alignment: Yes

- Severity: Low
  File: `src/chaos/stats/statistics.py`
  Issue: `mean_std` materializes the entire iterable into a list and makes multiple passes over the data.
  Impact: Extra memory and CPU overhead for large sample sets, which compounds when estimates are recalculated frequently.
  Recommendation: Use a single-pass streaming algorithm (e.g., Welford) or accept iterables already materialized to avoid extra copies.
  Architecture alignment: Not Available

- Severity: Low
  File: `src/chaos/domain/block.py`
  Issue: `_execute_graph` deep-copies the terminal `Response` just to add metadata (`response.model_copy(deep=True)`), even when the payload is large.
  Impact: Unnecessary memory churn and latency when responses contain big data structures.
  Recommendation: Avoid deep copy by cloning only metadata or creating a shallow copy with updated metadata.
  Architecture alignment: Unknown

## Dependency Config Review
# Dependency Config Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: pyproject.toml
  Issue: All runtime and dev dependencies are specified with only lower bounds (`>=`) and no upper bounds or lockfile pinning strategy.
  Impact: Version drift can introduce breaking API changes or behavior regressions without any code change, making builds non-reproducible and fragile over time.
  Recommendation: Add upper bounds (e.g., `<2`) for core dependencies or adopt a lockfile/pinning workflow with `uv` (e.g., `uv lock` and `uv sync`) to ensure reproducible installs.
  Architecture alignment: Unknown

- Severity: High
  File: src/chaos/config.py
  Issue: `Config.load()` uses `model_validate(payload)` which bypasses `BaseSettings` sources, so environment variables and `.env` are ignored whenever a JSON config exists.
  Impact: Deploy-time overrides (secrets, endpoints, model settings) silently stop working, increasing risk of running with stale or checked-in values.
  Recommendation: Load JSON via `Config(**payload)` or implement a custom settings source order that merges JSON with env, explicitly documenting precedence (env should override file for secrets).
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/config.py
  Issue: `litellm_use_proxy` does not enforce required companion settings (proxy URL and API key), so invalid proxy configurations can pass schema validation.
  Impact: Runtime failures or silent misrouting occur if proxy mode is enabled without a URL or credentials, making production behavior unpredictable.
  Recommendation: Add a model validator to require `litellm_proxy_url` (and optionally `litellm_proxy_api_key`) when `litellm_use_proxy` is true, and document the expected override rules.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/test_config.py
  Issue: Configuration tests do not cover environment-variable overrides or `.env` precedence relative to JSON files.
  Impact: A critical config precedence bug (env ignored when JSON exists) could ship unnoticed, and future changes to settings sources are unguarded.
  Recommendation: Add tests that set `OPENAI_API_KEY`/`CHAOS_*` env vars and verify they override JSON, plus a test for proxy-required fields when `litellm_use_proxy` is true.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/config.py
  Issue: The JSON config schema accepts `openai_api_key` in cleartext without any guardrails or separation guidance.
  Impact: Secrets are likely to end up in local files or checked into repositories, and no runtime mechanism discourages or prevents this.
  Recommendation: Prefer env-only secrets by documenting `openai_api_key` as env-only, optionally add validation that rejects keys in JSON unless an explicit allow flag is set.
  Architecture alignment: Unknown
