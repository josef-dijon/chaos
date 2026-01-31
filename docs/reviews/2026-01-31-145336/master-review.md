# Master Review

Timestamp: 2026-01-31-145336

## Top Risks

- Composite responses keep child metadata, breaking composite trace/span ownership and response provenance (src/chaos/domain/block.py).
- Repair policy retries drop repaired request metadata, losing recovery correlation and diagnostics (src/chaos/domain/block.py).
- No block_start/block_success/block_failure or recovery attempt events, leaving no execution event stream (src/chaos/domain/block.py).
- Stats store is created at import time and can fail on JSON corruption, blocking runtime startup (src/chaos/stats/store_registry.py).
- Observability docs promise composite metadata propagation, but implementation drops these fields (docs/architecture/core/block-observability.md).

## Architecture and SOLID Review

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but the architecture contract defines `payload` as `any` and LLMPrimitive expects string payloads; the request envelope is over-constrained.
  Impact: Blocks that legitimately accept non-dict payloads are forced into dict wrappers or rejected by validation, undermining the core Block interface and creating cross-layer coupling.
  Recommendation: Change `Request.payload` to `Any` (or a permissive union) and update any schema/validation assumptions so payload shape is block-specific.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: RepairPolicy flow discards the repaired `Request` by rebuilding from the parent request and only copying payload/context, violating the rule that repair must return a new request envelope.
  Impact: Repair functions cannot update metadata or request-level fields; recovery can silently ignore critical changes and violate deterministic repair semantics.
  Recommendation: Use the `repaired` request directly when building the next child attempt (preserving its metadata) and avoid reconstructing from the parent request.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Composite execution returns the child `Response` directly on failure, so the response metadata (block_name/span_id/attempt) reflects the child, not the composite boundary.
  Impact: The composite boundary leaks child identity, breaking traceability, response ownership, and the architecture’s requirement that each block returns its own outcome envelope.
  Recommendation: Synthesize a composite-level failure response (or clone and re-stamp metadata) so the returned response reflects the composite block as the responder.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Child request construction does not generate a new `metadata.id` despite the architecture’s requirement to create a new envelope id per request.
  Impact: Requests and responses cannot be uniquely correlated across nested executions, undermining observability and ledger provenance.
  Recommendation: Generate and set a new `metadata.id` when building child requests (and optionally for the root request in `_with_base_metadata`).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Child request construction clones the parent `context` wholesale; the base composite logic does not prune or map context for the child.
  Impact: Violates the request contract (caller must minimize context), increases coupling between blocks, and creates hidden dependencies across boundaries.
  Recommendation: Introduce a required hook or override to prune/map `context` per child, or enforce explicit context mapping in composite definitions.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: RetryPolicy execution ignores `delay_seconds` and does not implement any backoff or jitter behavior.
  Impact: Recovery behavior diverges from the recovery policy contract and can overwhelm downstream systems during retries.
  Recommendation: Honor `delay_seconds` (and optional jitter if added) before retry attempts, or delegate retry handling to a policy handler that enforces delays.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Domain `Block` directly depends on engine registries/handlers (`ConditionRegistry`, `RepairRegistry`, `PolicyHandler`), mixing orchestration infrastructure into the core domain model.
  Impact: Creates tight coupling across layers, makes domain blocks harder to test in isolation, and violates clean boundaries by requiring engine-level singletons inside core execution logic.
  Recommendation: Introduce domain-level abstractions or dependency injection for condition resolution and recovery handling, keeping engine-specific registries in the outer layer.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal attempt metadata uses non-namespaced keys (`block_attempt`, `llm_attempt`) instead of the recommended namespaced convention for internal retries.
  Impact: Increases the risk of metadata collisions and makes observability contracts harder to evolve without breaking consumers.
  Recommendation: Rename internal counters to a namespaced form (for example `llm.attempt`, `llm.retry_count`, `block.attempt`) and document them.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Condition resolution is validated at execution time, not during graph construction, even though the architecture requires fail-fast validation during build.
  Impact: Invalid graphs can be instantiated and only fail at runtime, violating deterministic construction guarantees and making errors harder to detect.
  Recommendation: Move condition validation into `build()`/`set_graph()` or add an explicit validation step during construction.
  Architecture alignment: No

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Tests do not assert required observability metadata (`trace_id`, `span_id`, `block_name`, `attempt`) despite explicit architecture testing guidelines.
  Impact: Metadata regressions can slip into production, breaking traceability and recovery analytics.
  Recommendation: Add assertions for the minimum response metadata keys and ensure they are correctly propagated in LLMPrimitive tests.
  Architecture alignment: No

