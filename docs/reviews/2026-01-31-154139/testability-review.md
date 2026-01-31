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
