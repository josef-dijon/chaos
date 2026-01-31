# Testability Review

Timestamp: 2026-01-31-145336

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: UUID and timing are generated internally (uuid4, perf_counter) with no injectable clock/ID provider.
  Impact: Tests cannot deterministically assert correlation metadata or duration behavior, forcing brittle assertions or monkeypatching globals.
  Recommendation: Inject a clock and ID generator (or accept them as optional constructor params) and use those in `_with_base_metadata`, `_build_child_request`, and `execute` timing.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Recovery and transition logic depend on global registries (ConditionRegistry, RepairRegistry) and static PolicyHandler without injection.
  Impact: Unit tests must patch global singletons to control conditions/repairs, making tests order-dependent and harder to isolate.
  Recommendation: Accept registries/handlers as constructor parameters or provide overridable factory methods for test doubles.
  Architecture alignment: Unknown

- Severity: High
  File: src/chaos/stats/store_registry.py
  Issue: Default stats store is instantiated at import time using `Config.load()` and `JsonBlockStatsStore`, which touches filesystem and config before tests can override it.
  Impact: Tests become order-dependent, slow, and may read/write real user files unless every test patches the registry early.
  Recommendation: Lazy-initialize the default store inside `get_default_store()` or provide an explicit bootstrap function; avoid IO in module import.
  Architecture alignment: Unknown

- Severity: High
  File: tests/domain/test_llm_primitive.py
  Issue: No tests cover composite block execution, recovery policies (Retry/Repair/Bubble), or condition resolution in `Block._execute_graph`/`_execute_child_with_recovery`.
  Impact: Core control-flow and recovery semantics can regress silently, especially around retries, repair functions, and branch conditions.
  Recommendation: Add focused unit tests for `_execute_graph` transitions (string/list), retry/repair/bubble policy handling, and condition resolution failures.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/messages.py
  Issue: `Response` assigns a random `metadata.id` via `uuid4()` during initialization with no injection point.
  Impact: Tests that assert metadata need to patch global UUIDs or ignore the field, reducing determinism.
  Recommendation: Allow passing an ID generator or accept `metadata.id` explicitly without overriding it in `__init__`.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Stats recording uses the global default store via `get_default_store()` with no per-block injection or opt-out.
  Impact: Unit tests must mutate global state to avoid file IO and cannot isolate stats behavior to a single block instance.
  Recommendation: Accept a stats store in the `Block` constructor or allow disabling recording for tests.
  Architecture alignment: Unknown

- Severity: Medium
  File: tests/domain/test_llm_primitive.py
  Issue: Most tests do not set a default stats store, so they implicitly use the JSON-backed store created at import time.
  Impact: Tests can read/write real `.chaos/db/block_stats.json`, causing slow IO and cross-test pollution.
  Recommendation: Use a fixture to set `InMemoryBlockStatsStore` for every test and reset the registry after each test.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/llm_service.py
  Issue: No unit tests cover `_render_prompts` or `_build_model` branch behavior (system + multi-role messages, API base routing, env key fallback).
  Impact: Prompt rendering and provider configuration regressions will not be caught, and these are high-impact integration seams.
  Recommendation: Add tests that exercise multi-message rendering, empty system prompt, proxy base usage, and API key selection behavior.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Error mapping logic has no tests for key branches (HTTP 401/403/429, ValidationError vs UnexpectedModelBehavior, heuristic fallbacks).
  Impact: Changes to error types or message patterns can silently break failure classification and recovery policy selection.
  Recommendation: Add parameterized tests covering each mapping branch and the generic fallback.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Correlation metadata propagation (`trace_id`, `run_id`, `span_id`, `parent_span_id`, `attempt`) is untested across child retries/repairs.
  Impact: Observability regressions (wrong span linkage or attempt numbering) will not be detected, reducing debuggability.
  Recommendation: Add tests that execute a composite block with retries/repairs and assert metadata propagation on child responses and stats records.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/litellm_stats_adapter.py
  Issue: Adapter fallback behavior (returning the provided prior when store returns a prior or empty stats) has no direct tests.
  Impact: Subtle regressions could change estimation behavior without test coverage, skewing cost/latency estimates.
  Recommendation: Add unit tests for both branches: store returns prior/empty vs store returns stats-based estimate.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: `_coerce_payload` supports string payloads and dict keys `prompt`/`content`/`input`, but tests only cover the `prompt` dict path.
  Impact: Alternative input forms can break without detection, narrowing supported inputs despite the code path.
  Recommendation: Add tests for string payloads, `content` key, and `input` key to confirm behavior and error handling.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Retry loop semantics (`for _ in range(policy.max_attempts)`) are not covered by tests to confirm expected total attempts and metadata increments.
  Impact: Off-by-one errors in retry counts can slip into production without detection, skewing retry behavior and stats.
  Recommendation: Add tests that assert exact number of executions and `attempt` metadata across `RetryPolicy` boundaries.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: No tests validate the exception-to-Response conversion path in `Block.execute` when `_execute_primitive` or child execution raises.
  Impact: Unhandled exception formatting or missing metadata can regress without coverage, leading to inconsistent error responses.
  Recommendation: Add tests that raise exceptions in a stub block and assert `internal_error` response fields and metadata attachments.
  Architecture alignment: Unknown