## Error Handling Review

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `unknown_node` failures return a Response without `error_type` set (line ~204), despite `error_type` being the canonical recovery selector.
  Impact: Upstream recovery policy selection will silently fall back to a generic Exception, losing deterministic error classification and making failure handling inconsistent.
  Recommendation: Set `error_type` explicitly (for example `Exception` or a dedicated graph error class) on the `unknown_node` response.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `RetryPolicy.delay_seconds` is never honored in `_execute_child_with_recovery` (retry loop runs back-to-back with no delay or jitter).
  Impact: Retries can hammer providers and amplify rate-limit/mechanical failures; violates recovery policy backoff expectations.
  Recommendation: Sleep between retries using `delay_seconds` (with optional jitter), or explicitly document that delay is unsupported and remove the field.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Repair handling drops the repaired request metadata by copying only `payload`/`context` onto a clone of the original parent request (`repaired_parent_request`), instead of using the `Request` returned by the repair function.
  Impact: Any recovery metadata or correlation hints added by the repair function are silently lost, making repair diagnostics and subsequent policy selection unreliable.
  Recommendation: Use the `Request` returned from the repair function as the basis for the retry, and only override/propagate reserved metadata fields explicitly if needed.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: When retry/repair is unsafe, `_execute_child_with_recovery` returns a new `unsafe_to_retry` Response, discarding the original failure `reason`/`details`.
  Impact: The caller loses the root cause and cannot distinguish between the underlying failure vs. a recovery-policy veto, complicating incident analysis and policy tuning.
  Recommendation: Preserve the original failure (for example by returning it with an added `details.recovery_blocked=true` or by embedding the original failure under `details.original_failure`).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Condition evaluation exceptions (`condition_func(response)`) are not caught during transition selection, so a condition bug throws and is translated into a generic `internal_error` in `Block.execute`.
  Impact: The failure reason loses the condition name and becomes opaque to recovery policies and debugging.
  Recommendation: Catch exceptions around condition execution and return a structured failure (for example `reason=condition_evaluation_error`, with `details.condition` and the exception string).
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: If a block implementation accidentally returns `None`, `execute` constructs an `internal_error` Response after the `finally` block, so no correlation metadata is attached and no attempt is recorded.
  Impact: The most severe class of contract violation (returning None) is invisible to observability/metrics, making recovery and diagnosis harder.
  Recommendation: Create the fallback `internal_error` Response before `finally` exits (or in `finally`) so metadata and attempt records are always captured.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/llm/llm_service.py
  Issue: `_run_agent` raises a `TypeError` for unexpected output types, which maps via `map_llm_error` to a generic mechanical failure instead of a structured schema/semantic error.
  Impact: Recovery policies and analytics misclassify malformed model output as transient infrastructure failure, obscuring root cause and policy tuning.
  Recommendation: Map unexpected output types to `SchemaError` (or wrap in a dedicated exception) so `LLMResponse` is categorized as `SEMANTIC_ERROR`.
  Architecture alignment: Yes

- Severity: Medium
  File: src/chaos/stats/json_block_stats_store.py
  Issue: `_load` assumes the JSON file is valid; corrupt or partially-written stats files raise `json.JSONDecodeError` during store initialization with no recovery path.
  Impact: A single corrupted stats file can prevent the system from starting, even though stats are non-critical.
  Recommendation: Catch JSON decode/validation errors, log a warning, and start with an empty record set or a quarantined backup.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_execute_child_with_recovery` defaults to `Exception` when `response.error_type` is missing, instead of using a deterministic fallback mapping (for example, from `response.reason`).
  Impact: Serialized or partially-constructed failures lose recovery specificity, causing policy selection to degrade to the generic stack.
  Recommendation: Add a fallback classifier (e.g., map from `reason` to an error type) when `error_type` is absent.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Unknown exceptions are mapped with `error_type=type(error)`, which can be provider-specific and unstable across versions.
  Impact: Recovery policy selection becomes non-deterministic across environments and upgrades, making automated recovery brittle.
  Recommendation: Normalize unknown errors to a stable domain exception (for example `LLMError` or a new `UnknownLLMError`) while preserving the original class name in `details`.
  Architecture alignment: No

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Recovery semantics are largely untested (no coverage for retry/repair paths, unsafe-to-retry behavior, or error_type-missing fallback selection).
  Impact: Error handling regressions can ship unnoticed, especially in composite recovery flows.
  Recommendation: Add focused tests for retry delays, repair metadata propagation, and policy selection when `error_type` is absent.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: The default stats store is instantiated at import time, so any JSON parse error or filesystem issue raises during module import with no recovery.
  Impact: Non-critical stats corruption can prevent the entire runtime from starting, and the failure path is hard to recover from in callers.
  Recommendation: Lazily initialize the default store inside `get_default_store()` with guarded error handling and a safe fallback (for example in-memory store).
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but LLMPrimitive expects `payload` to be either a string or a dict; a string payload will fail validation before error handling can run.
  Impact: Invalid payloads raise Pydantic validation errors outside the block boundary, bypassing the standardized failure responses and recovery policies.
  Recommendation: Widen `Request.payload` to `Any` (or `str | dict`) and let blocks validate/normalize payloads into their own error responses.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `_record_attempt` swallows all exceptions without logging or surfacing any signal.
  Impact: Stats persistence failures are silent, making it impossible to detect missing attempt records that feed recovery/estimation logic.
  Recommendation: Log a warning (or emit a telemetry event) when attempt recording fails, including the exception and block identity.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: The `manager_id` created for LLM auditing is stored only in the internal `LLMRequest` metadata and is not surfaced in the block `Response` metadata.
  Impact: When failures occur, there is no stable identifier to correlate provider-side logs/requests with block-level errors, reducing recovery and debugging effectiveness.
  Recommendation: Copy `manager_id` into `Response.metadata` (for both success and failure) under a namespaced key (e.g., `llm.manager_id`).
  Architecture alignment: Unknown

## Testability Review

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

## DRY and Dead Code Review

- Severity: Medium
- File: src/chaos/stats/json_block_stats_store.py
- Issue: Duplicate record-filtering and estimate-building logic is repeated in src/chaos/stats/in_memory_block_stats_store.py.
- Impact: Any change to filtering criteria or prior/estimate behavior must be updated in two places, inviting drift and inconsistent stats.
- Recommendation: Extract a shared helper (or base class) for filtering relevant records and building the estimate, then call it from both stores.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/llm/llm_error_mapper.py
- Issue: schema_error, rate_limit_error, and api_key_error mappings are duplicated across multiple branches (typed exceptions, httpx status, string heuristics).
- Impact: Any future change to reason/status or error_type must be updated in several branches, increasing inconsistency risk.
- Recommendation: Factor shared mappings into small helper functions or a mapping table to collapse repeated return blocks.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/block.py
- Issue: ConditionRegistry.get is resolved in _validate_graph and again in _execute_graph for the same transitions, duplicating error handling paths.
- Impact: Validation and execution can drift (e.g., different error reasons) and redundant lookup adds noise to the execution loop.
- Recommendation: Cache resolved conditions during validation or centralize condition resolution to a single helper used by both methods.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/llm/model_selector.py
- Issue: select_model is a pass-through that deletes request and always returns the default, making the abstraction a no-op.
- Impact: Extra indirection without behavior increases surface area and can hide the fact that per-request selection is not implemented.
- Recommendation: Either implement real selection logic or inline model choice in LLMPrimitive and remove the unused selector abstraction.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/stats/estimate_builder.py
- Issue: build_estimate_from_records accepts request but immediately deletes it; request is unused in all current estimate flows.
- Impact: Dead parameter suggests incomplete design and adds confusion/noise to every call site.
- Recommendation: Remove the request parameter throughout the estimate path or implement request-aware estimation (e.g., token-based bucketing) to justify it.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/block.py
- Issue: Retry safety checks for RetryPolicy and RepairPolicy are duplicated with identical unsafe_to_retry responses.
- Impact: Any future change to retry eligibility or error messaging must be updated in multiple branches, increasing drift risk.
- Recommendation: Extract a shared helper to validate retry safety and return a standardized failure response used by both branches.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/llm/litellm_stats_adapter.py
- Issue: estimate() re-checks for prior/sample_size==0 even though the underlying store already returns a prior when there is no data.
- Impact: Redundant indirection makes behavior harder to reason about and invites subtle divergence if store logic changes.
- Recommendation: Return the store estimate directly, or move the fallback logic into a single shared layer and remove the duplicate check here.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/stats/in_memory_block_stats_store.py
- Issue: Duplicate record-filtering and estimate-building logic is repeated in src/chaos/stats/json_block_stats_store.py.
- Impact: Changes to stats selection or estimate behavior can diverge across stores, leading to inconsistent outputs in tests vs production.
- Recommendation: Centralize the common filtering/estimate logic in a shared helper to ensure identical behavior.
- Architecture alignment: Unknown

## Python Best Practices Review

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]` but callers accept strings or other shapes (e.g., `LLMPrimitive._coerce_payload`).
  Impact: Type checkers and readers get a false contract; downstream code may skip validation or narrow incorrectly.
  Recommendation: Widen `payload` to `Any` or a `Union[str, Mapping[str, Any]]` and document the allowed shapes.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: `_coerce_payload` contains a `str` branch, but `Request.payload` is currently a dict-only field, making the string path effectively dead.
  Impact: The implementation and data model disagree, so type narrowing and validation are inconsistent with runtime expectations.
  Recommendation: Align `Request.payload` typing/validation with `_coerce_payload` (or remove the `str` branch) so the contract matches behavior.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_service.py
  Issue: `_run_agent` passes `system_prompt=system_prompt or ()`, which yields an empty tuple instead of `None`/`str` when no system prompt is provided.
  Impact: This violates the annotated type contract and can trigger subtle runtime type errors if the SDK expects a string or None.
  Recommendation: Pass `None` (or an empty string) when no system prompt exists; avoid non-string sentinel values.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Many test functions/classes lack docstrings despite the project standard requiring documentation for every function and class.
  Impact: Violates the documented documentation standard and makes test intent harder to scan consistently.
  Recommendation: Add concise docstrings to each test function/class or explicitly exempt tests in the documentation standard.
  Architecture alignment: Yes

## Naming and Maintainability Review

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `current_request` is never updated inside `_execute_graph`, so the name implies per-node evolution that does not exist.
  Impact: Misleading names obscure the data flow and make it harder to reason about whether requests are transformed between nodes.
  Recommendation: Rename `current_request` to `base_request` or update the variable when a node response should drive the next request.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but callers (e.g., LLMPrimitive) treat it as `str | dict` and raise on non-string values.
  Impact: Type hints mislead maintainers and API consumers, increasing misuse and forcing runtime errors instead of guiding correct usage.
  Recommendation: Update the type to `str | Dict[str, Any]` (or `Any` with explicit docstring constraints) and align docstrings with actual accepted shapes.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/messages.py
  Issue: Response uses the field name `ok` with alias `success`, but the rest of the codebase calls `success()` or passes `success=True/False`.
  Impact: Two names for the same concept reduce readability and make JSON payloads and code usage inconsistent to scan.
  Recommendation: Rename the field to `success` and remove `ok`, or standardize on `success` while keeping `ok` only for backward-compatible serialization.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: The identifier `manager_id` is introduced without a clear domain meaning and is used like a request/span identifier.
  Impact: Unclear naming makes logs and metadata difficult to interpret and causes confusion about who/what is “managing.”
  Recommendation: Rename to a precise term like `request_id`, `execution_id`, or `llm_trace_id` and align docstrings/metadata keys accordingly.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/model_selector.py
  Issue: `ModelSelector.select_model` ignores `request` and always returns `default_model`, despite the class name implying selection logic.
  Impact: The API advertises configurability that does not exist, which misleads maintainers and hides where model routing should live.
  Recommendation: Either implement actual selection logic (e.g., from request metadata) or rename the class/method to `DefaultModelResolver` to reflect reality.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/stats/estimate_builder.py
  Issue: `build_estimate_from_records` accepts a `request` parameter but immediately discards it (`del request`).
  Impact: Dead parameters make the API misleading and invite future callers to believe request-specific estimation exists when it does not.
  Recommendation: Remove the parameter until it is used, or implement request-aware estimation and document what request fields influence the estimate.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/policy.py
  Issue: `RetryPolicy.max_attempts` reads like a total-attempts cap, but the recovery loop treats it as “number of retries after the first attempt.”
  Impact: The name obscures real behavior and makes off-by-one errors easy when configuring retries or reading logs.
  Recommendation: Rename to `max_retries` (or adjust the loop to include the initial attempt) and update docstrings to match.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_request.py
  Issue: `manager_id` is a top-level field and also injected into `metadata`, duplicating a vague concept in two places.
  Impact: Redundant, unclear identifiers make request tracing and auditing harder to follow and increase the chance of divergence.
  Recommendation: Keep a single, clearly named identifier (e.g., `request_id`) and eliminate the duplicate metadata key.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/architecture/core/block-interface.md
  Issue: The doc states there is “no separate concept of manager,” yet runtime metadata introduces `manager_id` for LLM executions.
  Impact: Terminology drift makes the architecture harder to follow and undermines shared vocabulary for maintainers.
  Recommendation: Align terminology by renaming `manager_id` in code/docs or explicitly define what “manager” means in architecture docs.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-responses.md
  Issue: The doc specifies a `success` field, while the concrete model exposes `ok` with an alias for `success`.
  Impact: Readers may search for a `success` attribute in code and miss the alias, slowing onboarding and increasing confusion.
  Recommendation: Align the docs with the concrete field name or rename the field to `success` in the model.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal retry metadata uses `llm_attempt` and `block_attempt` keys, but the architecture recommends namespaced keys like `llm.attempt` for internal counters.
  Impact: Non-namespaced keys increase collision risk and make metadata harder to scan in logs.
  Recommendation: Rename internal counters to a namespaced form (`llm.attempt`, `llm.retry_count`) and align with the metadata conventions doc.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The doc defines `payload` as a `str`, but the implementation accepts dict payloads with keys like `prompt`, `content`, or `input`.
  Impact: API consumers and maintainers get conflicting guidance on required inputs, causing avoidable errors and unclear validation behavior.
  Recommendation: Update the doc to reflect the accepted payload shapes or tighten the implementation to enforce string-only payloads.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: Composite terminal responses add metadata keys `source` and `composite`, but `source` is overly generic and its meaning is unclear.
  Impact: Generic metadata keys are easy to misinterpret or collide with application-level metadata.
  Recommendation: Rename to explicit keys like `source_node` and `composite_name`, and document them in the metadata conventions.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/llm-primitive-refined.md
  Issue: The document repeatedly centers “Manager” and `manager_id` terminology, which conflicts with the core architecture’s “everything is a Block; no manager” language.
  Impact: Mixed vocabulary increases cognitive load and makes it unclear which concepts are current vs legacy.
  Recommendation: Either mark this document as legacy and align terms to Blocks, or update the core docs to explicitly define the Manager concept.
  Architecture alignment: No

- Severity: Low
  File: docs/llm-primitive-refined-notes.md
  Issue: Uses Manager/`manager_id` terminology and layered ownership chain that conflicts with the core Block-only vocabulary.
  Impact: Maintainers reading both docs will struggle to reconcile responsibilities and naming, especially for audit metadata.
  Recommendation: Reconcile terminology with the block architecture (or explicitly label this as a legacy sketch).
  Architecture alignment: No

- Severity: Medium
  File: docs/dev/llm-primitive-block-audit.md
  Issue: The audit claims `LLMPrimitive.get_policy_stack` returns a `RepairPolicy` and references internal semantic repair loops, but the current implementation only returns `BubblePolicy` and has no repair loop.
  Impact: Review artifacts drift from reality, confusing maintainers and making it hard to trust the audit as a source of truth.
  Recommendation: Update the audit to reflect current behavior or explicitly label it as historical and out-of-date.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_service.py
  Issue: `_render_prompts` returns a variable named `user_prompt` even when it may include concatenated assistant/system role text.
  Impact: Misleading naming obscures what is actually sent to the model and complicates debugging prompt formatting.
  Recommendation: Rename to `rendered_prompt` or `conversation_prompt` to reflect multi-role content.
  Architecture alignment: Unknown

## Logging and Observability Review

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Composite responses keep child `metadata.block_name`/`span_id` and never overwrite them with the composite attempt identifiers.
  Impact: Observability breaks at composite boundaries because callers cannot correlate a composite attempt (trace/run/span/attempt) to the returned response; the response appears to be from the child only.
  Recommendation: When a composite returns a response, explicitly set composite correlation metadata (`block_name`, `span_id`, `attempt`, `run_id`, `trace_id`, `node_name` as applicable) rather than using `setdefault` so the composite attempt is represented.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: Composite success responses add un-namespaced metadata keys (`source`, `composite`, `last_node`) that are not part of the reserved set.
  Impact: Metadata collisions and inconsistent log fields make observability queries brittle across blocks.
  Recommendation: Namespace composite-specific metadata (for example `composite.source`, `composite.name`, `composite.last_node`).
  Architecture alignment: No

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Tests do not assert required observability metadata fields (`trace_id`, `run_id`, `span_id`, `block_name`, `attempt`, `duration_ms`) on responses.
  Impact: Correlation regressions can slip in without detection, weakening observability guarantees.
  Recommendation: Add tests that validate presence and propagation of required metadata on success and failure paths.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Response metadata uses non-namespaced keys (`model`, `llm_usage`, `llm_calls`, `llm_retry_count`, `input_tokens`, `output_tokens`) despite the metadata standard requiring namespacing for non-reserved keys.
  Impact: Inconsistent metadata conventions make it harder to filter/aggregate logs and risk collisions with other producers.
  Recommendation: Namespace these fields (for example `llm.model`, `llm.usage`, `llm.calls`, `llm.retry_count`, `llm.input_tokens`, `llm.output_tokens`).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Error details embed `str(error)` and `str(cause)` verbatim without redaction or size bounds.
  Impact: Exception strings can include raw prompts, payload fragments, or credentials, which risks PII/secret leakage when these details are logged or persisted.
  Recommendation: Sanitize/redact sensitive fields (API keys, prompts, payloads) and enforce a maximum length before storing error details.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal retry metadata keys (`block_attempt`, `llm_attempt`) are not namespaced even though the metadata standard requires non-reserved keys to be namespaced.
  Impact: These keys can collide with other metadata producers and are harder to search/aggregate consistently.
  Recommendation: Rename to namespaced keys like `llm.block_attempt` and `llm.attempt` (or a project-specific namespace) and update any downstream consumers.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_record_attempt` swallows all exceptions without any logging or error counter.
  Impact: Stats persistence failures become silent data loss; operators cannot detect missing attempt records or diagnose store issues.
  Recommendation: Log a structured error event including correlation fields and the store error, or surface a metric/counter for record failures.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: No log/telemetry events are emitted for `block_start`, `block_success`, `block_failure`, or recovery policy attempts despite the observability vocabulary in the architecture.
  Impact: There is no event stream to debug execution flow, recovery decisions, or failures, making traces and incident response nearly impossible.
  Recommendation: Emit structured events at block start/end and around each recovery policy attempt with required correlation fields (`trace_id`, `run_id`, `span_id`, `parent_span_id`, `block_name`, `node_name`, `attempt`, `reason`).
  Architecture alignment: No

## Documentation Review

- Severity: High
  File: docs/architecture/core/block-observability.md
  Issue: Documentation requires responses to include trace/span/attempt metadata, but composite success responses drop these fields and only include `source/composite/last_node`.
  Impact: Readers will assume traceability is preserved across composite boundaries, but actual behavior loses correlation fields, making observability and recovery analysis unreliable.
  Recommendation: Update docs to note the current composite response metadata loss or (preferred) document the actual behavior and explicitly mark it as a gap requiring implementation.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: Input contract says `payload` is a string, but the implementation accepts either a string or a dict containing `prompt`, `content`, or `input` keys.
  Impact: Callers relying on the docs may pass only strings and miss supported dict shapes; conversely, callers may pass dict payloads that are not documented and later removed as “unsupported.”
  Recommendation: Document the accepted dict payload shapes (or explicitly deprecate them and enforce string-only in code).
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The doc claims provider calls are “routed through LiteLLM” and schema hints are passed to providers, but the implementation uses PydanticAI with the OpenAI SDK and only optionally points at a proxy base URL.
  Impact: Readers will expect LiteLLM client behavior, proxy-only metadata, and response-format features that are not implemented, which can lead to incorrect operational setups.
  Recommendation: Update the implementation note to describe the actual stack (PydanticAI + OpenAI SDK with optional LiteLLM-compatible proxy) and clarify how schema enforcement is performed.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/02-llm-primitive.md
  Issue: Failure modes list only schema/rate limit/api key/context length errors, but the LLM layer also emits generic `llm_execution_failed` and other mapped reasons.
  Impact: Operators will not know about non-classified failures, which makes debugging and recovery policy planning incomplete.
  Recommendation: Add a “generic/unknown LLM failure” reason and describe how it is classified when error types fall outside the known set.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: Propagation rules say composites should generate a new `id` for child requests, but `Request` has no auto-id and `_build_child_request` does not set it.
  Impact: Anyone relying on `id` for request-level tracing will not see it on child requests, despite docs implying it exists.
  Recommendation: Either implement `id` generation in child request construction or soften the doc to mark `id` as optional and not currently emitted.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/architecture/core/block-execution-semantics.md
  Issue: Child request construction requires context pruning, but the composite implementation clones the full parent context unchanged.
  Impact: Readers will assume context minimization is enforced; in practice, sensitive or bloated context may be passed to children without warning.
  Recommendation: Document the current behavior (no automatic pruning) and move the pruning requirement to a “caller responsibility” note if it is not enforced.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/llm-primitive-refined.md
  Issue: The dependency stack and runtime layering describe instructor/tenacity/LiteLLM + StableTransport/Manager layers that do not exist in the current implementation, which instead uses PydanticAI + OpenAI SDK.
  Impact: New contributors will attempt to configure or debug non-existent layers and packages, slowing onboarding and leading to incorrect operational assumptions.
  Recommendation: Mark this document as historical or replace the stack description with the current PydanticAI-based pipeline.
  Architecture alignment: No

- Severity: Medium
  File: docs/llm-primitive-refined.md
  Issue: The documented LLMRequest/LLMResponse shapes include fields like `budget`, `tag`, `history`, `manager_id`, and cost/time estimates, but the implemented `LLMRequest`/`LLMResponse` types do not define these fields.
  Impact: Consumers may build integrations around fields that do not exist, causing runtime failures or incorrect assumptions about budgeting and audit data.
  Recommendation: Update the schema examples to match `src/chaos/llm/llm_request.py` and `src/chaos/llm/llm_response.py`, or explicitly label them as hypothetical future fields.
  Architecture alignment: No

- Severity: Low
  File: docs/llm-primitive-refined-notes.md
  Issue: The layering notes assert a Manager/StableTransport/ModelStatsService stack and budgeting-based model selection that are not implemented in the current codebase.
  Impact: The notes read like actionable guidance but describe components that do not exist, which can misdirect architectural work.
  Recommendation: Add a prominent “concept-only” disclaimer and a pointer to current implementation files, or move this into an archive folder.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-recovery-semantics.md
  Issue: The doc says callers should map from `reason` when `error_type` is missing after serialization, but the implementation defaults to `Exception` and does not perform any reason-based mapping.
  Impact: Readers will assume reason-based fallback exists and design workflows around it, but actual runtime behavior will collapse diverse failures into a single recovery path.
  Recommendation: Either implement the reason-based fallback mapping or clarify in the doc that it is aspirational and not implemented.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/architecture/core/block-request-metadata.md
  Issue: The request contract states `payload` can be any type, but the `Request` model enforces `payload: Dict[str, Any]` and will not accept non-dict payloads without coercion.
  Impact: Documentation implies string payloads are supported for all blocks, but actual request validation can reject them, leading to runtime errors.
  Recommendation: Update the doc to match the concrete `Request` schema or loosen the schema to accept arbitrary payload types.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/dev/llm-primitive-block-audit.md
  Issue: The audit claims `LLMPrimitive.get_policy_stack` returns a `RepairPolicy(add_validation_feedback)`, but the current implementation returns `BubblePolicy()` only.
  Impact: The audit’s “critical” finding about a missing repair function is no longer accurate, which undermines confidence in the rest of the audit.
  Recommendation: Refresh the audit findings or mark this section as stale with the commit/date when behavior changed.
  Architecture alignment: Not Available

## Additional Risks Review

- Severity: Medium
- File: src/chaos/domain/llm_primitive.py
- Issue: Request metadata is copied into `LLMRequest` without validation/allowlisting, and caller-supplied keys can override values like `block_name`.
- Impact: Untrusted metadata can poison logs/stats, spoof identity fields, or leak arbitrary data to downstream LLM providers if metadata is propagated.
- Recommendation: Enforce a strict allowlist of metadata keys and ignore user-supplied identity fields; populate `block_name`, `manager_id`, and attempts from trusted sources only.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/config.py
- Issue: `litellm_use_proxy` can be true while `litellm_proxy_url` is unset, but no validation enforces a usable proxy configuration.
- Impact: Traffic can silently bypass the proxy (or fail later), causing policy or compliance drift and hard-to-debug routing behavior.
- Recommendation: Validate configuration invariants (if proxy enabled, require proxy URL and/or key) and raise a clear error on startup.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/llm_primitive.py
- Issue: `manager_id` truncates UUIDs to 8 hex characters.
- Impact: Higher collision probability in high-throughput systems, reducing traceability and audit reliability.
- Recommendation: Use full UUIDs or include additional entropy (timestamp or full uuid4 hex).
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/domain/block.py
- Issue: Uncaught exceptions are surfaced to callers with raw `str(e)` in `details`.
- Impact: Internal errors can leak secrets (API keys, prompt content, file paths) to external consumers and logs.
- Recommendation: Replace raw exception strings with sanitized error codes; log full details securely behind a debug flag.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/llm/llm_service.py
- Issue: LLM execution does not set or expose max output/token limits or timeouts in `ModelSettings`.
- Impact: A single request can generate unbounded output, increasing latency and cost; timeouts are provider defaults and may be too high.
- Recommendation: Add configurable `max_tokens` and timeout settings to `LLMRequest`/`Config` and pass them to the model settings.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/stats/in_memory_block_stats_store.py
- Issue: In-memory stats store grows without bounds and has no retention or eviction.
- Impact: Long-running processes will steadily increase memory usage and may degrade or crash under sustained load.
- Recommendation: Add configurable retention (max records/TTL) or disable recording for in-memory store in production.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/stats/json_block_stats_store.py
- Issue: JSON stats store rewrites the entire file on every attempt and uses no file locking or size limits.
- Impact: Concurrent writers can corrupt data, and large histories will cause slow writes and high memory usage.
- Recommendation: Add file locking, append-only or chunked storage, and configurable retention/size limits; consider a proper database backend.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/llm/llm_error_mapper.py
- Issue: Error mapping always includes raw exception and cause strings in `details`.
- Impact: Provider errors can embed secrets (API keys, prompts, URLs), which then flow into responses/logs and risk data leakage.
- Recommendation: Redact sensitive fields, truncate messages, and prefer structured error codes over raw exception strings.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/domain/policy.py
- Issue: `RetryPolicy.delay_seconds` is defined but never honored in execution paths.
- Impact: Operators cannot throttle retries, increasing the risk of rate-limit amplification and noisy retry storms.
- Recommendation: Implement delay/backoff handling in recovery execution or remove the field to avoid misleading configuration.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/block.py
- Issue: `_record_attempt` swallows all exceptions when persisting stats.
- Impact: Stats storage failures become silent, making it hard to detect monitoring gaps or capacity problems.
- Recommendation: Log or surface store write failures (at least at debug/error), and consider a configurable failure policy.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/domain/block.py
- Issue: Recovery loop can execute multiple Retry/Repair policies in sequence without a global attempt budget or backoff.
- Impact: A single failure can trigger a large number of re-executions, increasing cost and latency and amplifying load on downstream services.
- Recommendation: Add a global recovery budget (max total attempts) and backoff/jitter; enforce policy ordering and stop conditions explicitly.
- Architecture alignment: Unknown
